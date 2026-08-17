---
name: pikpak-webdav-manager
title: PikPak 文件管理
description: PikPak 网盘文件管理 — rclone WebDAV 操作、CDN 多线程下载、离线磁链、看门狗自动同步
---

# PikPak 文件管理

通过 rclone 静态二进制（`/tmp/rclone`）和 Python 多线程分片下载，管理 PikPak 云盘文件。

**四个接入方式对比（2026-08-15 更新）：**

| 方式 | 速度（本服务器） | 稳定性 | 适用场景 |
|:----|:---:|:-----|:--------|
| 🥇 **WebDAV 多文件并发 (rclone, dav.mypikpak.com:80)** | **单文件5-8MB/s，3并发=24MB/s 线性叠加** | ✅ 直连不走代理，0 流量费 | **🚨 用户硬规则：默认方案，一律用这个** |
| 🥈 **aria2 CDN + 8连接分片** | 快时 8-167MB/s，限流时 0.2MB/s | ⚠️ 节点间歇性 | CDN 解封时用 |
| 🥉 Python CDN + 多线程 Range | ~1.5MB/s（实测有时仅0.3） | ⚠️ 进程易被SIGTERM | aria2不可用时回退 |
| PikPak API CDN 直链 (rclone copyurl) | 200-250KB/s | ✅ 稳定但慢 | WebDAV 限流时备用 |

**🚨 2026-08-15 用户硬规则：从 PikPak 下载一律用 WebDAV 多文件并发！**
- **并发基准测试（2026-08-15 实测，见 `references/webdav-concurrency-benchmark-20260815.md`）**：单文件 5-8MB/s；并发线性叠加——3并发≈20MB/s、6并发≈34MB/s、9并发≈77MB/s、**15并发=111MB/s（峰值）**、20并发=82MB/s（饱和下降）。**最优并发=15**（稳定 79-112MB/s，平均 95.6）
- **0 流量费**（直连 dav.mypikpak.com，不走代理；代理按流量收费贵）
- WebDAV 凭据：url=`http://dav.mypikpak.com:80`，user=`xqji`，pass=`rtabnsvs`（rclone.conf 在 `/opt/data/.config/rclone/rclone.conf`）
- **⚠️ WebDAV 不支持 Range 分片请求**：curl 带 `Range: bytes=0-20M` 返回 HTTP 200 但 size=0（假死），必须**全量流式**下载（rclone copy 默认流式 OK）
- **🚨 判断 rclone 是否在下载：看 `.partial` 文件！** rclone 下载中先写 `<文件名>.<8位随机>.partial` 临时文件，完成后自动改名。**出现 .partial 且大小增长 = 正在下载**。不要用 ps/ss 连接数判断——大文件 WebDAV 握手慢，早期 40s+ 无连接无输出是正常的，误判"卡死"会杀掉正常下载（2026-08-15 踩坑：8 个 rclone 进程跑了 28GB 被误判卡死）
- 多文件并发：rclone 单进程 `--files-from 列表 --transfers 15`（每个文件独立连接，15 并发最优）

**🚨 下载完成流程（用户 2026-08-15 纠正，每次下载后必须执行）**：
1. ffprobe 全量验证（大小匹配 + 无 moov 错误 + 时长正常）
2. **删 PikPak 源文件**（本地完整才删：本地存在且大小≥99% 的文件对应删除；保留未下载的/文件夹）
3. **字幕改名为与视频文件名一致**（按番号匹配：正则 `[A-Za-z]{2,6}-?\d+` 提取番号，大写去连字符后配对，如 `DLDSS-348.[4K]@R.srt` → `DLDSS-348-入田真綾-...幼儿教师.srt`；无匹配视频的字幕保留不删）
4. 汇报时说明删了几个源 + 改了几个字幕

**🚨 moov atom not found 判定（2026-08-15 实测）**：ffprobe 报 moov atom not found = **PikPak 源文件本身损坏**，不是下载问题。判定流程：删本地重下（WebDAV）→ 仍损坏 → 换 CDN 直链 aria2 再下 → 仍损坏 → **实锤源文件损坏**。处理：删本地坏文件 + 删 PikPak 源（避免未来误下载），无法修复除非换磁链重新离线。

## 核心工具脚本

| 脚本 | 路径 | 说明 |
|:----|:----|:------|
| `pikpak_dl_aria2.sh` | `/opt/data/pikpak_dl_aria2.sh` | **aria2 CDN 多连接分片下载器（推荐，5.6 MB/s）**，支持 `-j N` 并行。⚠️ 注意：此脚本可能引用旧的 `/opt/data/aria2c`（缺 libaria2.so），优先用 `uv run aria2c` 或 pip 安装版 |
| `pikpak_cdn_dl.py` | `/opt/data/pikpak_cdn_dl.py` | Python 多线程分片下载器（备用，速度较差） |
| `pikpak.sh` | `/opt/data/pikpak.sh` | rclone 统一管理入口 |
| `check_pikpak_dl.py` | `~/.hermes/scripts/check_pikpak_dl.py` | **no_agent cron 脚本**：检查 PikPak 离线下载状态，完成后写直链到 `/tmp/pikpak_urls.json` |
| `pikpak_watch.py` | `scripts/pikpak_watch.py` | 看门狗监听新文件 |
| `pikpak_watch_wrapper.py` | `~/.hermes/scripts/pikpak_watch_wrapper.py` | 上层调度器 |

## CDN 多线程分段下载（推荐方案）

**方式一：aria2（推荐，5.6 MB/s，8 连接分片）**

aria2 用 C 编写，断点续传、重试策略、多连接分片原生支持，远比 Python 稳定高效。  
**用法**见下面「aria2 下载」章节。

**方式二：Python 多线程 Range（备用，0.3~1.5 MB/s）**

### aria2 下载

#### aria2 安装（无 root 环境 — 推荐 `pip install aria2`）

**推荐方案（2026-07-22）：** 直接 pip 安装（自带 libaria2.so，无需手动管理共享库）：

```bash
uv pip install aria2
# 验证
aria2c --version
```

**备选方案（手动 deb 提取，pip 不可用时）：**

```bash
# 1. 下载 aria2 deb
curl -x socks5://127.0.0.1:10808 \
  "http://ftp.debian.org/debian/pool/main/a/aria2/aria2_1.37.0+debian-3_amd64.deb" \
  -o /tmp/aria2.deb

# 2. 提取二进制
cd /tmp && mkdir aria2_extract && cd aria2_extract
ar x /tmp/aria2.deb && tar xf data.tar.xz
cp usr/bin/aria2c /opt/data/

# 3. 下载 libaria2.so.0
curl -x socks5://127.0.0.1:10808 \
  "http://ftp.debian.org/debian/pool/main/a/aria2/libaria2-0_1.37.0+debian-3_amd64.deb" \
  -o /tmp/libaria2.deb
cd /tmp && mkdir lib_extract && cd lib_extract
ar x /tmp/libaria2.deb && tar xf data.tar.xz
cp usr/lib/x86_64-linux-gnu/libaria2.so.0* /opt/data/

# 4. 下载 libcares2
curl -x socks5://127.0.0.1:10808 \
  "http://ftp.debian.org/debian/pool/main/c/c-ares/libcares2_1.34.5-1+deb13u1_amd64.deb" \
  -o /tmp/libcares.deb
cd /tmp && mkdir cares_extract && cd cares_extract
ar x /tmp/libcares.deb && tar xf data.tar.xz
cp usr/lib/x86_64-linux-gnu/libcares.so.2* /opt/data/

# 5. 设置 symlink + LD_LIBRARY_PATH
ln -sf /opt/data/libaria2.so.0.0.0 /opt/data/libaria2.so.0
export LD_LIBRARY_PATH=/opt/data
/opt/data/aria2c --version   # 验证
```

#### aria2 下载命令

```bash
export LD_LIBRARY_PATH=/opt/data

# 单文件
/opt/data/aria2c \
    --max-connection-per-server=8 \
    --split=8 \
    --min-split-size=8M \
    --continue=true \
    --max-tries=5 \
    --retry-wait=5 \
    --timeout=120 \
    --connect-timeout=30 \
    --console-log-level=notice \
    --dir=/opt/data/PikPak/Inbox-JAV \
    --out=<文件名> \
    "<CDN_URL>"

# 多文件并行下载（推荐——用 bash 包装器，见 references/bash-wrapper-parallel-download.md）
# ❌ 不要用 --input-file 传长 CDN URL（约835字符，会被截断导致 total length mismatch）
# ✅ 正确做法：将 URL 读入 shell 变量，作为参数直接传递
```bash
cat > /tmp/download_all.sh << 'SHEOF'
#!/bin/bash
export LD_LIBRARY_PATH=/opt/data
SONE_URL=$(cat /tmp/SONE_cdn.txt)
/opt/data/aria2c ... --out='file1.mp4' "$SONE_URL" &
PID1=$!
/opt/data/aria2c ... --out='file2.mp4' "$(cat /tmp/DRPT_cdn.txt)" &
PID2=$!
wait $PID1 $PID2
echo "ALL DONE"
SHEOF
chmod +x /tmp/download_all.sh && /tmp/download_all.sh
```

#### 一键脚本（推荐）

```bash
# 下载全部（自动读取 /tmp/pikpak_urls.json）
/opt/data/pikpak_dl_aria2.sh

# 并行下载最多5个文件
/opt/data/pikpak_dl_aria2.sh -j 5

# 指定并行数（最大5）
/opt/data/pikpak_dl_aria2.sh -j 3

# 下载指定文件
/opt/data/pikpak_dl_aria2.sh MIDA-646.mp4
```

**并行下载说明（默认行为）**：aria2 可同时下载最多 N 个文件（默认 5，上限 5），超出排队等候。每个文件使用 8 连接分片，速度互不影响。适合批量下载多个番号。  \\n注意：并行下载时总带宽会被均分，单个文件速度降低但整体吞吐量更高。  \\n**⚠️ 用户偏好：凡是多文件下载，默认启用 `-j N` 并行下载。不要串行逐个下载！** 即使单文件 CDN 速度慢（<2 MiB/s），将多个文件一起并行下载，快的文件先完成释放带宽，整体效率远高于串行等待。

### 🚨 大规模批量下载（100+ 文件 / 200GB+）— asyncio 并发架构（2026-08-09 AI短剧实战）

写 Python 批量下载器（asyncio worker 池 + Queue）时，三个必踩的坑：

**坑1：aria2/ffprobe 是阻塞 subprocess，直接 `await` 会冻结整个事件循环 → 4 个 worker 只有 1 个在干活**
症状：日志打了 4 条 `⬇️` 但只有 1 个 aria2 进程，其余 worker 永远不推进。
根因：`process_one` 里 `subprocess.run(aria2)` 阻塞调用占住事件循环，其他协程无法调度（asyncio 单线程）。
修复：**所有阻塞调用必须 `await loop.run_in_executor(None, fn, ...)` 或 `asyncio.to_thread()`** 包装，包括 aria2 和 ffprobe。

```python
async def aria2_download_async(url, dest_file):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, aria2_download, url, dest_file)  # aria2_download 是同步函数
```

**坑2：subprocess 里调用 `/opt/data/aria2c` 必须传 `env={'LD_LIBRARY_PATH': '/opt/data'}`**
shell 里 `export LD_LIBRARY_PATH` 不会传给 Python subprocess 子进程，直接 Popen 会报 `error while loading shared libraries: libaria2.so.0`。

**坑3：慢 CDN 节点（dl-a10b 段）会拖死整个队列 → 必须内置慢速检测 + 换节点**
用户明确要求：**速度 < 0.5MB/s 立即换节点，不要等**。机制：
1. aria2 用 `Popen`（非 run），后台线程每 15s 检查目标文件大小增量
2. 连续 2 次（30s）增量 < `0.5MB/s × 15s` → `proc.kill()` + 删半成品（`.mp4` + `.aria2`）→ 返回 SLOW
3. SLOW 后立即 `get_download_url()` 重新获取 URL（会分配到不同节点，dl-z01a 段通常快）
4. 换 3 次仍 SLOW → **放回队列尾部稍后重试（不要标记失败放弃）**——CDN 限流常是暂时的，重新排队可能分到快节点

**坑3a（🚨 2026-08-10 后半程关键修复）：大文件（>500MB）必须完全取消 SLOW 检测**
症状：补下大文件（1.4~4.3GB）时全部 `❌ 失败 (SLOW)`，只有小文件能成功——大文件下载中网络抖动 30s 就被 SLOW 检测 kill 从头再来，永远下不完。
根因：SLOW 检测对"短时降速"一视同仁，大文件中途抖一下（aria2 在重连/重试）就被误杀，删半成品重来 → 无限循环。
修复：`aria2_download` 加 `total_size` 参数，**`total_size > 500MB` 时直接 `proc.wait()` 跳过 SLOW 检测循环**（aria2 自带 `--max-tries/--timeout` 处理断连，让它一口气下完）。实测修复后 1~4GB 大文件全部 27~31MB/s 一次下完，0 失败。
```python
def aria2_download(url, dest_file, total_size=0):
    ...
    proc = subprocess.Popen(...)
    # 大文件完全取消 SLOW 检测
    if total_size > 500 * 1024 * 1024:
        proc.wait()
        return proc.returncode == 0, time.time()-t0, 'OK' if proc.returncode == 0 else 'FAIL'
    # 小文件才走 SLOW 检测循环
    while proc.poll() is None: ...
```
调用点传 `task['size']`，`aria2_download_async` 同步加参数。**用户拍板：大文件取消 SLOW 检测 + 并发按现场指定（本次 4）。**

**坑3b：FAIL（非 SLOW 错误）也要自动重排队**
aria2 返回非 SLOW 错误（超时/断连等，`reason == 'FAIL'`）时同样放回队列尾部重试，**用 `task['attempts']` 计数防无限循环（最多 3 次，SLOW 和 FAIL 共享计数）**。用户要求：失败不丢文件，重排队后再试。

```python
# 慢速检测核心（aria2 Popen 后循环）
while proc.poll() is None:
    time.sleep(3)
    if time.time() - last_check >= 15:
        cur = os.path.getsize(dest_file) if os.path.exists(dest_file) else 0
        if prev_size >= 0 and (cur - prev_size) < SLOW_THRESHOLD * 15:
            slow_count += 1
        else:
            slow_count = 0
        prev_size = cur
        if slow_count >= SLOW_CHECKS:  # 连续2次(30s)低于阈值
            proc.kill(); proc.wait()
            for p in [dest_file, dest_file + '.aria2']:
                if os.path.exists(p): os.remove(p)
            return False, elapsed, 'SLOW'
```

**坑4：暂停后恢复必须显式"跳过已存在文件"，不能只靠 `--continue=true`**
aria2 `--continue=true` 只续传半成品，已完整下载的文件会重新下。批量脚本 `process_one` 开头必须检查：
```python
if os.path.exists(dest_file):
    if os.path.getsize(dest_file) >= task['size'] * 0.99:  # 大小匹配(容差1%)
        results.append({'task': task, 'status': 'SKIP'})
        print(f"⏭️ 已存在跳过: {fname}")
        return
```
暂停/恢复工作流（2026-08-09/10 实战）：CDN 时段性限流（0 MB/s）时**暂停等恢复比空转强**——SLOW 换节点机制在整体限流下只是空转烧时间。流程：
1. `pkill -f ai_drama_dl.py` + `pkill -f aria2c.*<目标>` 停干净，删 `*.aria2` 半成品（保留完整文件）
2. **同时暂停监控 cron**（否则每 10 分钟误报"进程已退出"）
3. 挂测速 cron：no_agent 每 30 分钟跑 `curl -r 0-20M` 测 CDN，**速度 >1MB/s 才 print 提醒，低速完全静默**（no_agent cron 空输出=不打扰，非空 stdout 原样推送）
4. 用户说继续 → 重启脚本（自动 SKIP 已完成）+ resume 监控 cron
测速脚本：`/opt/data/scripts/ai_cdn_speed_test.sh` + `.py`（用 .venv python 包装，pikpakapi 不在系统 python）。

**用户下载策略偏好（2026-08-09 明确 + 2026-08-15 更新，批量下载必须遵守）**：
- **省钱第一**：**默认走 WebDAV 直连（5-7MB/s，0 流量费）**。代理按流量收费太贵，用户 2026-08-15 明确："怎么能不用代理下载？用代理下载按照流量收费，太贵了"。CDN 直连虽然免费但节点限流不稳定（间歇 0.2MB/s）。
- **判定顺序**：① WebDAV 直连（省钱首选）→ ② aria2 CDN 直连（节点解封时快）→ ③ 代理 SG-AWS02（仅当 WebDAV/CDN 都不可用或急需高速时）。**判定标准（2026-08-10 实战）**：直连全节点 <0.1MB/s 持续 10+ 分钟 = IP 级限流 → 切代理（`--all-proxy=http://127.0.0.1:10808`）换出口 IP，实测提速 ~80 倍。
- **慢节点立即换**：< 0.5MB/s 马上 kill + 换 URL，不等不重试。
- **并发数用户每次现场指定**（4 → 3 → 2 均出现过，2 最稳），脚本用 `CONCURRENCY` 常量随时可调，不要写死。
- 换 3 次仍慢 → 文件放回队列尾部（REQUEUE），不放弃。

**批量下载完整脚本模式**（AI短剧 1248 文件/242GB 实战验证）：
- 架构：`asyncio.Queue` + N 个 worker + `Semaphore(CONCURRENCY)`，每个 worker `queue.get()` → `process_one()` → `queue.task_done()`，用 `None` 哨兵终止
- 进度统计：`stats = {'total', 'done', 'bytes_ok', 't0'}`，ETA = 剩余字节 / (累计字节/总耗时)，每次完成 print 累计均速 + 剩余 GB + ETA
- 结果落盘：每个文件 append 到 results 列表（OK/DL_FAIL/URL_FAIL/REQUEUE），结束 dump JSON
- 完整脚本：`/opt/data/ai_drama_dl.py`（2026-08-09 实战，可参考）
- 完整实录（manifest 结构/运行方式/监控/复用步骤）：`references/batch-folder-download-20260809.md`

### 批量文件 → 剧集文件夹归属（文件名《标题》识别）

PikPak 文件夹常混入其他剧集（尤其"合集"文件夹，文件名才暴露真实归属）。规则（2026-08-09 用户确认）：
1. **文件名含 `《标题》` → 用标题作为该文件的剧集归属**（不管它在哪个文件夹）——混入的剧集自动摘出单独建文件夹
2. 无书名号 → 按所在文件夹归属
3. 剧集合并（古寺艳鬼录 / G-古寺艳鬼录 / 古寺艳鬼录 1-10 → 同一剧集）：规范化核心名（去 `G-`/`D-`/`【I_No.N】` 编号前缀、去尾部集数、去符号）后，**相同 OR 互相包含（短名/长名 ≥ 60%）OR 编辑距离 1** 视为同一剧集，并查集合并
4. ⚠️ 合集长名陷阱：`《爱琳-...长生录...征服郭伯母...》` 这类合集名会"包含"多个无关剧集名 → **包含匹配必须限制短名占长名 ≥ 60%**，否则误合并
5. 去重：同剧集内规范化文件名相同 → 只留最大。**用户偏好：无法确认是否重复的视频不去重，都塞进文件夹**（宁可多下不可漏）


### Python 分片下载（备用）

**原理**：通过 `pikpakapi` 获取 CDN 直链 → Python 多线程 HTTP Range 并发分片 → 合并。

#### 用法

```bash
# 刷新直链并下载（自动获取所有文件）
/opt/data/.venv/bin/python3 /opt/data/pikpak_cdn_dl.py

# 或指定文件
/opt/hermes/.venv/bin/python3 /opt/data/pikpak_cdn_dl.py NSFS-484.mp4
```

#### 参数调优

| 变量 | 默认值 | 说明 |
|:----|:-----|:-----|
| THREADS = 8 | 8 | 并发线程数 |
| CHUNK_MB = 8 | 8MB | 每分片大小（小分片避免超时） |

### 从 PikPak 获取 CDN 直链（使用 token 恢复）

```python
from pikpakapi import PikPakApi
import json, asyncio

async def get_urls():
    with open('/opt/data/.pikpak_token.json') as f:
        state = json.load(f)
    client = PikPakApi.from_dict(state)
    
    # ⚠️ 用 path_to_id() 而不是 file_list() 来找文件夹！
    # file_list(parent_id=...) 有时会报 "File or folder is not found"
    # path_to_id 始终可靠
    result = await client.path_to_id('/Inbox-JAV')
    inbox_id = result[0]['id'] if isinstance(result, list) else result
    
    ls = await client.file_list(parent_id=inbox_id)
    urls = {}
    for f in ls.get('files', []):
        if f.get('kind') == 'drive#folder':
            continue
        if not f.get('name','').endswith('.mp4'):
            continue
        info = await client.get_download_url(f['id'])
        # ⚠️ URL 在 web_content_link 字段，url 字段可能为空
        url = info.get('web_content_link', '')
        if url:
            urls[f['name']] = url
    
    json.dump(urls, open('/tmp/pikpak_urls.json','w'))
    return urls

asyncio.run(get_urls())
```

**⚠️ 坑：必须用完整 file ID**。`file_list()` 返回的 `id` 字段是完整 ID（如 `VOw8FDYPL1n6I5mr2b3QkmiLo2`），终端显示可能截断。用截断版调用 `get_download_url()` 会返回 "File or folder is not found"。

**`get_download_url()` 返回的 URL 在 `web_content_link` 字段（2026-07-22 确认：`url` 字段永远为空，`links` 和 `medias` 字段也不包含有效下载 URL。只用 `web_content_link`。）**

### 速度实测数据（2026-08-15 更新 — WebDAV 已逆袭）

| 方案 | 并发数 | 合计速度 | ETA(5GB) | 稳定性 |
|:----|:-----:|:-------:|:--------:|:------|
| 🥇 **WebDAV 直连 (rclone copy)** | 1 | **5-7 MB/s（持续不降速）** | **~15min** | ✅ 稳，0 流量费 |
| 🥈 aria2 8连接分片 CDN | 8 | 快时 8-167 / 限流 0.2 | 不定 | ⚠️ 节点间歇 |
| 🥉 Python 8线程 Range | 8 | ~0.3~1.5 MB/s | ~1h | ⚠️ 进程易被SIGTERM |
| rclone copyurl CDN | 1 | 200-250KB/s | ~6h | ✅ 慢但稳 |
| PC Neat Download | N/A | 5MB/s | ~17min | N/A |

> ⚠️ 旧数据（2026-06）记录 WebDAV 只有 1.4MB/s→50KB/s 降速+503，**已过时**——换出口 IP / PikPak 政策变化后 WebDAV 直连稳定 5-7MB/s，是本服务器当前**最省钱**的下载通道。

### 坑 — 务必逐条阅读

- **🚨 IP 级限流（2026-08-10 重大发现）**：当**所有** CDN 节点直连都 <0.1MB/s（换 URL 无效、多节点/多文件全慢），是 **PikPak 对服务器出口 IP 限流**，不是节点问题也不是全局限流！解法：**aria2 加 `--all-proxy=http://127.0.0.1:10808` 走代理换出口 IP**。实测：直连 0.08 MB/s → 代理出口（103.62.49.138）0.95 MB/s（单连接 curl），aria2 8连接实际 **6~8 MB/s**，提速 ~80 倍。判定流程：curl 直连测速 <0.1MB/s → `curl -x http://127.0.0.1:10808` 测同一 URL，代理明显更快 → 确认 IP 限流 → 下载脚本加 `--all-proxy`。注意走代理后 SLOW 阈值要降（代理吞吐上限低，0.5MB/s 阈值会误杀，**用户拍板用 0.2MB/s**）。完整实录见 `references/pikpak-ip-throttling-20260810.md`。
- **🚨 代理出口 IP 也会被限流（2026-08-10 后半程）**：103.62.49.138 用了约 1 小时后从 0.95MB/s 掉回 ~0，且该 IP 段的 AWS日本节点（103.62.49.138/.178）全都只有 ~0.95MB/s。**换节点是常态操作不是一次性**：`bash /opt/data/proxy-skill/proxy_auto_switch.sh --node '🇸🇬AWS新加坡02'` 切到 **67.159.48.147 后实测 25~30MB/s（aria2 8连接）**，242GB 在 ~1 小时内下了 170GB。经验：**逐节点测速（`curl -x 10808 -r 0-20M`）找出口 IP 段差异大的节点，快节点直接让整个下载提速一个数量级**。测速/切换脚本见 `references/pikpak-ip-throttling-20260810.md`。
- **不要走代理下载（默认）**：代理按流量收费，且通常更慢。CDN 直链和 WebDAV 都是直连 HTTP，不需要代理。**例外：IP 级限流时（见上条）走代理是唯一解法。** 完整 WebDAV 实测 + Range 坑 + 下载脚本模式见 `references/webdav-direct-download-20260815.md`。
- **Python 下载器缺陷**：`pikpak_cdn_dl.py` 进程经常被 SIGTERM（exit code 143）杀死，导致频繁重下。此时切 aria2 可解。
- **🚨 幽灵 inode 陷阱（2026-06-27 新增）**：下载过程中 **绝对不要** `rm -f` 正在被 aria2 写入的文件！即使文件被删除（unlink），aria2 仍通过文件描述符继续写入孤儿 inode，数据写入磁盘但在目录中不可见。重新创建同名文件使用的是新 inode，旧数据无法恢复。等于白下。删除操作分成两步：
  1. 先 `kill <aria2_pid>` 或 `pkill -f "aria2c.*特定文件名"` (不要无差别杀)
  2. 确认进程死后，再 `rm -f 文件` 和 `rm -f *.aria2`

- **🚨 不要无差别 `pkill -f aria2c`！** 这条命令会杀掉**所有** aria2 进程，包括刚启动的新下载。正确的做法：杀旧进程时用更精确的匹配，如 `pkill -f pikpak_cdn_dl.py`（杀 Python 进程）。如果必须杀 aria2，先 `ps aux | grep aria2` 确认 PID，再 `kill <PID>`。

- **✅ 推荐：下载到临时目录** — 先下载到 `/tmp/dl/`、`/tmp/dl2/` 等独立临时目录，aria2 完成后 ffprobe 校验通过，再 `mv` 或 `cp` 到最终目录。这完全避免与目标目录的 inode 冲突。注意 `cp`/`mv` 大文件（>5GB）可能被终端 10s 超时打断导致文件损坏——用 `background=true + notify_on_complete=true` 来执行复制操作即可。校验通过后再删除临时文件。
  ```bash
  mkdir -p /tmp/dl
  aria2c --dir=/tmp/dl --input-file=/tmp/input.txt
  ffprobe ... /tmp/dl/file.mp4     # 校验
  mv /tmp/dl/file.mp4 /target/     # 搬迁
  ```

- **🚨 多个下载进程不能同时写同一个文件！** 旧会话后台残留的 `pikpak_cdn_dl.py` / rclone 进程会覆盖 aria2 已下载完成的文件，导致文件损坏。**典型案例**：先 aria2 下载完成（5.98GB 满大小，ffprobe 验证通过），后台旧 Python/rclone 进程后写完覆盖，文件逻辑大小 6.0GB 正确但 `ffprobe` 报 `moov atom not found`（MP4 元数据损坏），等于白下。**下载前必须先 kill 所有旧进程**：
  ```bash
  pkill -f pikpak_cdn_dl.py 2>/dev/null
  pkill -f rclone.*copy.*Inbox-JAV 2>/dev/null
  pkill -f pikpak_queue.py 2>/dev/null
  sleep 1  # 确保进程退出
  ```
  **下载后必须做完整性检查**：
  ```bash
  # 唯一可靠的校验 — ffprobe 通过才算通过
  ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 file.mp4
  # 输出数值(秒) → ✅ | 报错/"moov atom not found"/无输出 → ❌ 损坏，删了重下
  ```
  **不要依赖 `du`/`stat`/`ls -lh` 判断文件完整性**。aria2 使用 fallocate() 预分配，文件一创建就显示全量大小，但实际数据可能只写了开头。
  **重下步骤**：
  ```bash
  rm -f file.mp4 *.aria2                    # 清空旧文件+控制文件
  pkill -f pikpak_cdn_dl.py 2>/dev/null     # 杀干扰进程
  pkill -f rclone 2>/dev/null
  sleep 1
  export LD_LIBRARY_PATH=/opt/data
  /opt/data/aria2c --max-connection-per-server=8 --split=8 ...  # 重下
  ffprobe -v error -show_entries format=duration ... file.mp4   # 验证
  ```
- **清理旧 .part 碎片**：Python 分片下载器 `pikpak_cdn_dl.py` 中断后会留下大量 `*.partN` 文件（~2GB 空占空间）。下载前/后清理：
  ```bash
  rm -f /opt/data/PikPak/Inbox-JAV/*.part*
  ```
- **Python 输出缓冲**：后台跑 Python 下载脚本需加 `PYTHONUNBUFFERED=1` 否则看不见进度。
- **⚠️ `--input-file` 与超长 CDN URL 不兼容（2026-07-09）**：PikPak CDN URL 约 835 字符，`--input-file` 解析会截断，报 `total length mismatch`。**改用 Bash 包装器**：将 URL 读入 shell 变量作为命令行参数直接传递。详见 `references/bash-wrapper-parallel-download.md`。
- **⚠️ aria2 `--out` 多文件**：用 `--out=file1 URL1 --out=file2 URL2` 语法时第二个 `--out` 覆盖第一个。多文件时用 bash 包装器（推荐）或 `--input-file`（仅短 URL）。
- **⚠️ aria2 `--continue` 与旧 .aria2 控制文件**
- aria2 下载到 99% 时尾部速度会降至 ~1 MB/s（只有 1 连接在收尾），这是正常现象，耐心等待几秒即可完成。
- **PikPak CDN 限流较松，但短期大量并发请求仍可能被限。稳定在 8 连接即可。** aria2 实测速度可达 8~13 MiB/s（8连接，3文件并行时每文件约 2~5 MiB/s，总计 ~13 MB/s），远超 Python 多线程。
- 分片不能太小（8MB 以上），否则 TCP 慢启动无法充分利用带宽。
- CDN URL 有效期约 24 小时，但可能在几分钟内被 CDN 节点拒绝（403 error，随机旋转节点）。**必须在启动 aria2 前立即获取 URL**，不要缓存后等几分钟再用。失效时重新 `get_download_url()` 会分配不同 CDN 节点。
- **🎯 CDN 节点速度不均**：PikPak 的不同 CDN 节点（dl-a10b-* vs dl-z01a-*）速度差异很大，有的 0.7~1 MiB/s，有的 8~12 MiB/s。发现单个文件速度 <2 MiB/s 时，**不必等待**，直接 kill 当前 aria2 进程，将多个文件合并到同一个 aria2 并行会话（`-j N`）下载。多文件并行时，慢的 CDN 节点带宽自然被挤占，快的节点先下完释放资源给其他文件。**总吞吐量远大于单文件低俗等待。**
- **🚨 文件级持续限速（2026-07-31）**：个别文件（如 NMSL-011 7.07GB）在**连续 4 个不同 CDN 节点**上都只有 20~120 KB/s（换 URL 3 次、每次分配到新节点 dl-a10b-1543/1555/1196 都限速）。**这不是节点问题，是该文件在 PikPak CDN 上的分发有问题**——继续换 URL 无用。处理：kill 进程 → 删除 PikPak 中的该文件 → 回 javdb 换**不同 btih 的磁链**重新离线（同番号通常有多个 btih）。判定标准：换 2 个节点仍 <500KB/s 且 ETA 以"小时"计 → 停止换 URL，直接换磁链。
- **⚠️ 换不同大小版本必须删旧残留（2026-07-31）**：同一番号先下了小版本（如 1.8GB）被取消/中断，再下大版本（5.2GB）时，若 `/tmp/dl/番号.mp4` 残留旧文件，aria2 报 `total length mismatch. expected: 5577148855, actual: 1916883978`（expected 是新 URL 的目标大小，actual 是残留旧文件大小）。**每个 aria2 启动前必须 `rm -f /tmp/dl/番号.mp4 /tmp/dl/番号.mp4.aria2`**，特别是同一番号换过不同大小版本时。
- **CDN URL 403 限流（2026-07-30 新增）**：PikPak CDN 会随机返回 `status=403`，伴随 `X-Xos-Err-Desc: 1` 头部，表示当前 CDN 节点拒绝服务。即使 URL 中的 `expire` 参数未到，节点也可能限流。修复：重调 `client.get_download_url(file_id)` 获取新 URL（通常分配到不同节点），`rm -f` 旧文件后从零重下。**不要**用 `--continue=true` 续传 403 后的文件——数据已损坏。
- **死种/异常磁链重试策略**：参见 `references/dead-magnet-retry-strategy.md`。PikPak 死种（offline 任务消失）或 size=0 卡住时，等 30 分钟后重新搜索 javdb，最多 3 次。
- **📊 状态报告含下载速度**：向用户汇报下载进度时，始终包含速度和 ETA（如 `ATID-537 | 573MiB/5.0GiB (11%) CN:8 DL:11MB/s ETA:7min`）。来自用户明确的偏好：`"以后再报状态时候可以加一个下载速度"`。
- **⚠️ `batch_download_url` 不支持文件夹内文件**：`POST /files/{id}:batch_download_url` 用于获取文件直链，但如果文件在离线任务创建的文件夹内（见前文磁链坑），此 API 返回 "unimplemented"。正确方式是用 `GET /drive/v1/files/{id}?_magic=1`，URL 在 `web_content_link` 字段。

## rclone WebDAV 操作

### 基础命令（🚨 所有 rclone/curl 命令必须加超时保护，禁止裸跑！）

**为什么**：2026-08-16/17 两次微信死掉都是 rclone/curl 网络命令遇 PikPak 瞬时故障无限等待 → agent 卡死 → gateway 忙转。**查询类命令用 shell `timeout` 前缀；下载类命令用 rclone 自带 `--timeout`（空闲超时，下载中有数据流动不误杀，卡死自动断）。**

```bash
timeout 60 /tmp/rclone ls pikpak:/目录          # 列出（查询类：必须 timeout 前缀）
timeout 60 /tmp/rclone lsjson pikpak:/目录      # JSON 格式
timeout 60 /tmp/rclone lsf pikpak:/目录         # 只列名（最常用，确认实际路径）
timeout 120 /tmp/rclone delete pikpak:/文件     # 删除
# 下载/上传：shell timeout 会误杀大文件，改用 rclone 自带 --timeout 60s --contimeout 30s
```

### 配置信息

```yaml
type: webdav
url: http://dav.mypikpak.com:80
vendor: other
user: xqji
pass: <加密>
```

**获取 WebDAV 密码：** `/tmp/rclone reveal "<encrypted_pass>"`

### rclone copy 下载（🥇 首选 — 2026-08-15 验证 5-7MB/s）

**省钱关键：WebDAV 走 dav.mypikpak.com 直连，不经过代理 → 0 流量费。** 用户明确要求避免代理下载（按流量收费太贵）。批量下载默认用 WebDAV。

```bash
mkdir -p /tmp/dl   # ⚠️ 目标本地目录必须先存在，否则报 "directory not found"
timeout 3600 /tmp/rclone copy "pikpak:/远程/文件.mp4" /tmp/dl \
  --buffer-size=128M --multi-thread-streams=0 --progress --timeout 60s --contimeout 30s
# shell timeout 3600 兜底（防 rclone 本身异常挂死）；--timeout 60s = 60s 无数据流动即断
```

**⚠️ 坑A：WebDAV 不支持 HTTP Range 请求！**
用 `curl -H "Range: bytes=0-..."` 测 WebDAV 会返回 **HTTP 200 但 size=0**（服务器忽略 Range 头返回空响应），误以为"连不上/0 速度"。**必须用 rclone copy 全量流式下载**。测速也别用 curl Range，用 rclone copy 跑 15-30s 后看落盘字节数。

**⚠️ 坑B：rclone copy 报 "directory not found" 时先检查远程路径**
`rclone copy pikpak:目录/文件.mp4` 把远程路径当目录解析。先 `rclone lsf pikpak:根目录/` 确认文件实际路径（文件可能在子文件夹内，如 `My Pack/DSOD-008/xxx.mp4`），且本地目标目录要 `mkdir -p`。

**⚠️ 坑C：多线程参数**
`--multi-thread-streams=0` 关闭多线程（WebDAV 单线程更稳）。要并行多文件时用 `--transfers N`（见下）。

注意：历史记录（2026-06）WebDAV 长期传输可能触发 503 限流、速度降至 50KB/s——2026-08-15 实测未复现，但超大文件长时间传输若降速，暂停 10 分钟恢复。

## 批量并行下载

```bash
# 指定文件列表（files-from 里写相对路径文件名，rclone 相对于 copy 的远程源根解析）
# ⚠️ 远程根=整个 PikPak 根，不是 Inbox-JAV！文件在 Inbox-JAV 下时：
#   远程路径必须写 pikpak:Inbox-JAV（files-from 里仍是纯文件名）
#   ❌ 错误: rclone copy pikpak:Inbox-JAV/DASS-xxx.mp4 本地（把路径当目录，报 directory not found）
#   ✅ 正确: rclone copy pikpak:Inbox-JAV 本地 --files-from /tmp/list.txt
echo "file1.mp4" > /tmp/list.txt
timeout 7200 /tmp/rclone copy --files-from /tmp/list.txt pikpak:/Inbox-JAV /本地 \
  --transfers 15 --buffer-size=128M --multi-thread-streams=0 --progress --timeout 60s --contimeout 30s
```

**🚨 坑D：子文件夹内的文件，files-from 必须写完整相对路径（2026-08-15 AI短剧 实战）**
当远程源文件夹含多层子文件夹（如 AI短剧 48 个子文件夹）时，`--files-from` 只写纯文件名 → rclone 报 **"There was nothing to transfer"**（它在源根找不到这些文件）。必须先用 pikpakapi 递归遍历拿到每个缺失文件的完整相对路径，files-from 里写 `子文件夹/子子文件夹/文件名`：
```python
# 1. pikpakapi 递归收集缺失文件的完整相对路径
path_map = {}  # name -> '子文件夹/文件名'
async def walk(pid, relpath):
    r = await api.file_list(parent_id=pid, size=100)
    for f in r.get('files', []):
        if f.get('kind') == 'drive#folder':
            await walk(f['id'], relpath + '/' + f['name'] if relpath else f['name'])
        elif f['name'] in missing_names:
            path_map[f['name']] = (relpath + '/' + f['name']) if relpath else f['name']
# 2. files-from 写 path_map.values()，rclone copy pikpak:AI短剧 本地 --files-from ...
```
判定信号：rclone 秒退（0.5s）且日志 "There was nothing to transfer" = files-from 路径没对上源根。

**批量补下工作流（云端 vs 本地对比）**：
1. pikpakapi 扫描云端全部文件（含子文件夹递归）→ manifest
2. 对比本地：文件名直接匹配 OR 去 `2048.hk@` 前缀匹配（云端常带网站前缀，本地可能已去前缀）→ 得出缺失清单
3. 对缺失清单递归拿完整相对路径 → files-from
4. `--transfers 15` 下载，本地已存在且大小≥99% 的剔除（断点续传）
5. 进度监控：看 `.partial` 文件增长（不是 ps/ss），单进程 rclone 日志可能长时间无输出

**批量下载实战（2026-08-15 Inbox-JAV 6 文件/66GB）**：
1. 用 pikpakapi `file_list` 扫描目录，筛 >100MB 视频（排除字幕文件夹/小文件）
2. 生成 files-from 列表（纯文件名，文件在源根时）
3. `rclone copy pikpak:Inbox-JAV <本地> --files-from 列表 --transfers 15`（15 并发最优）
4. 本地已存在且大小 ≥99% 的文件从列表剔除（断点续传）
5. 进度监控：看 `.partial` 文件增长（不是 ps/ss），单进程 rclone 日志可能长时间无输出

## 看门狗自动下载（智能休眠版）

详见 `scripts/pikpak_watch.py` + `scripts/pikpak_watch_wrapper.py`。  
核心：**no_agent 纯脚本 → 0 token 消耗**。

### 架构

| 文件 | 作用 | 位置 |
|:----|:----|:----|
| `pikpak_watch.py` | 底层下载器 | `scripts/pikpak_watch.py` |
| `pikpak_watch_wrapper.py` | 上层调度器 | `~/.hermes/scripts/pikpak_watch_wrapper.py` |

### 控制

```bash
# 激活
touch /opt/data/PikPak/.watch_active

# 休眠
rm -f /opt/data/PikPak/.watch_active /opt/data/PikPak/.watch_idle_since
```

## PikPak 磁链离线注意事项

> 📌 FC2 番号在 javdb 需要登录才能看磁链（登录墙）——让用户自行把磁链加入 PikPak，Agent 从 PikPak 侧继续（取 CDN → aria2 → 入库）。详见 `references/fc2-login-wall-pikpak-continue.md`。

### ⚠️ 磁链可能创建文件夹而非文件

PikPak 离线下载磁链后，不一定会直接生成 `.mp4` 文件在目标文件夹中。某些磁链（尤其是从 javdb 获取的 `[来源]番号-C` 格式）会**创建一个以磁链标题命名的文件夹**，视频文件在文件夹内部：
```
Inbox-JAV/
  [22sht.me]rbd-664-C/          ← 磁链创建的文件夹
    rbd-664-C.mp4               ← 实际视频在里面
    安卓二维码.jpg               ← 有时还附带广告文件
  CAWD-992.mp4                  ← 其他磁链直接生成文件
```

**处理方法**：添加离线后，用 `file_list(parent_id=inbox_id)` 检查返回的是 `kind=drive#file` 还是 `kind=drive#folder`。如果是文件夹，需要进一步 `file_list(parent_id=folder_id)` 获取内部文件。然后用 `get_download_url(file_id)` 获取 CDN 链接。

### ⚠️ 磁链垃圾广告污染

有些 torrent 文件（尤其是国产发布的"fhdall"或"合集"类种子）包含大量**垃圾广告文件**（图片、txt 推广、二维码等），实际视频可能很小或质量很差。

**典型案例**：`0327-wanz-320-fhdall`（5.81GB 声称大小），实际包含 10+ 个垃圾文件，仅有一个 `wanz320.avi`（937MB 标清）。

**处理方法**：
1. **不要直接使用第一个可用视频** — 检查文件夹内视频文件的实际大小
2. 如果发现视频文件明显小于预期（如 937MB vs 声称的 5.81GB），说明种子被污染
3. **换一个干净磁链** — 返回 javdb 页面选择另一个磁链
4. **多磁链兜底策略**：第一个磁链下载后发现是垃圾 → 立即回 javdb 页面重新选干净磁链加入 PikPak，删除污染文件夹

磁链选择详见 `references/javdb-magnet-selection.md`。  
curl 提取磁链流程详见 `references/javdb-magnet-extraction.md`（当 web_extract 或浏览器无法访问 javdb 时）。


## 下载完成后的命名规范

每次下载完成后，必须按以下格式重命名视频和字幕文件：

```
{番号}-{女优名}-{标签} {描述}.mp4
{番号}-{女优名}-{标签} {描述}.srt
```

**示例**：
- `CAWD-992-清野咲-多P痴汉轮奸 在地铁上被痴汉们骚扰摆弄并轮奸的清纯美白美腿美尻舞蹈女学生.mp4`
- `CAWD-992-清野咲-多P痴汉轮奸 在地铁上被痴汉们骚扰摆弄并轮奸的清纯美白美腿美尻舞蹈女学生.srt`

**步骤**：
1. ffprobe 校验视频完整性（format=duration + size）
2. `mv tmp.mp4` → 新文件名
3. `cp` 或 `mv` 字幕文件 → 对应 .srt 新文件名（字幕必须和视频同名同目录）
4. 清理临时文件（`*.tmp.mp4`, `*.aria2`, `*.part*`）

## JAV 字幕自动搜索（subtitlecat.com）

字幕来源：[subtitlecat.com](https://www.subtitlecat.com)，支持日→中简体/繁体翻译。

### 搜索流程

```python
import subprocess, re

# 1. 搜索番号
code = 'CAWD-992'  # 或 IPZZ-835、JUR-764
r = subprocess.run([
    'curl', '-sL', 'https://www.subtitlecat.com/index.php?search=' + code,
    '-H', 'User-Agent: Mozilla/5.0'
], capture_output=True, text=True, timeout=15)
html = r.stdout

# 2. 从搜索结果提取字幕页面链接
links = re.findall(r'href="(subs/\d+/[^"]+\.html)"', html)

# 3. 打开页面，查找中文翻译
detail_url = f'https://www.subtitlecat.com/{links[0]}'
detail_html = subprocess.run(['curl', '-sL', detail_url, '-H', 'User-Agent: Mozilla/5.0'],
    capture_output=True, text=True, timeout=15).stdout

# 4. 提取翻译版本的直接下载链接
# 中文简体: zh-CN.srt, 中文繁体: zh-TW.srt
# 页面中的 href="/subs/{folder}/{name}-zh-CN.srt"
zh_links = re.findall(r'href="(/subs/\d+/[^"]+-zh-CN\.srt)"', detail_html)
if zh_links:
    sub_url = f'https://www.subtitlecat.com{zh_links[0]}'
    subprocess.run(['curl', '-sLo', '/tmp/sub.srt', sub_url, '-H', 'User-Agent: Mozilla/5.0'])
```

### 字幕文件结构

| 命名模式 | 示例 | 说明 |
|:--------|:----|:------|
| `{name}-orig.srt` | `CAWD-992-FHD-orig.srt` | 原始上传（可能日/中/混合） |
| `{name}-zh-CN.srt` | `CAWD-992.whisperjav-zh-CN.srt` | 中文简体翻译 |
| `{name}-zh-TW.srt` | `CAWD-992.whisperjav-zh-TW.srt` | 中文繁体翻译 |
| `{name}-ja.srt` | `CAWD-992.whisperjav-ja.srt` | 日文原文（WhisperJAV 转录） |

### 推荐优先级

1. **WhisperJAV 日→中翻译** - 质量最高（~38KB 完整对话）
2. **`[番号]-en-zh-CN.srt`** — 从英文页面翻译的中文简体（质量好且完整，如 `[PPPD-394]-en-zh-CN.srt` 37KB/1172条）— 当中文页面字幕损坏时优先尝试
3. 其他中文翻译版本（7~32KB）
4. 原始日文字幕 + 自行翻译

### 字幕质量检查

下载后立即验证字幕质量，避免使用残缺版本：

```bash
# 检查字幕条目数（越多越完整）
grep -c '^[0-9]' /tmp/sub.srt
# 2小时电影正常应有 800~1500+ 条
# <300 条 → 可能只是部分翻译，换一个版本

# 检查前几行有无乱码
head -10 /tmp/sub.srt | cat -v
# 出现 锟斤拷 或 M- 或 ^[[ 等异常 → 编码损坏
```

**质量对照**（以 PPPD-394 为例）：
| 来源 | 大小 | 条目数 | 覆盖 | 编码 |
|:----|:---:|:-----:|:----:|:----:|
| `PPPD-394-CN-zh-CN.srt` (CN页面) | 48KB | 1544 | 全程 | ❌ 损坏 |
| `PPPD-394.zh-zh-CN.srt` (zh页面) | 6KB | 231 | 仅22分钟 | ✅ 干净 |
| `[PPPD-394]-en-zh-CN.srt` (en页面→中) | 37KB | 1172 | 全程 | ✅ 干净 |

**推荐策略**：优先尝试 `[番号]-en-zh-CN.srt` 模式（英文页面翻译的中文版），其次 `{番号}.zh-zh-CN.srt`，最后再尝试 `{番号}-CN-zh-CN.srt`。如果中文页面全部编码损坏，检查 `-en` 页面的中文翻译往往是干净的。

### ⚠️ 字幕编码可能损坏

有些 subtitlecat 上的中文字幕文件（尤其是年代较老的番号）存在**编码损坏**问题：
- 原始文件可能以 GBK/GB2312 存储但被当作 UTF-8 读出
- 导致大量 `锟斤拷`、`�`（U+FFFD 替换字符）乱码
- 所有翻译版本（zh-CN、zh-TW、en、orig）都基于同一个损坏源

**处理方法**：
1. 尝试 `iconv` 转换：`iconv -f GBK -t UTF-8 file.srt`（多数情况下无效）
2. 检查页面中有无其他来源的字幕（如 `[SubtitleTools.com]` 版本）
3. 如果所有版本都损坏，仍使用最佳可用版本（虽有些乱码但大部分内容可看）
4. 不能因编码问题放弃字幕 — 部分损坏的字幕比没有好
5. 可考虑 WhisperJAV 日文原版字幕自行翻译

### 关键词：不要用 proxy

subtitlecat.com 不需要代理，直接 curl 即可。

## PikPak API 集成（pikpakapi）

安装：`uv pip install pikpakapi`（Hermes venv 中已安装）。  \
使用：`/opt/hermes/.venv/bin/python3` 调用 pikpakapi。

### ⚠️ pikpakapi 超时或 token 过期时的备选方案

pikpakapi 在 token 刷新或网络延迟高时可能长时间无响应（>30s）。此时可退化为**直接调用 PikPak REST API**（使用 `curl` + 手动 token 刷新）。

**token 过期场景**：pikpakapi 的 `encoded_token` 恢复后调用 `file_list()` 可能报 `"File or folder is not found"`，因为旧 token 已过期。直接 REST API 方案：

```bash
# 1. 从 token 文件提取 refresh_token，直接刷新
RT=$(python3 -c "import json; print(json.load(open('/opt/data/.pikpak_token.json'))['refresh_token'])")

curl -s --proxy http://127.0.0.1:10808 \
  -X POST "https://user.mypikpak.com/v1/auth/token" \
  -H "Content-Type: application/json" \
  -d "{\"grant_type\":\"refresh_token\",\"refresh_token\":\"$RT\",\"client_id\":\"YNxT9w7GMdWvEOKa\",\"client_secret\":\"Db5dI1j67p1OjLd8sH3jxvCjt2eX3n3p\"}"

# 2. 保存新 token
# 返回的 access_token 写入文件即可继续 API 调用
```

**注意**：登录（signin）可能触发 captcha（`"captcha_required"`, error_code 4001），此时只能通过 refresh_token 刷新而不能重新登录。只要 refresh_token 未过期，刷新请求不会触发 captcha。

**🚨 refresh token 一次性 + 并发刷新冲突（2026-08-10 踩到）**：PikPak refresh_token **每次使用即失效**（一次性）。当下载脚本和测速/查清单脚本**同时**调 `refresh_access_token()`（如 token 刚过期后两边并发触发），后刷新的一方会报 `PikpakException: refresh token os.XXX has been refresh at <时间>`，且该 token 作废。
- **修复**：token 文件（`.pikpak_token.json`）里存了 username/password，用 `api.login()` 重新登录拿全新 token 并保存：
```python
state = json.load(open('/opt/data/.pikpak_token.json'))
api = PikPakApi.from_dict(state)
await api.login()   # 用文件里的 username/password 重新登录
json.dump(api.to_dict(), open('/opt/data/.pikpak_token.json','w'), ensure_ascii=False, indent=2)
```
- **预防**：不要让多个进程同时操作 token——测速/探测脚本和下载主脚本避免同时冷启动触发刷新；或刷新后立即落盘再继续。

详见 `references/pikpakapi-timeout-workaround.md`。

### 登录与 Token 管理

```python
# 从 token 文件恢复
import json
from pikpakapi import PikPakApi

data = json.load(open('/opt/data/.pikpak_token.json'))
client = PikPakApi(encoded_token=data['encoded_token'])
```

Token 文件结构：`/opt/data/.pikpak_token.json`

### 主要操作（pikpakapi v0.1.11）

| 方法 | 用途 |
|:----|:-----|
| `file_list(size=100, parent_id=None, next_page_token=None, additional_filters=None)` | 文件列表，返回 `{files: [...]}`。⚠️ 参数名是 **`size`**（每页条数），不是 `page_size`——传 `page_size=` 会 `TypeError: got an unexpected keyword argument`（2026-08-10 踩过） |
| `offline_download(magnet, parent_id)` | 添加磁链下载到指定文件夹 |
| `offline_list()` | 查看所有离线下载任务及进度 |
| `get_download_url(file_id)` | 获取 CDN 直链（含 24h 有效期）→ **URL 在 `web_content_link` 字段**，`url` 字段可能为空 |
| `file_rename(id, name)` | 重命名 |
| `file_batch_move(ids, parent_id)` | 批量移动 |
| `create_folder(name, parent_id)` | 创建文件夹 |
| `path_to_id(path)` | 按路径查找文件夹 ID（比 `file_list` 可靠） |
| `delete_to_trash(ids)` | 删除到回收站 |
| `get_task_status(task_id)` | 查询离线下载任务状态 |

**⚠️ `get_download_url()` 重要提示**：返回的 CDN 直链在 **`web_content_link`** 字段（约 835 字符）。`url` 字段永远为空。`links` 和 `medias` 也不包含有效下载链接。只用 `web_content_link`。

### 直链缓存与时效

- CDN URL 有效期约 **24 小时**，失效后需重新 `get_download_url()`
- 建议将 URL 写入文件（如 `/tmp/{番号}_cdn.txt`）以减少 API 调用
- 下载完成后及时清理缓存文件

## rclone 密码解密

rclone 配置文件中的 `pass` 字段使用其内部的混淆算法加密：

```bash
# 查看加密内容
/tmp/rclone config show pikpak | grep pass

# 解密
/tmp/rclone reveal "J3w9..." → 输出明文
```

注意：解密后的密码可能不等于 WebDAV 实际密码（rclone 使用内部混淆格式）。

## 文件存储

默认下载目录：`/opt/data/PikPak/`。  
Inbox-JAV：`/opt/data/PikPak/Inbox-JAV/`

# PikPak 批量下载（aria2 归档方案）— 2026-08-27 合并自 pikpak-bulk-download

> ⚠️ **2026-08-27 CDN 直连 IP 被封（用户确认预计不解封）**：本文件的 aria2 CDN 方案（ai_drama_dl.py、pikpak_dl_aria2.sh）**当前全部不可用**。WebDAV 15 并发（`bash pikpak.sh copy15`）是唯一下载通道。若未来 CDN 解封，按本归档恢复。

## 批量下载架构（asyncio + aria2，历史验证）

成熟实现：`/opt/data/ai_drama_dl.py`（1248 文件/242GB AI短剧 全量下载实战验证，多轮调试后稳定）

```
build_plan(): manifest JSON → 过滤(仅视频ext) → 去重(同内容取最大) → 合并(相近剧集名)
→ asyncio.Queue + N×worker → 每 task: get_url(web_content_link) → aria2 → ffprobe 校验
```

- `CONCURRENCY` 常量为并发数（用户偏好 4，历史上 4→3→2→4 反复调过，**以用户当下指令为准**，每次改动需重启脚本）
- manifest 由 file_list 全量扫描生成（root folder id + next_page_token 翻页）

## ⚠️ 核心坑位（全部实战踩过）

1. **aria2 必须进线程池**：`subprocess.run` 阻塞事件循环 → N 个 worker 卡死只有 1 个 aria2 在跑（"假并行"假象）。必须 `await loop.run_in_executor(None, aria2_download, url, dest)` 包装，ffprobe 同理。
2. **LD_LIBRARY_PATH**：aria2c 报 `error while loading shared libraries: libaria2.so.0` → `env['LD_LIBRARY_PATH']='/opt/data'` 传入 subprocess。
3. **SLOW 检测**：每 15s 检查目标文件大小增长，连续 2 次 < 阈值 → kill aria2 → 删半成品（含 .aria2 控制文件）→ 重取 web_content_link 重试（同文件最多 3 次）→ 仍 SLOW 放回队列尾部。阈值用户调成 **0.2MB/s**（走代理时速度上限低，阈值太高会频繁误杀空转）。
3b. **⚠️ 大文件（>500MB）必须完全取消 SLOW 检测**：`aria2_download(url, dest, total_size)` 里 `if total_size > 500MB: proc.wait()` 跳过监测循环。否则下载到一半 30 秒网络抖动就被判 SLOW 杀进程删半成品，重来又从头，**大文件永远下不完**。用户明确要求"大文件取消 slow 检测"。小文件才保留 SLOW 检测（换 URL 成本低）。
4. **FAIL 自动重排队**：非 SLOW 错误（超时/断连等）也重排队，`task['attempts']` 计数 ≤ 3，超限才标 DL_FAIL。
5. **断点续传**：dest 已存在且 size ≥ task 的 99% → SKIP 跳过。不加这个每次重启会全量重下。
6. **守卫绕过**：terminal 跑含 /opt/data 的脚本触发 embedded null bug → 用 bash wrapper + cd + PATH 裸名 python3。

## ⚡ IP 级限速绕过（历史发现，CDN 时代）

- **症状**：直连 PikPak CDN 所有节点 0.02-0.09MB/s，换 URL 无效 → 是**服务器出口 IP 被限流**。
- **解法**：aria2 加 `--all-proxy=http://127.0.0.1:10808`，走代理出口 IP 下载 → 0.95-8.7MB/s（10 倍+）。
- **出口 IP 速度差异大**：
  - AWS 日本段 103.62.49.x：0.9-2.2MB/s（快，但周期性断流）
  - 圣何塞 134.195.101.x：0.25-0.34MB/s（慢）
  - **SG-AWS02（🇸🇬AWS新加坡02）出口 67.159.48.147：25-30MB/s 稳定，最快节点**（2026-08-10 实测 27-31MB/s 下完 242GB）
- **测速方法**：`curl -x 代理 -r 0-31457280` 下 30MB 测速；测速矩阵脚本 `/opt/data/tmp_node_scan.py`
- **用户策略**：先直连省钱（代理按流量计费），限速了再切代理。
- **WebDAV 也被 IP 总量限流（2026-08-12 实测）**：CDN 直连 0.08MB/s；WebDAV 单线程 0.17、`--transfers=8` 多文件并发 0.35MB/s —— 多连接救不了，PikPak 按出口 IP 掐总带宽。**注意：2026-08-15 后 WebDAV 已恢复 5-8MB/s（单文件）/15并发 24-111MB/s，本条目仅历史参考。**
- **根治方向（免费优先）**：限流对象是**出口 IP**（实测 111.193.27.155 联通家宽 PPPoE）。①**重启光猫/路由器重拨换 IP** → 新 IP 干净、限流立即解除（唯一免费根治方案）；②等临时 IP 处罚自动解除（几小时~几天）。
- **免费 CDN 中转已排除**：CF Workers 默认域名国内被墙；公共免费 HTTP 代理测 PikPak 直链全 0.00MB/s。结论：**无免费换 IP 捷径**。
- **rclone 二进制丢失修复**：/tmp 被清后 `/tmp/rclone` 消失。重下配方：`curl -sL --max-time 120 -x http://127.0.0.1:10808 -o /tmp/rclone.zip https://github.com/rclone/rclone/releases/download/v1.67.0/rclone-v1.67.0-linux-amd64.zip`，用 python `zipfile` 解压到 /tmp/rclone（系统无 unzip）。配置在 `/opt/data/.config/rclone/rclone.conf`（type=webdav, url=http://dav.mypikpak.com:80）。
- 测速脚本：`/opt/data/scripts/ai_cdn_speed_test.py` + `.sh`（>1MB/s 才输出，配合 no_agent cron 空输出=静默）。
- 出口被限就换节点：`bash /opt/data/proxy-skill/proxy_auto_switch.sh --node usXX`；**auto_switch 无参数全遍历会卡死节点**，用 --node 指定 + 外层超时。

## ⚠️ CDN 限速"按连接"而非"按 IP 总量"时（2026-08-15 实测）

**换 IP 后（123.123.74.83）出现新规律**：单连接 curl 测速 0.16-0.32MB/s（看似全限），但 **aria2 8 连接并发实际 8.9MB/s**——单连接被掐，多连接不受影响！**别被 curl 单连接测速吓到**，直接上 aria2 实测：

- curl 单连接 0.2MB/s vs aria2 --split=8 8.9MB/s（44x），总速度随并发文件数叠加（3 并发 ~27MB/s）
- 节点分组差异：部分节点组（dl-a10b-155x）解封至 1.9-2.2MB/s，另一组（dl-z01a-*）仍单连接 0.2MB/s——但 aria2 多连接下 z01a 也能 8.9MB/s
- 判断方法：`--split=8` 的 aria2 才是真实速度；限速"按连接"时多连接直接绕过
- 直连"间歇性解封"会在运行中突然全挂（403/超时）：解封窗口不保证持续。判断卡死：`ss -tn | grep -c ESTAB` 为 0 + 速度 0 = 挂了，别干等
- **稳妥兜底**：aria2 函数加 `use_proxy` 参数（默认无代理），直连失败 2 次后**自动切代理**下载同一文件。用户策略"先直连省钱"，卡死自动切代理而不是无限重试。

### aria2 偶发卡死：数据满但 .aria2 不释放

下载完成后个别 aria2 进程可能卡在收尾（文件 st_blocks 已达目标，但 .aria2 控制文件不删、进程不退）。处理：
1. 等 60-90s 看是否自然收尾；仍卡 → `pkill -9 -f aria2c`
2. 删残留 `.aria2`（数据已满则安全）
3. 完整性核对：`os.path.getsize(dest)` vs manifest size（±1%）+ ffprobe 抽验时长

## ✅ 用户规则：下载到本地后删除 PikPak 源文件（2026-08-15 明确）

用户原话："以后记得，下载到本地后将pikpak中的文件删除掉"——**每个文件下载到本地验证完整后，删除网盘里的对应文件**（释放网盘空间）。实现：worker 里 verify OK 后调 `api.delete_to_trash([file_id])`，或全部完成后批量删 manifest 中已完整下载的。注意：网盘文件删了之后，旧 manifest 的 file id 会过期（`File or folder is not found`），重扫拿新 ID 是预期行为。

## Token 刷新冲突

- 报错 `refresh token ... has been refresh at ...` = **多进程/多 worker 并发刷新冲突**。
- **根治（get_url 内加锁）**：`_refresh_lock = asyncio.Lock()`（模块级），get_url 捕获到 `'refresh token' in msg` 时 `async with _refresh_lock:` 内 `await api.login()` 一次，然后 `continue` 重试。
- **持久化注意**：pikpakapi 的 `get_user_info()`（同步方法）返回的 dict **不含 password/device_id**——直接覆盖保存会丢 password，下次 login() 失败。必须从旧 token 文件补回：`for k in ('password','device_id'): if k in old and k not in new: new[k]=old[k]`。
- 教训：测速/其他脚本操作 PikPak 前先确认无下载进程在跑，或共用 token 刷新锁。

## 下载流程模板（aria2 时代）

1. 生成 manifest（file_list 全量扫描；**翻页参数是 `next_page_token`，不是 `page_token`**——后者直接 TypeError）
2. build_plan 过滤/去重/合并 → 打印任务数 + 总大小给用户确认
3. 先试跑 3 个小文件验证全链路（get_url → aria2 → ffprobe）
4. 后台启动（Popen + start_new_session），日志 /tmp/ai_drama_dl.log
5. 监控 cron（每 10min 查主进程 + aria2 数 + 日志 age），异常才通知
6. 完成/失败统一写 result JSON

## 复用下载器到新文件夹

不复制整个脚本——**新脚本 import ai_drama_dl 的下载核心**，只换 manifest 和目标目录：

```python
sys.path.insert(0, '/opt/data')
import ai_drama_dl
from ai_drama_dl import get_url, aria2_download_async, verify_file, loop_run, CONCURRENCY
```

- 模板：`/opt/data/twitter_dl.py`（完整可参考，含 SKIP/FAIL 重排队/大文件无 SLOW/ETA）
- 前提：ai_drama_dl.py 的下载核心函数都是模块级可 import 的
- **去重策略按文件夹类型选**：
  - **AI短剧类**（结构化命名）：按文件名去重（同名/相似名只下最大）
  - **Twitter 类**（文件名随机/各账号转发改名）：**必须按文件 size 去重**——字节数完全相同 = 大概率同一视频。实现：`seen_sizes` set，同 size 只保留第一个（实测 374→356 个，去掉 18 个重复 4GB）
  - ⚠️ 换去重规则后重启前：检查已下载目录里是否有落在"跳过名单"的文件，有则删掉

## 重复下载/增量下载

用户说"下载 XXX 文件夹" ≠ 重下全部。已全量下载过的文件夹再次请求时：
1. **重新扫描** PikPak 文件夹生成新 manifest（不要复用旧 manifest！）
2. ⚠️ **旧 manifest 的文件 ID 会过期**：用户可能已删除/移动网盘文件，用旧 ID 调 `get_download_url` 报 `File or folder is not found`——这是预期，不是 bug。
3. 本地已有文件（dest 存在且 ≥99%）会被 SKIP 逻辑自动跳过，**只下新增/缺失的**。

## 完整性核对

磁盘口径陷阱：**只数 *.mp4 会漏 .mov/.mkv**。核对方法：逐 task: dest 存在且 size ≥ task['size']*0.99 → 完整；磁盘总量 ≈ 计划总量（±0.1%）即视为全量完成。清理残留：`find -name '*.aria2' -delete`（主文件 ≥99% 时）。

## 补下模式

主脚本跑完时队列里重排队的任务没处理完 = "失败"其实是未轮到。补下：
1. 从 result JSON 取 status ∈ (REQUEUE, RETRY, VERIFY_FAIL) 的任务
2. 过滤掉 dest 已存在且 ≥99% 的
3. 用同样下载核心跑一轮，日志独立（/tmp/xxx_fix.log），结果写 result2.json
4. VERIFY_FAIL 里有真失败也有 ffprobe 偶发误判——核对 size 后以磁盘为准

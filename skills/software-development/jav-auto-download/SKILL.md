---
name: jav-auto-download
title: JAV 自动下载智能体
description: 给定番号 → 搜javdb获取磁链 → 按规则选择（字幕优先/高清优先）→ PikPak离线下载(多文件自动选单视频) → 无字幕则从subtitlecat获取中文
---

# JAV 管理器 — 统一下载+本地同步

一本搞定：搜索磁链 → PikPak 下载 + 清理广告 → **自动 rclone 到本地**。看门狗也集成在内。

> ⚠️ **入库目标目录（2026-08-04 用户纠正）**：番号视频（jav-auto-download）下载完成后**必须存到 `/opt/data/PikPak/Inbox-JAV/`**，不是 `/opt/data/Movie/`！Movie 目录只给**电影下载 skill**（普通电影/剧集）用。两个规则不要混用。

## 用法

```bash
# 下载指定番号（全程自动，含本地同步——rclone 同步，大文件可能超时）
/opt/data/.venv/bin/python3 /opt/data/jav_manager.py DSOD-005

# 跳过 rclone 同步（推荐，后续用 aria2 并行下载）
/opt/data/.venv/bin/python3 /opt/data/jav_manager.py --no-sync DSOD-005

# 批量处理多个番号
/opt/data/.venv/bin/python3 /opt/data/jav_manager.py --no-sync \
  PPPE-419 SNOS-227 CAWD-992 JUR-751 EBWH-331 IPZZ-835 \
  RKI-741 MIMK-267 FPRE-232 SNOS-163 JUR-686 EBWH-322 ABF-334

# 或者告诉我番号，我帮你执行
```

## 脚本文件

- **主脚本**：`/opt/data/jav_manager.py`（420行）← 统一入口
- ~~旧脚本~~：`jav_agent.py` / `pikpak_watch.py`（已废弃，被管理器取代）

## 完整工作流程

```
┌─────────────────────────────────────────────────────────┐
│ jav_manager.py DSOD-005                                   │
├─────────────────────────────────────────────────────────┤
│ Phase 1: javdb 搜索                                       │
│   javdb搜索 → 获取磁链 → 选最佳（字幕优先/高清优先）        │
├─────────────────────────────────────────────────────────┤
│ Phase 2: PikPak 离线下载                                   │
│   添加磁链 → 检测多文件 → 删广告文件 → batchMove移出       │
│   → 重命名(保留-C后缀) → 删空文件夹                        │
├─────────────────────────────────────────────────────────┤
│ Phase 2.5: 字幕搜索（-C内嵌字幕版跳过，仅裸磁链版）       │
│   subtitlecat搜索 → 选简体中文 → 下载SRT到本地目录          │
├─────────────────────────────────────────────────────────┤
│ Phase 3: 本地同步                                          │
│   --no-sync 跳过 → 用 aria2 CDN 并行同步（推荐）           │
│   或 rclone WebDAV 同步（旧方式，大文件易超时）            │
│   （如果 PikPak 还没下载完，看门狗稍后自动完成）          │
├─────────────────────────────────────────────────────────┤
│ jav_manager.py --watch（看门狗模式，每10分钟）               │
│   检查PikPak → 同步新文件 → 1小时无更新自动休眠             │
└─────────────────────────────────────────────────────────┘

## 关键步骤详解

### 1. javdb 搜索（依赖 xray 代理）

- 先请求 `/over18?respond=1` 设置 cookie
- 搜索 `https://javdb.com/search?q={code}&f=all` ← ⚠️ 必须加 `&f=all`，否则只返回"热门推荐"
- 在卡片中匹配 `<strong>{番号}</strong>` 精确匹配（卡片结构：`<div class="video-title"><strong>{番号}</strong> 标题</div>`）

### 2. 磁链提取与选择

#### 如何读取 javdb 页面的磁链信息

javdb 每个磁链下方直接标注文件大小（如 `8.71GB`）和清晰度（`高清`/`標清`）以及字幕信息（`字幕`/`无码`）。不要猜测磁链对应的文件大小——直接从页面用 curl+grep 提取磁链和属性：

```bash
curl -s --proxy http://127.0.0.1:10808 \
  -H "User-Agent: Mozilla/5.0" \
  "https://javdb.com/v/VIDEO_CODE" | grep -oP '(magnet:[^"&]+[^"]*|[0-9]+\.[0-9]+ *GB|中字|字幕|无码|破解|HD|高清)' | head -60
```

输出结构：每个磁链 URL 后面紧跟着它的文件大小和标注。`dn=` 参数包含磁链的文件名（如 `FNS-216-UC`、`SNOS-324-U.无码破解`）。

#### 磁链选择规则（按优先级排序）

1. **清晰度优先**：选文件大小最大的版本（高清优先），不看是否带字幕。
2. **内嵌中文字幕次选**：同清晰度（大小接近）的磁链中，优先选文件名含 `-C`、`-UC`、`中字`、`内嵌`、`SUB`、`字幕` 等标记的内嵌字幕版。
3. **禁止 `-U`（无码破解版）**：文件名含 `-U`（非 `-UC`）或 `无码破解` 标注的磁链**一律禁止选择**。用户明确禁止下载无码破解版。`-UC`（无码中字版）是可接受的。
4. **大小过滤**：视频文件小于 **2GB** 的**跳过不下载**（清晰度太差）。必须在当前番号的 javdb 页面其他磁链中找 >=2GB 的高清版。如果当前番号仅有的磁链都 <2GB，如实告知用户。

### ⚠️ 磁链选择后字幕判断流程（2026-07-18 用户纠正）

**重要**：流程顺序必须是 **先看磁链版本再决定是否需要外挂字幕**，不是先搜字幕再找磁链。

```
① javdb 找磁链
    │
    ├─ 磁链文件名含 -C / -UC / 中字 / 内嵌 / SUB / 字幕
    │     → 视频已内嵌字幕轨道，无需 subtitlecat
    │
    └─ 纯番号（无字幕后缀）
          → 去 subtitlecat 下载外挂 .srt
```

**对应到 Phase：**
- 有内嵌字幕的磁链（-C/-UC等）→ **跳过 Phase 2.5**（不搜索 subtitlecat）
- 裸磁链（纯番号如 `FNS-216`）→ **执行 Phase 2.5**（subtitlecat 搜索 + 下载 .srt）

**不要**用 subtitlecat 的结果反向决定是否下载——应该以磁链文件名是否标注含字幕为准。subtitlecat 上的字幕即使存在也是外挂的，不需要为内嵌字幕版再下一份。

### 3. PikPak 离线下载 + 广告文件清理

> ⚠️ 如需跳过无码破解版（-UC/-U），参见 `references/manual-override-no-uncensored.md` 的手动覆盖工作流。

磁链经常包含**文件夹**（主视频 + 广告视频HTML等垃圾文件），例如 DSOD-005-C 的文件夹结构：

| 文件 | 说明 |
|:----|:----:|
| `489155.com@DSOD-005-C.mp4` (6.09 GB) | ✅ 主视频（含内嵌字幕） |
| `社 區 最 新 情 報.mp4` (14.4 MB) | ❌ 广告 |
| `台湾uu美少女直播 20年信誉保证服务全球.mp4` (13.2 MB) | ❌ 广告 |

脚本会在下载完成后自动清理广告，只保留主视频：

```
Step 4: PikPak下载...
  添加到 PikPak: DSOD-005-C (5.70 GB)
  状态: Saving
  检查是否有广告文件...
    [1/15] 子文件 3 个 全部就绪
  找到 2 个广告文件，删除中...
    🗑️ 社 區 最 新 情 報.mp4 (14.4 MB)
    🗑️ 台湾uu美少女直播 20年信誉保证服务全球.mp4 (13.2 MB)
  ✅ 广告已清除，保留: 489155.com@DSOD-005-C.mp4
```

**技术实现** (`pikpak_cleanup_ads`)：

1. `offline_download()` 添加磁链 → 拿到 `file_id`（可能初始为空，需轮询 20s）
2. 等待 30s（最多 15 次 × 2s）直到 `offline_file_info(file_id)` 返回 `kind=drive#folder`
3. 用 `file_list(parent_id=file_id)` 列出子文件
4. 等待所有子文件 `phase=PHASE_TYPE_COMPLETE`
5. 用 `delete_to_trash([...])` 批量删除广告文件
6. **用 `batchMove` API 将视频移至父目录**（PATCH parent_id 无效，必须用专用的 `drive/v1/files:batchMove` 端点）
7. **重命名：保留 `-C` 后缀** — 文件名中的 `-C` 表示内嵌中文字幕，重命名时保留（如 `489155.com@DSOD-005-C.mp4` → `DSOD-005-C.mp4`）。换用裸番号 `DSOD-005-C.mp4` 而不带广告前缀
8. **最后删除空文件夹** — ⚠️ 重命名必须在删除文件夹之前执行（顺序：move → rename → delete_folder），否则 PikPak 报 "file_rename_in_recycle_bin"

**视频文件识别规则**：
- 扩展名：`.mp4/.mkv/.avi/.wmv/.mov/.flv/.ts/.m4v/.webm`
- 优先选文件名**含番号**的 → 如 `489155.com@DSOD-005.mp4` 含 `DSOD-005`
- 多个匹配时选**最大**的
- 无匹配时选最大的视频文件
- 其余文件（非视频/非番号）一律删除

> ⚠️ **不要用 `selected_files` PATCH 方法！** PikPak 解析磁链极快（从 "not found" 直接跳到 "PHASE_TYPE_COMPLETE" 只需 4-6s），PATCH 来不及生效，返回 `file_nothing_updated`。**删除法是唯一可靠方案**。

### ⚠️ PikPak Inbox-JAV 文件夹 ID 可能变化

PikPak 的 Inbox-JAV 文件夹 ID **不是永久固定的**。跨会话操作（重启代理、重新登录、Docker 容器重建）后 parent_id 可能改变。

**症状**：用之前硬编码的 `parent_id` 调用 file_list 返回空结果或不正确的文件列表；手动添加磁链时返回 `file_not_found` / `File or folder is not found`。

**修复**：每次操作前动态获取当前 Inbox-JAV 的 folder ID：

```python
# 方法1：pikpakapi path_to_id
result = await client.path_to_id('/Inbox-JAV')
inbox_id = result[0]['id']

# 方法2：REST API 搜索
# GET /drive/v1/files?parent_id=*&page_size=100
# 从返回中找 name='Inbox-JAV' 且 kind='drive#folder' 的条目
```

**规则**：不要在代码中硬编码 `parent_id`。每次新会话开始时从活跃会话状态或 REST API 重新获取。

### 手动搜索 javdb 磁链（当 web_extract / browser 不可用时）

当工具层屏蔽 javdb（如 `web_extract` 返回 `"Blocked: private/internal network"`、浏览器超时）时，可以用 **curl + 代理** 直接获取页面全文，再用 grep 提取磁链：

```bash
source /opt/data/home/.bashrc  # 设置代理 env

# 1. 下载页面（通过代理访问）
curl -s --proxy http://127.0.0.1:10808 \
  -H "User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36" \
  "https://javdb.com/v/VIDEO_CODE" -o /tmp/page.html

# 2. 提取磁链
grep -oP 'magnet:\?xt=urn:btih:[a-zA-Z0-9]+[^"]*' /tmp/page.html | sort -u
```

javdb.com 直连也可访问（当前 IP 实测 200 OK），优先用直连；如果直连 403/超时，走 sing-box SOCKS5 代理。

### ⚠️ PikPak 死种/无种磁链处理

某些磁链在 PikPak 上会创建任务但**永远不进入下载**——`offline_file_info(task_id)` 反复返回 `"File or folder is not found"`，即使等待 60+ 秒。任务最终从离线列表消失，不留痕迹。

**特征：**
- `offline_download(magnet)` 成功返回 task，含 `file_id` → 但 `offline_file_info(task_id)` 始终报 "File or folder is not found"
- 60 秒后 `offline_list()` 中任务已消失
- 文件从未出现在 PikPak 的任何目录

**常见于：** 公开 tracker 的裸磁链（非 `-C`/`-UC` 版），尤其是标准版的非付费种子。PikPak 的种子网络可能没有该资源的有效种源。

**处理方案（按优先级）：**

1. **换磁链** — 同一个番号在 javdb 上通常有多个磁链（不同 btih）。选另一个来源重试（如 kks11.cc 版、不同 tracker）
2. **换 API 方式（新增 2026-07-09）** — 当直接用 REST API curl 添加磁链返回 `phase=waiting` 且永远不进入下载时（如 DSOD-008 案例），改用 **pikpakapi 的 `offline_download(magnet, parent_id=inbox_id)` 方法**。前一次用 REST API 直调始终 `phase=waiting`，同一磁链用 pikpakapi 立即返回 `PHASE_TYPE_RUNNING` 并成功进入下载队列。
3. **换来源** — 检查 javdb 页面的其他标签页（如「百度網盤」链接）
4. **定时重试** — 非高峰时段（如 19:00-21:00）用 cron 自动重试，有时 PikPak 的种子缓存会刷新
5. **aria2 直拉**（最后手段）— 用 aria2 `--enable-dht` 直接磁链下载，走 P2P 网络。速度不确定，可能很慢或也下不动
6. **如实汇报** — 所有方案均失败时告知用户，用户可能知道其他可用来源

## PikPak API token 多进程冲突

启动新 `PikPakApi` 实例时，如果另一个进程此前已刷新过 token，新实例的 refresh 操作会失败：`invalid refresh token for it may be has been refreshed by other process`。

**原因**：每个 `PikPakApi` 实例在首次 API 调用前自动 refresh token。jav_manager.py 的 Phase 2 已刷新 token，后续在另一个线程/进程中新建实例又试图刷新，导致冲突。

**修复**：建立新实例后，手动设回已保存的 access_token / refresh_token，跳过自动刷新：

```python
state = json.load(open('/opt/data/.pikpak_token.json'))
client = PikPakApi(encoded_token=state['encoded_token'])
client.access_token = state.get('access_token', '')
client.refresh_token = state.get('refresh_token', '')
client.user_id = state.get('user_id', '')
client.device_id = state.get('device_id', '')
# 此时首次 API 调用不会触发 refresh，而是用已有的 token
```

## REST API 直调方案（当 pikpakapi 不可用或 token 过期时）

当 pikpakapi 因 token 过期（`invalid refresh token for it may be has been refreshed by other process`）或超时而无法使用时，可退化到直接 REST API 调用。

### Token 刷新（避免 captcha）

**不要重新登录**（signin 会触发 captcha: `error_code=4001, captcha_required`）。用 refresh_token 直接刷新：

```bash
RT=$(python3 -c "import json; print(json.load(open('/opt/data/.pikpak_token.json'))['refresh_token'])")

curl -s --proxy http://127.0.0.1:10808 \
  -X POST "https://user.mypikpak.com/v1/auth/token" \
  -H "Content-Type: application/json" \
  -d "{\"grant_type\":\"refresh_token\",\"refresh_token\":\"$RT\",\"client_id\":\"YNxT9w7GMdWvEOKa\",\"client_secret\":\"Db5dI1j67p1OjLd8sH3jxvCjt2eX3n3p\"}"
# 返回新 access_token 和 refresh_token，写入文件保存
```

### 列出 Inbox-JAV 文件

```bash
AT=$(python3 -c "import json; print(json.load(open('/opt/data/.pikpak_token.json'))['access_token'])")

# 获取 Inbox-JAV 文件夹 ID
curl -s --proxy http://127.0.0.1:10808 \
  -H "Authorization: Bearer $AT" \
  "https://api-drive.mypikpak.com/drive/v1/files?parent_id=*&page_size=100" \
  | python3 -c "import json,sys; [print(f['id'],f['name']) for f in json.load(sys.stdin).get('files',[]) if 'Inbox' in f['name']]"

# 列出文件
INBOX_ID="..."
curl -s --proxy http://127.0.0.1:10808 \
  -H "Authorization: Bearer $AT" \
  "https://api-drive.mypikpak.com/drive/v1/files?parent_id=$INBOX_ID&page_size=50"
```

### 添加磁链

```bash
MAGNET="magnet:?xt=urn:btih:..."
curl -s --proxy http://127.0.0.1:10808 \
  -X POST "https://api-drive.mypikpak.com/drive/v1/files" \
  -H "Authorization: Bearer $AT" \
  -H "Content-Type: application/json" \
  -d "{\"kind\":\"drive#file\",\"parent_id\":\"$INBOX_ID\",\"upload_type\":\"UPLOAD_TYPE_URL\",\"url\":{\"url\":\"$MAGNET\"}}"
```

### 获取 CDN 直链（文件非文件夹）

```bash
FILE_ID="..."
# 用 _magic=1 而不是 batch_download_url（后者对文件夹内文件返回 unimplemented）
curl -s --proxy http://127.0.0.1:10808 \
  -X GET "https://api-drive.mypikpak.com/drive/v1/files/$FILE_ID?_magic=1" \
  -H "Authorization: Bearer $AT" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('web_content_link','') or d.get('links',{}).get('application/octet-stream',{}).get('url',''))"
```

### 递归处理文件夹内文件

磁链通常创建文件夹（`kind=drive#folder`），内部含广告文件和视频：

```python
import requests, json

AT = json.load(open('/opt/data/.pikpak_token.json'))['access_token']
headers = {'Authorization': f'Bearer {AT}', 'Content-Type': 'application/json'}
proxy = {'http': 'http://127.0.0.1:10808', 'https': 'http://127.0.0.1:10808'}

# 列出文件夹
r = requests.get(
    f'https://api-drive.mypikpak.com/drive/v1/files?parent_id={folder_id}',
    headers=headers, proxies=proxy, timeout=15)
files = r.json().get('files', [])

# 识别视频（通常最大文件，>1GB）
for f in files:
    size = int(f.get('size', 0))
    name = f['name']
    kind = f['kind']
    print(f'{name}: {size/1024**3:.2f}GB ({kind})')

# 广告文件通常 <20MB，视频 >1GB
```

### ⚠️ 注意

- **`batch_download_url` 不支持文件夹内文件**：POST `.../:batch_download_url` 返回 `unimplemented`。正确方式是用 `GET .../{id}?_magic=1`
- **Inbox-JAV 文件夹 ID 会变**：跨会话后需重新查找，不要硬编码
- **refresh_token 会过期**：长期未使用的 token 会彻底失效，此时只能重新登录（需 captcha 处理）

### 4. 字幕补充（仅裸磁链版，-C内嵌字幕版跳过）

**前置判断**：如果选中的磁链文件名含 `-C`、`-UC`、`_C`、`_UC`、`中字`、`内嵌`、`SUB` 等标记，说明视频已内嵌字幕轨道，**跳过** subtitlecat 搜索。

```python
# jav_manager.py 中实现
magnet_name = selected_magnet.get('name', '')
skip_subs = any(s in magnet_name.upper() for s in ['-C', '-UC', '_C', '_UC', '中字', '内嵌', 'SUB', '字幕'])
if skip_subs:
    print('📀 内嵌字幕版，跳过 subtitlecat 下载')
    return  # 不下载独立 .srt
```

仅对裸磁链（`REAL-766`、`SONE-028` 等不含字幕后缀的）执行 subtitlecat 搜索。

- 搜索 `https://www.subtitlecat.com/index.php?search={code}`
- 选下载量最高的结果
- 语言优先级：zh-CN > zh-TW > zh
- 下载 SRT，重命名与视频文件一致（如 `HMN-850.mp4.srt`）

**如果直接搜索没找到中文**：检查 Eng 页面（如 `subs/1432/DRPT-109%20Eng.html`）。有些番号的中文翻译版本放在了英文页面上（文件名 `{番号} Eng-zh-CN.srt`），直接搜索番号只能看到 "Eng" 结果，点进去才有 zh-CN。下载量可能低于原版页面但质量相同。

详见 `references/subtitlecat-scraping.md`。

### 5. 本地同步（Phase 3 — aria2 CDN 并行下载 **推荐** / rclone 备选）

**默认的 rclone Phase 3 容易对大文件（>4GB）超时**。因此 jav_manager.py 支持 `--no-sync` 参数跳过 Phase 3，改用 aria2 同步：

```bash
# Phase 1-2.5 完成后跳过 rclone，后续用 aria2
/opt/hermes/.venv/bin/python3 jav_manager.py --no-sync 番号1 番号2 ...
```

**推荐方案（aria2 并行同步）**：

```
Phase 1-2: jav_manager.py --no-sync → 加入 PikPak + 字幕
              │
              ▼
Phase 3a: check_pikpak_dl.py → 获取 CDN 直链到 /tmp/pikpak_urls.json
              │
              ▼
Phase 3b: pikpak_dl_aria2.sh -j 5 → aria2 并行下载到本地
              │
              ▼
           ffprobe 校验完整性
```

**步骤详解：**

**Phase 1-2（已修改支持 `--no-sync`）：**
1. 运行 `/opt/data/.venv/bin/python3 /opt/data/jav_manager.py --no-sync 番号1 番号2 ...`
2. 脚本搜索 javdb → 加 PikPak → 清理广告 → 重命名 → 找字幕，**跳过** rclone 同步
3. 支持批量处理多个番号（脚本自动循环）

**Phase 3a：check_pikpak_dl.py（获取 CDN 直链）**
- 脚本：`~/.hermes/scripts/check_pikpak_dl.py`
- 列出 PikPak `/Inbox-JAV` 中所有 mp4 文件，针对每个未在本地的文件
- 调用 `api.get_download_url(full_file_id)` 获取 CDN 直链
- 保存到 `/tmp/pikpak_urls.json`
- **关键坑：必须用完整的 file ID（如 `VOw8FDYPL1n6I5mr2b3QkmiLo2`），截断的 ID（`VOw8FDYPL1n6I5mr2b3Q`）会被 PikPak API 返回 "File or folder is not found"**
- 可作为 no_agent cron 每 5 分钟运行一次（cron job: `504e2a379e7d`）
- 也支持批量：自动遍历 Inbox-JAV 中所有文件

**Phase 3b：pikpak_dl_aria2.sh（aria2 并行下载）**
- 脚本：`/opt/data/pikpak_dl_aria2.sh`
- 自动读取 `/tmp/pikpak_urls.json`
- 用 aria2 8 连接分片 + 最多 5 个文件并行：
  ```bash
  # 下载全部（默认并行5个）
  /opt/data/pikpak_dl_aria2.sh
  
  # 指定并行数（最大5）
  /opt/data/pikpak_dl_aria2.sh -j 3
  ```
- 速度 **4~14 MB/s** 稳定（单个文件），总带宽约 **10 MB/s**（5 个并行时均分）
- aria2（C 实现）比 Python 多线程（0.3 MB/s）快 18 倍，比 rclone（~50KB/s→503）快 50-100 倍
- 每个文件使用 8 连接分片，内置断点续传和重试
- 排到下个文件：前一批完成后自动启动下一批（队列吃满 5 并行）

**校验（关键步骤）：**
```bash
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 file.mp4
# 输出数值(秒) → ✅ | "moov atom not found" → ❌ 损坏
```
不要依赖 `du`/`stat`/`ls -lh`——aria2 预分配文件，大小准确不代表数据完整。

**⚠️ 坑（死进程覆盖）：**
旧会话残留的 Python/rclone 后台进程会在 aria2 完成后覆盖已下载文件，导致 `moov atom not found` 损坏。
**下载前必须：**
```bash
pkill -f pikpak_cdn_dl.py 2>/dev/null
pkill -f rclone.*Inbox-JAV 2>/dev/null
sleep 1
```
**下载后必须 ffprobe 逐文件校验**。损坏时：`rm -f file.mp4` → 杀旧进程 → sleep 1 → 重下。
同时清理旧 .part 碎片：`rm -f /opt/data/PikPak/Inbox-JAV/*.part*`

更多 aria2 细节参看 `pikpak-webdav-manager` 技能。

**rclone 备选方案（旧方式，不推荐）：**
1. 查询 `pikpak:/Inbox-JAV` 的文件列表（`rclone lsjson`）
2. 比对 `.inbox_record.json` 排除已下载
3. `rclone copy` 到本地
4. 如果 PikPak 还没下载完，最长等 30 秒轮询
- 注意：rclone WebDAV 对本服务器 IP 限流严重（1.4MB/s → 50KB/s 持续降速 → 503）

**⚠️ 不要走代理下载**（代理按流量收费，且更慢）。CDN 直链和 WebDAV 都是直连 HTTP。

**看门狗模式** (`--watch`，cron 每 10 分钟)：
- 检查 `/opt/data/PikPak/.watch_active` 标志文件
- 不存在 → 静默退出（休眠中）
- 存在 → 执行 `rclone_sync()` 同步新文件
- 有新文件 → 刷新活跃时间戳
- 超 55 分钟无新文件 → 清除标志文件，进入休眠
- 用户说"下载inbox-JAV" → 创建标志文件即可激活

## 依赖

- `pikpakapi`（已安装在 `/opt/data/.venv/` 中，NOT 在 Hermes venv 中。运行 jav_manager.py 须用 `/opt/data/.venv/bin/python3` 而非 `/opt/hermes/.venv/bin/python3`）
- sing-box 代理（SOCKS5 127.0.0.1:10808，需运行中）— 启动：`bash /opt/data/proxy-skill/proxy.sh start`，详见 `xray-proxy` 技能
- PikPak Token（`/opt/data/.pikpak_token.json`，已缓存含 refresh_token）
- `/tmp/rclone`（PikPak → 本地同步工具）

## 代理可用性

当前使用 sing-box + REALITY 协议直连美国圣何塞01节点（134.195.101.129:443），2026-07-18 验证通过（Google HTTP 302, javdb HTTP 200）。`http_get()` 内置 3 次自动重试（判断条件是 stdout 是否 > 100 bytes），确保检索成功率 ~94%。如果持续失败，参考 `xray-proxy` 技能换节点或重启代理（`bash /opt/data/proxy-skill/proxy.sh restart`）。

## 文件

- 主脚本：`/opt/data/jav_manager.py`（420行，统一入口）
- PikPak Token：`/opt/data/.pikpak_token.json`
- javdb Cookie：`/tmp/jdb_cookies.txt`
- **下载目录：`/opt/data/PikPak/Inbox-JAV/`**（⚠️ 番号视频入库唯一目标，不是 Movie/）
- 下载记录：`/opt/data/PikPak/.inbox_record.json`
- 看门狗标志：`/opt/data/PikPak/.watch_active`
- 看门狗 cron：`4e83fab5185d`（每10分钟 `--watch` 模式）
- 参考文档：`references/pikpak-cleanup.md`（PikPak 多文件磁链清理详解）
- 参考文档：`references/pikpak-folder-contents-listing.md`（PikPak 文件夹内容列举——检查种子中的广告文件）
- 参考文档：`references/session-20260718-corrected-workflow.md`（2026-07-18 磁链→字幕决策顺序纠正、CDN 工作流）

### 踩坑记录

- **🚨 番号匹配漏掉主视频导致误删（2026-07-18 修复）**：`pikpak_cleanup_ads()` 中 `code in fname.upper()` 用精确字符串匹配。当 `code="CAWD-001"`（带横杠）但磁链文件名是 `CAWD001C.mp4`（无横杠）时，匹配失败，**主视频被当广告删除**。CAWD-001 案例中 1.46GB 主视频被误删进回收站，且 PikPak 回收站 API（`/drive/v1/files/trash`）返回 404 无法恢复。

  **修复**：增加无横杠匹配 `code_nohyphen = code.replace('-', '').upper()`，条件改为 `code in fname_upper or code_nohyphen in fname_upper`。

  **预防**：任何番号匹配都应同时检查带横杠和不带横杠两种形式。javdb 磁链文件名经常省略横杠（如 `CAWD001C` 而非 `CAWD-001-C`）。清理广告前应打印 keep/del 决策表，人工确认主视频在 keep 列表中再执行 delete。

- **大文件 cp/mv 前台超时（2026-07-04 新增）**：`cp` 或 `mv` 一个 7GB 文件到 Inbox-JAV 大约需要 10-20 秒。如果终端工具超时（如 10s），`mv` 会被截断，目标文件只有部分数据且 ffprobe 报 `moov atom not found`。源文件仍在 `/tmp/` 完好，但需要重做操作。**修复**：对大文件（>4GB）的 cp/mv 操作必须使用 `background=true` + `notify_on_complete=true` 模式，不受前台超时限制。或者分步操作：前台 `cp` → 等待 → 前台 `ffprobe` 验证。
- **Phase 3 对大文件（>4GB）必然超时**。rclone 同步 600s timeout 不够，7200s 也不够。超时不是错误——PikPak 云端已完成，只需用 aria2 CDN 直链重新拉取。不要重复添加磁链到 PikPak（PikPak 不会处理重复磁链）。
- **推荐方案**：Phase 1-2 完成后，不依赖 rclone Phase 3。改为用 `check_pikpak_dl.py`（no_agent cron 每5分钟）等待离线下载完毕 → 获取 CDN 直链 → aria2 拉回 → ffprobe 验证。详见 `pikpak-webdav-manager` 技能的 `references/pikpak-offline-wait-cron.md`。
- **多个下载进程不能同时写同一文件**。旧会话残留的 Python/rclone 后台进程会在 aria2 完成后覆盖文件，导致 `moov atom not found`。下载前必须 `pkill -f pikpak_cdn_dl.py; pkill -f rclone`，下载后用 ffprobe 验证。
- **aria2 残留控制文件阻塞新下载**：aria2 完成后可能残留 `.aria2` 控制文件。新 aria2 实例会因旧 `.aria2` 文件卡住不启动新下载（所有 socket 为 0，进程睡眠）。**重启 aria2 前必须先清理：** `rm -f /opt/data/PikPak/Inbox-JAV/*.aria2`
- **aria2 幽灵子进程（关键！）**：用 `kill <bash_wrapper_pid>` 杀死 aria2 的 bash 包装器时，**实际的 aria2 子进程不会死**。它会继续运行，写入一个已从目录入口删除的文件描述符（`fd -> file.mp4 (deleted)`），造成文件在 `ls` 中不可见但仍占用磁盘并被写入。最终表现是：新下载的 `file.mp4` 瞬间"完成"（大小匹配）但 ffprobe 报 `moov atom not found`。**正确做法：**
  ```bash
  # 错误：kill bash wrapper 没用
  kill <bash_pid>
  
  # 正确做法（慎用，见下方警告）：
  kill $(pgrep aria2c) # 或逐一 kill 子进程
  
  # 确认无残留
  ps aux | grep aria2c

> ⚠️ **不要用 `pkill -f aria2c`** 当 Hermes 后台 aria2 进程在跑时：`pkill -f aria2c` 会杀死**所有** aria2 实例，包括通过 `terminal(background=true, notify_on_complete=true)` 管理的活跃下载。Hermes 后台进程被杀死后不可恢复，需要重新拿新 URL 启动。如果只想查状态，用 `pgrep -a aria2c` 或 `process(action=list)`。

  # 删腐败文件 + sync 等待
  rm -f file.mp4; sync; sleep 2
  ```
  不要相信 `ls -lh` 看到的文件大小——7.6GB 文件秒出现但校验失败是不正常的，说明是幽灵进程写入的腐败数据。

### 多番号并行下载（2026-07-08 新增）

当用户连续给出多个番号时，采用 **逐个 Phase 1-2 → 批量 Phase 3** 模式：

```
番号1 → jav_manager.py --no-sync（Phase 1-2: 搜索+PikPak）
番号2 → jav_manager.py --no-sync
番号3 → jav_manager.py --no-sync
         │
         ▼ 全部 Phase 1-2 完成后
番号1 → terminal(background=true) aria2 CDN下载
番号2 → terminal(background=true) aria2 CDN下载  ← 并行
番号3 → terminal(background=true) aria2 CDN下载  ← 并行
         │
         ▼ 逐个完成通知
         校验ffprobe → cp到Inbox-JAV → rm /tmp/dl
```

**操作步骤：**

1. 按番号逐个执行 `jav_manager.py --no-sync 番号`（Phase 1-2），等待每个完成后才启动下一个（PikPak API 有限频）
2. 获取每个番号的 CDN 直链：`api.get_download_url(file_id)`，保存到 `/tmp/<番号>_url.json`
3. 每个番号用一个独立的 `terminal(background=true, notify_on_complete=true)` 启动 aria2。**必须通过命令行直接传 URL，不能用 `--input-file`**。
   ```bash
   export LD_LIBRARY_PATH=/opt/data
   /opt/data/aria2c \
     --max-connection-per-server=8 --split=8 --min-split-size=8M \
     --continue=true --max-tries=5 --retry-wait=5 \
     --timeout=120 --console-log-level=notice \
     --dir=/tmp/dl --out=番号.mp4 \
     "$(python3 -c "import json; print(json.load(open('/tmp/<番号>_url.json'))['番号.mp4'])")"
   ```

**⚠️ `--input-file` 对 PikPak CDN URL 无效**：PikPak CDN 链接长达 ~835 字符，`aria2c --input-file=url.txt` 会截断/错误解析 URL，报 `total length mismatch. expected: 6429096397, actual: 7395207885` 并将输出写到 `index.html`。必须通过命令行参数直接传递 URL。

**⚠️ CDN URL 中途过期导致 `moov atom not found`**：即使文件大小完全匹配 PikPak 标称值，CDN URL 可能在下载中途返回 403（`X-Xos-Err-Desc: 1`），aria2 用 `--continue=true` 续传时写入的后续数据是来自新 URL 的过期/错误数据。结果：`ls -lh` 显示正确大小，但 ffprobe 报 `moov atom not found`。不要依赖文件大小判断完整性——**必须 ffprobe 验证**。

修复：重新调用 `api.get_download_url(file_id)` 获取新 URL，**删除旧文件**（不要依赖 `--continue=true`），从零开始下载。
   ```
4. 各 aria2 进程并行下载互不干扰，`--continue=true` 保证续传安全
5. 每个下载完成后通知会触发，再手动 ffprobe 校验 → cp 到 Inbox-JAV → rm /tmp/dl

**注意事项：**\n- **不要用 `pkill -f aria2c` 清理旧进程**——这会杀了所有后台 aria2。用 `pgrep -a aria2c` 查看，用 `kill $(pgrep -f 'aria2c.*特定番号')` 精准杀\n- **CDN URL key 必须匹配 `--out` 参数**：手动保存 URL 到 JSON 文件时，不要对文件名做 `replace('-C','')` 等清理操作。JSON 的 key 必须与 aria2 `--out` 参数完全一致，否则会报 `KeyError`。保存时用 `fname = file_info['name']`（原始文件名）做 key\n- CDN URL 有效期 24h，期间可安全续传。如果拿到新 URL 替代旧文件，aria2 会报 403 再重试，更快的方法是手动调用 `api.get_download_url()` 重新获取
- **PikPak CDN URL 可能旋转（403 错误）**：即使 URL 的 `expire` 时间未到，CDN 节点可能随机拒绝（返回 403，`X-Xos-Err-Desc: 1`）。表现为 aria2 报 `errorCode=22 The response status is not successful. status=403`。必须重新调用 `api.get_download_url(file_id)` 获取新 URL（通常分配不同 CDN 节点如 `dl-z01a-0048` → `dl-z01a-0043` → `dl-z01a-0041`，每次调用都不同）。**不要**复用 `/tmp/pikpak_urls.json` 中的过期 URL。
- **推荐下载策略：/tmp → 校验 → mv**（避免幽灵 inode）：直接下载到 Inbox-JAV 目录时，如果曾经在该目录有过被 kill 的 aria2 进程（留下 `(deleted)` fd），新 aria2 可能写入同一兄弟 inode 导致文件校验失败。**最佳实践：**
  ```bash
  # Step 1: 杀所有旧进程（必须在启动新下载前完成！）
  pkill -f aria2c && sleep 1 && ps aux | grep aria2c || echo "clean"
  
  # Step 2: 下载到 /tmp 全新目录
  curl -L -o /tmp/dl/FILE.mp4 "$FRESH_URL"
  # 或 aria2 --dir=/tmp/dl
  
  # Step 3: ffprobe 校验
  ffprobe -v error -show_entries format=duration -of csv=p=0 /tmp/dl/FILE.mp4
  
  # Step 4: 合格后搬入
  mv /tmp/dl/FILE.mp4 /opt/data/PikPak/Inbox-JAV/FILE.mp4
  ```
- **curl 单线程兜底方案**：当 aria2 出现幽灵进程/控制文件残留等复杂问题时，curl 单线程下载到 `/tmp` + ffprobe 校验 + `mv` 到目标目录是可靠兜底。速度通常 2-3 MB/s（可控但慢），适合最后几个小文件的收尾。
- **ffprobe 校验不可替代**：`moov atom not found` 错误总是表示文件损坏，**无论文件大小是否匹配**。aria2 预分配文件会导致 `ls -lh` 显示完整大小，但数据可能为空或损坏。必须用 `ffprobe -v error -show_entries format=duration -of csv=p=0 file.mp4` 验证。

### subtitlecat
- **搜索结果链接是相对路径**：`href="subs/1460/HMN-850.html"`（无前导 `/`）和 `href="/subs/..."`（有前导）两种都可能出现，代码必须兼容
- **SRT下载链接有空格**：`href = "/subs/..."`（等号两侧空格），正则必须用 `href\s*=\s*"..."`
- **下载前必须创建目录**：`os.makedirs(dir, exist_ok=True)`
- **同一番号可能对应多个 subtitlecat 页面**：如 WANZ-320 有 `subs/120/WANZ-320.html`（原始/自动翻译版，24种语言）和 `subs/245/WANZ-320%20eng.html`（英文用户上传版，22种语言）。两个页面的 SRT 语言选项不同。第一个搜索结果页面不一定是中文选项最丰富的，可查看第二个搜索结果页（如 `...eng.html`）获取更多中文变体（如 `eng-zh-CN`）

### javdb（唯一磁链来源）

- **用户偏好：只从 javdb.com 找磁链**，不要用 web_search 或其他网站搜索磁链
- **Over18 cookie**: 每次新会话先请求 `/over18?respond=1`
- **磁链重复**: 每个磁链在页面出现两次，按 btih 去重
- **代理IP可能被封**: 某些节点返回 403，需切换节点
- **旧番可能无种**: 磁链数为 0 时如实汇报
- **部分番号首次搜索可能失败但实际存在**: 如 START-540 首次 javdb 搜索无结果（被判断为不存在），但几小时后重试成功找到。原因可能是代理节点 IP 临时被封、javdb 索引更新延迟、或地区屏蔽间歇性。策略：延迟 1-2 小时后重试，或换代理节点。彻底放弃前需告知用户，用户可能知道可用链接。
### PikPak 广告清理

- **`selected_files` PATCH 不可靠**: PikPak 解析极快（4-6s 从 "not found" → "PHASE_TYPE_COMPLETE"），来不及 PATCH 选文件，返回 `file_nothing_updated`。
- **可靠方案**: 等所有子文件 `phase=COMPLETE` 后，用 `file_list(parent_id=folder_id)` 列出文件，再用 `delete_to_trash([...])` 删除广告。
- **`offline_file_info(file_id)` 可能失败**: 刚添加磁链后，文件未就绪时抛 "File or folder is not found"。需 try/except 重试。
- **`params.files` 不可用**: PikPak 的 `offline_file_info` 不暴露子文件列表（始终为 0）。必须用 `file_list(parent_id=folder_id)` 查子文件。
- **文件夹 `kind=drive#folder`**: 多文件磁链创建的是文件夹，检测 `info.get('kind')` 是否为 `drive#folder` 来判断是否有子文件。
- **⚠️ `size` 是字符串（2026-07-09 发现）**: `file_list()` 返回的 `size` 不是 int，比较时必须 `int(sf.get('size', '0'))`，否则报 `TypeError: '<' not supported between instances of 'str' and 'int'`。
- **番号匹配（横杠陷阱）**: 广告文件名有时会加上前缀（如 `489155.com@DSOD-005-C.mp4`）。匹配时必须同时检查带横杠和不带横杠两种形式——磁链文件名经常省略横杠（`CAWD001C.mp4` 而非 `CAWD-001-C.mp4`），用 `code in fname.upper() or code.replace('-','').upper() in fname.upper()`。否则主视频会被误判为广告删除（见踩坑记录）。
- **`-C` 后缀保留**: 重命名时保留 `-C`/`-U` 等后缀（标记内嵌字幕/无码版），用 `for s in ['-C','-U','_C','_U']: if s in base.upper(): suffix = s; break` 提取。
- **执行顺序关键**: 先 `batchMove` 移出 → 等 1s → PATCH 重命名 → 最后 `delete_to_trash` 删文件夹。若先删文件夹再重命名会报 "file_rename_in_recycle_bin"。

直接使用 pikpakapi 清理文件夹（无需 jav_manager.py）的完整工作流见 `references/pikpakapi-direct-cleanup.md`。

### 代理（sing-box + REALITY）
- 重启服务器后需重跑 `bash /opt/data/proxy-skill/proxy.sh start`
- 查状态：`bash /opt/data/proxy-skill/proxy.sh status`
- 重启：`bash /opt/data/proxy-skill/proxy.sh restart`
- 当前节点：美国圣何塞01 REALITY（134.195.101.129:443，直连 IP 不走 Cloudflare）
- **节点全挂时**：参考 `xray-proxy` 技能。若 VLESS WS 节点返回 403 且响应头含 `cf-mitigated: challenge`，说明 Cloudflare 封了出口 IP 段——换 IP 不一定解决，应改用 REALITY 直连节点（不走 CF CDN）。若 UDP 被封则 hy2 节点不可用。
- **代理失效时 javdb 搜索返回空**：Phase 1 的 `http_get()` 在代理不通时静默失败（空响应），不会报错但搜不到磁链。如果搜索"未找到 番号"，先 `bash /opt/data/proxy-skill/proxy.sh status` 检查代理连通性再重试。
- **用户偏好（2026-07-18）**：任何 skill 或接口被墙时，先启动代理再重试，不要反复重试同一不通的路径。

### 脚本运行
- 统一入口：`/opt/data/.venv/bin/python3 /opt/data/jav_manager.py 番号`
- 跳过 rclone 同步：加 `--no-sync` 参数（推荐，后续用 aria2 并行下载）
- 批量多番号：`/opt/data/.venv/bin/python3 /opt/data/jav_manager.py --no-sync 番号1 番号2 ...`
  - 注意：PikPak API 有频率限制，批量发太多会报 HTTP Error（重试可恢复）。建议一批不超过 8-10 个
  - 200+HTTP Error 常见于连续多个离线下载请求，等一两分钟重试即可
- 看门狗模式：`/opt/data/.venv/bin/python3 /opt/data/jav_manager.py --watch`
- 手动检查一次：`/opt/data/.venv/bin/python3 /opt/data/jav_manager.py --watch-once`
- 脚本依赖 `pikpakapi`（安装在 `/opt/data/.venv/`，**不在** Hermes venv 中。cron 和第三方脚本调用时必须用 `/opt/data/.venv/bin/python3`，否则报 `ModuleNotFoundError: No module named 'pikpakapi'`）
- 如果 Token 过期（401 错误），联系用户重新登录

## 内嵌字幕检测逻辑（2026-07-08 新增）

### 规则

**视频优先选择内嵌字幕版**，如果磁链名含 `-C`/`-UC`/`中字` 等标记说明已内嵌字幕，则**不再从 subtitlecat 下载独立 .srt 文件**。

具体实现：
1. Phase 1 选磁链时字幕版优先（已有逻辑）
2. Phase 2.5 增加前置判断：磁链名含 `-C`/`-UC` 等 → 跳过 subtitlecat
3. 裸磁链版（不含字幕后缀）→ 正常执行 subtitlecat 下载 .srt

### 选择磁链时的优先级

1. **首选内嵌中文字幕版** — 文件名含 `-C`、`-UC`、`中字`、`内嵌`、`SUB` 等标记
2. **其次高清优先** — 同类中选最大的
3. **最后兜底** — subtitlecat 下载独立 .srt

### 下载后检测

视频下载到本地后，用 `ffprobe` 检测是否有内嵌字幕流：

```bash
# 检查是否有字幕流
ffprobe -v error -select_streams s -show_entries stream=index,codec_name,codec_type -of csv=p=0 file.mp4
# 有输出 → 包含字幕流 ✅
# 无输出 → 无内嵌字幕 ❌
```

- 如果有字幕流 → **跳过** subtitlecat 下载，直接进入重命名阶段
- 如果无字幕流 → 正常执行 Phase 2.5（subtitlecat 下载独立 .srt）

### 在重命名阶段保留字幕

无论字幕是内嵌还是独立的 .srt 文件，最终自定义文件名（如 `番号-女优名-描述.mp4`）规则不变：
- 内嵌字幕版 → 只重命名视频文件
- 独立字幕版 → 视频和 .srt 同名重命名

## 用户偏好

- **🚨 严禁擅自替换用户给定的番号（2026-07-18 硬性纠正）**：用户说下载 `CAWB-001`，我擅自下载了 `CAWD-001`（视觉相近就"自动纠正"了）。这是严重错误，用户原话"怎么会出现这么低级的错误，以后严禁再犯"。规则：**用户给什么番号就搜什么番号，不做任何替换、猜测、近似匹配**。即使搜索结果第一个不是用户给的番号，也要找到完全匹配的那个。视觉相近的番号（CAWB/CAWD、SONE/SONE、START/STAR）尤其要逐字符核对。
- **主动汇报**：任何失败（javdb 403、PikPak 错误、字幕下载失败）必须**立即主动告知用户**，不等用户来问。遇到异常、阻塞或不确定的情况第一时间汇报，不自己默默跳过。
- **禁止无码破解版（-U）**：`-U`（非 `-UC`）或无码破解标注的磁链一律不选。如果 `jav_manager.py` 自动选了 `-U` 版，需手动删除 PikPak 文件，回 javdb 选纯 `-C` 或裸磁链版
- **单文件 + 干净文件名**：不下载包含广告/HTML 的文件夹，自动只选视频文件；最终结果必须是**根目录单文件，不留文件夹**（用 batchMove 移出视频 + 删空文件夹）；视频文件名重命名为 `番号-C.mp4` 格式（保留 `-C` 后缀），去掉广告前缀（如 `489155.com@`）
- **简体中文优先**：subtitlecat 上 zh-CN > zh-TW，同类按下载量排序
- **自定义中文文件名（重要）**：当用户明确给出自定义文件名（如 `番号-女优名-日文描述.mp4`），必须以用户指定名称为准，视频和字幕使用同一自定义名称（仅后缀不同）。例如用户要求"CAWD-992-清野咲-多P痴汉轮奸 在地铁上被痴汉们骚扰摆弄并轮奸的清纯美白美腿美尻舞蹈女学生"，则视频命名为 `{用户指定名}.mp4`，字幕命名为 `{用户指定名}.srt`
- **subtitlecat 搜不到字幕是正常情况**：许多新番号（尤其是发行 <2 周的）在 subtitlecat 上可能没有对应的字幕页面。搜不到直接跳过，不必报错或等待后续重试。不影响下载流程。
- **重复番号处理**：如果 PikPak Inbox-JAV 中已存在该番号的文件（PHASE_TYPE_COMPLETE），说明之前已下载过但本地丢失。此时**跳过 Phase 1（javdb 搜索 + 磁链）**，直接进入 Phase 2.5（搜字幕）+ Phase 3（aria2 下载到本地），无需重新添加磁链
- **视频文件不小于 2GB**：番号视频小于 2GB 的不要下载（标清 AVI 版清晰度太差，如 WANZ-320 的 894MB 版）。必须找 1080p 或其他高清版本（通常 3GB+），如果 PikPak 中已有旧版小文件，搜索新磁链覆盖

## 自定义文件名处理

当用户提供自定义中文文件名时（如 `CAWD-992-清野咲-多P痴汉轮奸...`），流程调整为：

1. **Phase 1 略有调整**：javdb 搜索磁链时仍用番号搜索，但下载后**不使用脚本的默认重命名规则**（`番号-C.mp4`）
2. **Phase 2.5（字幕）**：照常搜索 subtitlecat，下载翻译后的 SRT
3. **Phase 3（本地同步）**：下载完成后：
   - 视频文件名：`{用户指定名}.mp4`（如 `CAWD-992-清野咲-多P痴汉轮奸...mp4`）
   - 字幕文件名：`{用户指定名}.srt`（与视频同名，仅后缀不同）
4. **验证**：ffprobe 校验视频，head 检查字幕内容

注意：自定义文件名时，PikPak 中保留原始文件名（`番号.mp4`），只在本地重命名。

### 重复番号处理

如果 PikPak Inbox-JAV 中已存在该番号的文件（PHASE_TYPE_COMPLETE），说明之前已下载过但本地已清空。此时：
1. **跳过 Phase 1（javdb 搜索 + 磁链）** — 不需要重新添加磁链
2. 直接 `get_download_url(file_id)` 获取 CDN 直链（`web_content_link` 字段，不是 `url` 字段）
3. 进入 Phase 2.5（搜字幕）+ Phase 3（aria2 下载到本地）
4. 最后用自定义文件名重命名

## 验证

```bash
# 测试下载（搜索→PikPak→rclone同步到本地）
/opt/data/.venv/bin/python3 /opt/data/jav_manager.py DSOD-005

# 手动检查新文件并同步
/opt/data/.venv/bin/python3 /opt/data/jav_manager.py --watch-once

# 检查下载目录
ls -la /opt/data/PikPak/Inbox-JAV/
```

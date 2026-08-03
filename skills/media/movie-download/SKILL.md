---
name: movie-download
title: 影视资源下载（BT磁链 → PikPak → aria2）
description: 下载电影/剧集（含内嵌中文字幕版）：从 BT 影视资源站找磁链 → PikPak 离线 → aria2 拉回本地 → ffprobe 校验重命名入库。适用于任何非番号影视内容。
version: 1.0.0
tags: [下载, 磁力, 磁链, BT, 电影, 剧集, 中文字幕, PikPak, aria2, movie, torrent, magnet]
trigger: 用户要求下载某部电影/剧集/纪录片，或提到"下载XX片"、"找中字版"、"内嵌字幕"、资源站清单
---

# 影视资源下载（电影/剧集，非 JAV）

用户要求下载电影、剧集、纪录片等**非番号影视内容**时使用本 skill。番号视频走 `jav-auto-download`，两者共用 PikPak 离线 + aria2 拉回管线，但**资源发现路径完全不同**。

## 🚨 用户硬性规则（2026-08-01 明确）

**不要外挂中文字幕。选磁链时必须选内嵌中文的版本**（文件名含 `中字`/`简繁字幕`/`中英字幕`/`国语`/`CHS`/`简中` 等标注，或压制组内封字幕流）。

- 不主动找外挂 .srt 来配（与 jav-auto-download 的 subtitlecat 流程相反）
- 若只有原版无中字磁链，**不要直接用**——继续找内嵌中字版，找不到就如实告诉用户
- 下载后可用 `ffprobe -v error -select_streams s -show_entries stream=index,codec_name -of csv=p=0 file.mp4` 验证确有字幕流（注意：mkv 内封软字幕也算内嵌，播放器直接可显）

## 资源站清单

**14 个影视资源站**（用户提供 + 补充）保存在 `/opt/data/movie_sources.md`，含每个站的定位说明：

- BT之家 https://www.1lou.me/（Discuz 论坛，实测可 web_extract 拿种子，**首选**）
- 6V电影 https://www.66s6.cc/、BT部落天堂 https://www.btbuluo.net/、Rarbg https://rargb.to/、SeedHub https://www.seedhub.cc/、Grab4K https://www.grab4k.cn/、飘花 https://www.piaohua.com/、磁力熊 https://www.cilixiong.com/、悠悠MP4 https://www.uump4.cc/、BTDigg https://btdig.com/、1337x https://1337x.to/、YTS https://yts.mx/、电影天堂 https://www.dytt8899.com/、BT蚂蚁 https://btmayi.cc/（磁力搜索导航入口，聚合多站资源）

## 标准流程

```
① 站内搜磁链（内嵌中字优先）
② 磁链 → PikPak 离线（Inbox-JAV，动态取 folder id）
③ 就绪后取 CDN URL → aria2 拉回 /tmp
④ ffprobe 校验 → 重命名入库（用户给中文名则用之）
```

### ① 找磁链——站点可用性实测（2026-08-01）

| 站点 | 状态 | 说明 |
|:----|:----|:----|
| 1lou.me（BT之家） | ✅ | Discuz，`web_extract` 直接可读全文，种子附件页 `attach-download-<id>.htm` 可用 curl 下载 |
| twlkbt 等 Discuz 论坛 | ✅ | `web_extract` 可拿 magnet hash（页面里直接有 `magnet:?xt=urn:btih:` 明文） |
| yts.mx / 1337x / bt4g | ❌ | Cloudflare 拦截（`Just a moment...`），curl 直连/代理都不行 |
| btmayi.cc（BT蚂蚁） | ⚠️ | 搜索结果页 JS 渲染，curl 只拿到标题无磁链；作导航入口查资源存在性，实际拿磁链去 BT之家等论坛 |
| nbwin / 云盘集 | ⚠️ | 文章页可读但下载链接常已失效；海外 IP 拉正文可能超时 |
| assrt.net（射手网伪站） | ⚠️ | 反爬严，curl 返回 812B 错误页，需浏览器 |
| zimuku 字幕库 | ⚠️ | 有云锁验证码页，需浏览器 |

**搜索技巧**：`web_search` 搜 `"片名" 年份 1080p 中字 magnet` 或 `"片名" 年份 btih`，命中 Discuz 论坛页后用 `web_extract` 直接提取 `magnet:?xt=urn:btih:<40位hash>`。

### ② 种子文件 → 磁链（btih 提取）

1lou 等站点只提供 `.torrent` 附件时：下载附件 → 用 bencode 解析 info dict → SHA1 得 btih：

```bash
curl -sL --proxy http://127.0.0.1:10808 -A "Mozilla/5.0" \
  "https://www.1lou.me/attach-download-<id>.htm" -o /tmp/movie.torrent
# 然后 python 解析（见 scripts/btih_from_torrent.py）
```

得到 `magnet:?xt=urn:btih:<HASH>&dn=<名称>` 后加入 PikPak。

### ③ PikPak 离线 + aria2 拉回

与番号流程一致，详见 `jav-auto-download`：
- 动态取 `/Inbox-JAV` folder id（不硬编码）
- 离线完成后 `get_download_url` 取 `web_content_link`（不是 `url` 字段）
- aria2：`export LD_LIBRARY_PATH=/opt/data`，8 连接分片，URL 走命令行参数（**禁止 `--input-file`**，CDN URL 超长会截断）
- 下载到 /tmp → ffprobe 校验 → mv 入库，**不要直接下载到目标目录**（防幽灵 inode）

### ④ 重命名入库（2026-08-02 用户明确）

**普通电影**：下载完成后**必须改名**为 `中文片名.英文片名.年份.扩展名`（如 `致命黑兰.Colombiana.2011.mkv`、`应召女王.Madame.Claude.2021.mkv`、`池畔谋杀案.Swimming.Pool.2003.mkv`），存 **`/opt/data/Movie/`**（电影独立目录，与番号分开）。
**番号视频**（NMSL-011 等）：走 jav-auto-download 规则命名（`番号-女优名-描述.mp4`），存 `/opt/data/PikPak/Inbox-JAV/`。**两个规则不要混用**——用户明确纠正过：番号视频不能按电影规则命名入库。

- 移入用 cp 后台 + 校验大小一致（rsync 未安装，用 `cp` + 手动对比字节数；跨文件系统 mv 会超时被截断）
- 移入后删 /tmp 源文件

## 踩坑记录

- **Cloudflare 站不要死磕**：yts/1337x/bt4g 全部 CF 拦截，直接换 Discuz 论坛或 web_search 挖 hash
- **中文压制版链接常失效**（如 nbwin 的"简繁字幕版"）——优先找"高清原版+内封中字"的压制组版（CATCHPLAY WEB-DL / CMCT / CHD 等），而不是去下外挂字幕
- **用户规则冲突时以最新为准**：JAV 流程允许 subtitlecat 外挂（jav-auto-download），但**电影/剧集明确禁止外挂**——两个 skill 各自独立，不要串
- **PikPak 对特定文件可能限速**（2026-08-01 NMSL-011：单文件被限到 20-250KB/s，换节点/换磁链无效，同期其他文件 6-19MB/s）——挂后台慢慢爬或换小版本，别反复换节点
- **PikPak CDN 全节点 503（间歇性故障）**：同一批新取的 URL 可能全部 503（errorCode=29）。不要逐个重试——杀掉所有失败的 aria2，**等 10-30 分钟**（用 `sleep 600 && 重取URL && 重启下载` 的后台脚本），CDN 恢复后重新 `get_download_url` 换新 URL 即可，旧 URL 过期没用
- **种子文件夹常混入广告文件**（BBQDDQ.com 压制组种子尤甚：`.png`/`.doc`/`.pdf`/`.mkv` 名义的 0 字节广告）：离线结果是文件夹时 `file_list` 列内部文件，**只挑 size > 100MB 的真视频取 URL**，广告文件跳过
- **PikPak 离线结果可能是文件夹**（kind=drive#folder，size=0）：电影种子常把视频包在子目录里。取 URL 前必须 `file_list(parent_id=<folder_id>)` 找到内部视频文件，再用其 id 调 `get_download_url`。参考 jav-auto-download 同款坑。
- **PikPak API 删除方法**：没有 `offline_delete`，删离线任务用 `delete_tasks([task_id])`；删网盘文件用 `delete([file_id])`。可用 `dir(client)` 先确认方法名再调用。
- **aria2 显示 0KB/s 但文件已是满大小 ≠ 卡死**：aria2 预分配文件，`stat` 看到完整大小但速度 0 可能是下载已完成、只是 `.aria2` 控制文件残留（进程被杀/异常退出时常见）。**验证法**：杀进程 → `rm .aria2` → 用 `--continue=true` 重启同一 URL，若立即报 `Download has already completed` 说明文件其实完整，直接 ffprobe 校验后入库（2026-08-01 池畔谋杀案案例）。
- **并发上限 3**：用户明确要求最多同时下 3 个文件（2026-08-02）。批量下载用并发计数循环（`pgrep -fc aria2c` 计数 + 等待槽位）或 `xargs -P3`，不要一次全开。NMSL-011 等大文件挂后台慢慢爬即可。
- **"中文字幕"磁链标注不可靠**：NMSL-011 磁链名标"中文字幕"但 ffprobe 无字幕流、抽帧也无硬字幕（只有水印）。电影下载后同样要验证内嵌字幕：`ffprobe -select_streams s` 查字幕流；无流时**抽帧 + OCR 查硬字幕**（`ffmpeg -ss <秒> -i file -frames:v 1 -vf scale=480:-1 /tmp/f.jpg` + 本地 RapidOCR `/opt/data/ocr_venv`），多抽几帧（对白多的位置如 600/2400/4200s）。确认无字幕要如实告知用户，别当有中字版入库。
- **假种子/截断种子（2026-08-02 野兽女孩事故）**：磁链标注 720P 完整版，下载后 ffprobe 发现时长只有 **4分45秒**（6840帧）——种子本身是截断/假货，PikPak 离线 + aria2 拉回全程无异常，只有 ffprobe 时长能识破。**每部电影下完必须核对时长是否符合预期**（野兽女孩 108 分钟 vs 实际 4分45秒 → 换另一个磁链 `6115DA56` 拿到 1.31GB 完整版）。不要只看文件大小/有无字幕流就入库。同类坑：小文件（<500MB 的"完整电影"）尤其要怀疑。
- **无字幕版入库标注**：用户允许"入库但标注清楚无字幕"（2026-08-02 野兽女孩：韩语无字版按用户要求入库，文件名加"韩语无字幕"标注，用户自己想办法补字幕）——入库前问用户或按用户要求标注，不要擅自拒绝入库。

## 参考

- `references/colombiana-20260801.md` — 《致命黑兰》完整实战：磁链搜索路径、种子→btih 提取、站点可用性实测
- `references/madame-claude-20260801.md` — 《应召女王》第二次实战：多译名搜索、种子附件 id 定位、版本筛选
- `references/batch-4-movies-20260801.md` — 批量下载 4 部电影：多译名识别、CDN 全节点 503 恢复模式（等 10 分钟重取 URL）、广告文件过滤、批量 aria2 脚本
- `references/nysm3-nmsl-20260802.md` — 惊天魔盗团3 下载 + NMSL-011 换 2.6G 中字版：限速死局换版、jav_manager 处理番号、"中文字幕"标注不可靠、抽帧 OCR 字幕验证标准流程
- `references/beastie-girls-20260802.md` — 野兽女孩下载：假种子识别（时长验证）、换源、无字幕入库标注决策
- `scripts/btih_from_torrent.py` — 从 .torrent 提取 btih hash 的脚本

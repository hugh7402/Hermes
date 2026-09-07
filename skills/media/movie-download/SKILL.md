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
- 6V电影 https://www.66s6.cc/、BT部落天堂 https://www.btbuluo.net/、Rarbg https://rargb.to/、SeedHub https://www.seedhub.cc/、Grab4K https://www.grab4k.cn/、飘花 https://www.piaohua.com/、磁力熊 https://www.cilixiong.org/（⚠️ .com 已停放，用 .org）、悠悠MP4 https://www.uump4.cc/、BTDigg https://btdig.com/、1337x https://1337x.to/、YTS https://yts.mx/、电影天堂 https://www.dytt8899.com/、BT蚂蚁 https://btmayi.cc/（磁力搜索导航入口，聚合多站资源）

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
| **磁力熊 cilixiong.org** | ✅ **影视剧首选源** | 用户 2026-08-04 定：**质量比电影天堂好**。⚠️ **cilixiong.com 域名已停放（2026-08-27 验证），用 `.org`**。`/drama/<id>.html` 整季页面列出多版本（2160p/1080p，含大小标注），`web_extract` 直接拿全部 `magnet:?xt=urn:btih:` 明文。优先 `web_search site:cilixiong.com 片名` |
| **磁力熊站内搜索（EmpireCMS）** | ✅ 2026-08-27 验证 | POST `https://www.cilixiong.org/e/search/index.php`，**必须带全参数** `classid=1,2&show=title&tempid=1&keyboard=关键词`（缺参数返回"信息提示"JS 跳转页，不是搜索结果）。需 `Referer: https://www.cilixiong.org/` + UA，走代理。**电影结果在 `/movie/<id>.html`，剧集在 `/drama/<id>.html`**（旧版只记了 drama——电影分类在 movie 下）。压制组中字版常在这里，如 `摔跤吧！爸爸.2016.1080p.简繁中字￡CMCT梦幻.12GB` |
| **BTDigg btdig.com** | ⚠️ 限流严重 | 2026-08-27 验证：`web_extract`/浏览器失败，**curl `-x http://127.0.0.1:10808` 代理可访问**。文件名在磁链 href 的 `dn=` 参数（HTML 转义 `&amp;` 需 replace 回 `&`，再 urllib unquote；BTDigg 标题在嵌套 div 里，别从 `<a>` 文本提取）。**连续请求被限流**（返回 <2000B），每部搜索间隔 10-12s + 失败重试 3 次 |
| 1lou.me（BT之家） | ✅ | Discuz，`web_extract` 直接可读全文，种子附件页 `attach-download-<id>.htm` 可用 curl 下载 |
| twlkbt 等 Discuz 论坛 | ✅ | `web_extract` 可拿 magnet hash（页面里直接有 `magnet:?xt=urn:btih:` 明文） |
| 电影天堂 dytt8899.com | ✅ | 站内搜索：POST `https://www.dytt8899.com/e/search/index.php`（`--data-urlencode keyboard=关键词`，需 Referer 头，**GBK 编码**），无结果返回"没有搜索到相关的内容"提示页。剧集页每集一个磁链（`dn=剧名XX.mp4`）。**搜不到的美剧直接转磁力熊，别死磕** |
| yts.mx / 1337x / bt4g | ❌ | Cloudflare 拦截（`Just a moment...`），curl 直连/代理都不行 |
| btmayi.cc（BT蚂蚁） | ⚠️ | **实为导航站**：列出磁力搜索器入口（btmayi.top/btfox.icu/TorrentKitty 等），不直接给磁链。搜索格式 `?s=关键词`，结果页是各站链接。不如磁力熊直接 |
| nbwin / 云盘集 | ⚠️ | 文章页可读但下载链接常已失效；海外 IP 拉正文可能超时 |
| assrt.net（射手网伪站） | ⚠️ | 反爬严，curl 返回 812B 错误页，需浏览器 |
| zimuku 字幕库 | ⚠️ | 有云锁验证码页，需浏览器 |
| subhd.tv | ⚠️ | 云锁验证码（代理也触发），验证码页 HTML 埋"伪搜索结果"诱饵（如"YYeTs字幕组..."实为防火墙页）——解析前先确认标题不是"网站防火墙/安全验证" |

**搜索技巧**：`web_search` 搜 `"片名" 年份 1080p 中字 magnet` 或 `"片名" 年份 btih`，命中 Discuz 论坛页后用 `web_extract` 直接提取 `magnet:?xt=urn:btih:<40位hash>`。

### ② 种子文件 → 磁链（btih 提取）

1lou 等站点只提供 `.torrent` 附件时：下载附件 → 用 bencode 解析 info dict → SHA1 得 btih：

```bash
curl -sL --proxy http://127.0.0.1:10808 -A "Mozilla/5.0" \
  "https://www.1lou.me/attach-download-<id>.htm" -o /tmp/movie.torrent
# 然后 python 解析（见 scripts/btih_from_torrent.py）
```

得到 `magnet:?xt=urn:btih:<HASH>&dn=<名称>` 后加入 PikPak。

### ③ PikPak 离线 + 拉回本地

与番号流程一致，详见 `pikpak-webdav-manager`：
- 动态取 `/Movie` 或 `/Inbox-JAV` folder id（不硬编码；pikpakapi 的 `path_to_id('/')` 可能返回空，用 `file_list(parent_id='')` 从根目录找 Movie 文件夹）
- **🚨 拉回通道（2026-08-27 CDN 直连 IP 已封，aria2 方案作废）**：离线完成后用 **WebDAV 15 并发**拉回——`bash /opt/data/pikpak.sh copy15 /Movie /tmp/dl`（或 `--files-from` + `--transfers 15 --buffer-size=32M`）。aria2 CDN 直链（`get_download_url` 取 `web_content_link`）**不可用**，仅历史参考
- 下载到 /tmp → ffprobe 校验 → 后台 cp 入库（跨文件系统，前台 mv 会超时截断），**不要直接下载到目标目录**（防幽灵 inode）

### ④ 重命名入库（2026-08-02 用户明确）

**普通电影**：下载完成后**必须改名**为 `中文片名.英文片名.年份.扩展名`（如 `致命黑兰.Colombiana.2011.mkv`、`应召女王.Madame.Claude.2021.mkv`、`池畔谋杀案.Swimming.Pool.2003.mkv`），存 **`/opt/data/Movie/`**（电影独立目录，与番号分开）。
**剧集（多集）**：建子目录 `Movie/剧名第一季(年份)/`，集数文件保留原名（如 `Stranger.Things.S01E01.1080p.BluRay.x264-SHORTBREHD.mkv`），字幕同目录。
**番号视频**（NMSL-011 等）：走 jav-auto-download 规则命名（`番号-女优名-描述.mp4`），存 `/opt/data/PikPak/Inbox-JAV/`。**两个规则不要混用**——用户明确纠正过：番号视频不能按电影规则命名入库。

> ⚠️ **版本选择偏好（2026-08-04 用户明确）**：用户偏好**高清大版本**。同片多版本时选清晰度高的大版本（如怪奇物语 S1 选 26.69G BluRay x264 SHORTBREHD 而非 6.15G x265），不要默认选小体积。

- 移入用 cp 后台 + 校验大小一致（rsync 未安装，用 `cp` + 手动对比字节数；跨文件系统 mv 会超时被截断）
- 移入后删 /tmp 源文件

## 踩坑记录

- **🚨 网络命令必须带 timeout（2026-08-16 驭风男孩 gateway 卡死事故）**：`rclone lsf pikpak:Movie/` 在 PikPak 瞬时连接故障时会**无限挂起** → agent 的 terminal 调用不返回 → gateway 线程死循环烧 CPU（实测单线程 97%）→ 整个微信网关无响应（用户感知"死机"，且恰好发生在启动 skill 之后，容易误判成 skill 问题——**skill 本身是好的，是网络调用挂起拖死了 agent**）。预防：**所有 rclone/PikPak/curl 网络命令一律加 `timeout <秒>` 前缀**（如 `timeout 60 /tmp/rclone lsf "pikpak:Movie/"`），长下载用 background=true + notify_on_complete，不要前台长阻塞。gateway 卡死诊断与恢复见 `weixin-gateway-troubleshooting` skill。
- **🚨 时长校验禁用 bc 命令（2026-08-04 三剧连环误删事故）**：批量脚本写 `echo "$dur > 100" | bc` 判断时长，但**服务器没装 bc** → 判断恒为空 → **已下载成功的完整文件全部当失败删除**（护宝寻踪 8 集 45 分钟正常时长全被 rm）。症状隐蔽：日志显示 `校验失败 (dur=2734)`，时长明明是正常的。**必须用 python 判断**：`[ "$(python3 -c "print('1' if float('$dur') > 100 else '0')" 2>/dev/null)" = "1" ]`。所有批量校验脚本统一走 python，不要假设系统装了 bc。附带影响：**改完校验逻辑后，旧进程仍在跑旧逻辑**——重启脚本才生效，已启动的后台任务要 kill 掉用修好的版本重跑（配合 `--continue=true` 断点续传不浪费已下载部分）。
- **Cloudflare 站不要死磕**：yts/1337x/bt4g 全部 CF 拦截，直接换 Discuz 论坛或 web_search 挖 hash
- **电视剧批量下载（多集，2026-08-04 护宝寻踪实战）**：电影天堂（dytt8899.com）剧集页**每集一个独立磁链**（`dn=剧名XX.mp4`），页面 **GBK 编码**。流程：① curl 抓页 → python `raw.decode('gbk')`（UTF-8 解码会失败/乱码）② 按 `<tr>` 行解析 `re.findall(r'<tr[^>]*>(.*?)</tr>', html, re.S)`，行内含 `magnet:?xt=urn:btih:<hash>&dn=剧名XX.mp4`（36 集 = 36 个唯一磁链，页面每个磁链出现两次需去重；第一行 `<tr>` 是剧集简介不含磁链，注意跳过）③ 批量 `offline_download(url, parent_id=inbox_id)` 加 PikPak（每集间隔 ~1.5s 避免限频，36 个全成功）④ 等 ~60s 后批量 `get_download_url` 取 CDN 直链存 JSON ⑤ aria2 批量下载：**并发槽位控制 `pgrep -fc aria2c` 计数 ≤3**，下载到 /tmp → ffprobe 时长校验（>100s 才算完整，防假种子）→ cp 到 Movie/ → rm /tmp ⑥ 每集独立校验+入库，**已完成文件跳过**（幂等，重启安全）。**电视剧入库目标 = Movie/**（与番号分开，用户 2026-08-04 确认）。
- **中文压制版链接常失效**（如 nbwin 的"简繁字幕版"）——优先找"高清原版+内封中字"的压制组版（CATCHPLAY WEB-DL / CMCT / CHD 等），而不是去下外挂字幕
- **用户规则冲突时以最新为准**：JAV 流程允许 subtitlecat 外挂（jav-auto-download），但**电影/剧集明确禁止外挂**——两个 skill 各自独立，不要串
- **PikPak 对特定文件可能限速**（2026-08-01 NMSL-011：单文件被限到 20-250KB/s，换节点/换磁链无效，同期其他文件 6-19MB/s）——挂后台慢慢爬或换小版本，别反复换节点
- **PikPak CDN 全节点 503（间歇性故障）**：同一批新取的 URL 可能全部 503（errorCode=29）。不要逐个重试——杀掉所有失败的 aria2，**等 10-30 分钟**（用 `sleep 600 && 重取URL && 重启下载` 的后台脚本），CDN 恢复后重新 `get_download_url` 换新 URL 即可，旧 URL 过期没用
- **种子文件夹常混入广告文件**（BBQDDQ.com 压制组种子尤甚：`.png`/`.doc`/`.pdf`/`.mkv` 名义的 0 字节广告）：离线结果是文件夹时 `file_list` 列内部文件，**只挑 size > 100MB 的真视频取 URL**，广告文件跳过
- **PikPak 离线结果可能是文件夹**（kind=drive#folder，size=0）：电影种子常把视频包在子目录里。取 URL 前必须 `file_list(parent_id=<folder_id>)` 找到内部视频文件，再用其 id 调 `get_download_url`。参考 jav-auto-download 同款坑。
- **PikPak API 删除方法**：没有 `offline_delete`，删离线任务用 `delete_tasks([task_id])`；删网盘文件用 `delete([file_id])`。可用 `dir(client)` 先确认方法名再调用。
- **rclone 删云端源必须 delete + rmdir 两步（2026-08-16 驭风男孩）**：`timeout 120 rclone delete "pikpak:Movie/<目录>/"` 只删文件，**空目录壳仍留在 `lsf` 列表**；补 `timeout 120 rclone rmdir "pikpak:Movie/<目录>/"` 才彻底移除。验证：删除后 `timeout 60 rclone lsf` 目录名应从列表消失。下载到本地验证完整后必须删 PikPak 源（用户规则）。
- **aria2 显示 0KB/s 但文件已是满大小 ≠ 卡死**：aria2 预分配文件，`stat` 看到完整大小但速度 0 可能是下载已完成、只是 `.aria2` 控制文件残留（进程被杀/异常退出时常见）。**验证法**：杀进程 → `rm .aria2` → 用 `--continue=true` 重启同一 URL，若立即报 `Download has already completed` 说明文件其实完整，直接 ffprobe 校验后入库（2026-08-01 池畔谋杀案案例）。
- **并发上限 3**：用户明确要求最多同时下 3 个文件（2026-08-02）。批量下载用并发计数循环（`pgrep -fc aria2c` 计数 + 等待槽位）或 `xargs -P3`，不要一次全开。NMSL-011 等大文件挂后台慢慢爬即可。
- **"中文字幕"磁链标注不可靠**：NMSL-011 磁链名标"中文字幕"但 ffprobe 无字幕流、抽帧也无硬字幕（只有水印）。电影下载后同样要验证内嵌字幕：`ffprobe -select_streams s` 查字幕流；无流时**抽帧 + OCR 查硬字幕**（`ffmpeg -ss <秒> -i file -frames:v 1 -vf scale=480:-1 /tmp/f.jpg` + 本地 RapidOCR `/opt/data/ocr_venv`），多抽几帧（对白多的位置如 600/2400/4200s）。确认无字幕要如实告知用户，别当有中字版入库。
- **🚨 无字幕流但有"烧录硬字幕" = 也算中字版合格（2026-09-07 知无涯者案例）**：WEB-DL 中字版常是**烧录硬字幕**（中文字幕烧进画面，无音轨字幕流）。`ffprobe -select_streams s` 返回空 ≠ 没中字。必须抽帧 OCR 分辨两态：抽帧出中文对白 = 硬字幕**合格**，可正常入库；抽帧无字/只有水印 = 真无中字，如实告知。知无涯者 PARKHD 版即无字幕流但 OCR 在 1800s/3000s 抽出"起来国王要来了"等中文对白 → 中字确认入库。
- **假种子/截断种子（2026-08-02 野兽女孩事故）**：磁链标注 720P 完整版，下载后 ffprobe 发现时长只有 **4分45秒**（6840帧）——种子本身是截断/假货，PikPak 离线 + aria2 拉回全程无异常，只有 ffprobe 时长能识破。**每部电影下完必须核对时长是否符合预期**（野兽女孩 108 分钟 vs 实际 4分45秒 → 换另一个磁链 `6115DA56` 拿到 1.31GB 完整版）。不要只看文件大小/有无字幕流就入库。同类坑：小文件（<500MB 的"完整电影"）尤其要怀疑。
- **🚨 WebDAV 对新移出文件同步延迟（2026-08-27 知无涯者实战）**：pikpakapi `file_batch_move` 把视频移出到 `Movie/` 根后，**rclone/WebDAV 可能数分钟看不到该文件**——`rclone lsf` 返回空、`--dir-cache-time 0s` 仍不可见，但 pikpakapi `file_list` 已确认文件在根目录。这是 **PikPak WebDAV 服务的索引同步延迟**（非 rclone bug）。**对策**：移出后不要立即下载，用后台脚本每 30-60s 探测 `timeout 50 /tmp/rclone lsf --dir-cache-time 0s pikpak:/Movie | grep 文件名` 直到可见再启动 WebDAV 拉回（上限 ~30 分钟轮询）。批量移出多文件后通常等几分钟即可见（5 部电影场景），**单文件移出后立即探测常遇延迟**——别以为移出失败，继续等。
- **无字幕版入库标注**：用户允许"入库但标注清楚无字幕"（2026-08-02 野兽女孩：韩语无字版按用户要求入库，文件名加"韩语无字幕"标注，用户自己想办法补字幕）——入库前问用户或按用户要求标注，不要擅自拒绝入库。
- **avgood.com 站点结构（2026-08-04 水管工/野兽女孩）**：avgood 是中文成人影视资源站，分两种页面：`/c/` = **在线区**（仅播放，无磁链）、`/t/` 或下载二区 = **下载区**（有 `magnet:?xt=urn:btih:` 明文，`web_extract` 可提取）。同片可能有多个条目（不同大小/时长/清晰度），逐个检查。搜不到时用 `web_search site:avgood.com 片名`。菲律宾/韩国三级等资源该站覆盖面好，是 BT 之家之外的重要补充源。
- **flash2u 神魂颠倒论坛（2026-08-04）**：帖子会标注 `Subtitles Internal: Chinese`（内嵌中字），但下载链接常是第三方网盘（xunniufxp 等），**这些网盘链接容易失效/无法直接磁链**。处理：把网盘链接当作"存在中字版"的线索，去 avgood 或 BT 之家搜同片磁链版。
- **找片顺序（2026-08-04 验证）**：`web_search 片名 年份 中字 magnet` → BT之家(1lou.me) 种子附件 → avgood 下载区磁链 → flash2u（网盘链接仅作线索）。三个来源互补，全都没有再告知用户。
- **中字版搜索核心技巧（2026-08-27 五部经典实战）**：磁力熊/电影天堂只有无字原版时，**用 BTDigg 搜压制组种子名**——`MiniHD`/`BTBTT`/`高清影视之家`（BBQDDQ.com、HDBTHD.com、BBEDDE.com 等转发站），典型命名「片名[国语音轨+中文字幕/简繁字幕].1080p/2160p...」。优选「国语配音+中文字幕」WEB-DL 2160p 60帧版（爱奇艺/优酷源）和 REMUX 版（无损最大最清晰）。种子文件夹名带压制站前缀（【高清影视之家...】），处理同 jav：移出视频→删 3 个 www.HD 开头广告→file_list 验证后才删文件夹。
- **经典老片中字版寻找路径（2026-08-27 验证，5 部豆瓣高分片实战）**：① **磁力熊站内搜索**（EmpireCMS POST，见上表）——压制组中字版（CMCT/CHD）常直接命中；② **BTDigg 代理搜索**（限流友好间隔）——能搜到大量版本但中字标注少；③ 网盘站（bzswh.com / yhzyw.cc / wpxz.pro 等）——有"国语音轨/中文字幕"版但**只有网盘链接无磁链**，仅作"存在中字版"的线索，别死磕；④ hdchd.cc 等高清论坛有国英多音轨简繁字版但被 Cloudflare 拦（需浏览器过 CF）；⑤ 电影天堂（dytt8899）搜经典老片常无结果（GBK 搜索 + `--data-urlencode`）。**找不到内嵌中字版就如实告知用户，不直接用无字版**（用户硬规则）。
- **PikPak CDN URL 过期（2026-08-04 心灵猎人事故）**：批量取完 URL 后隔较久才启动 aria2，CDN URL 可能已过期——aria2 显示 INPR（下载中）但实际只拉到 **61-150 字节的空文件**，ffprobe `dur=` 为空，校验全挂。**症状不是报错而是静默空文件**。对策：① 取 URL 后尽快下载（别隔太久）② 校验失败时先看文件大小，<1KB 基本是 URL 过期 ③ 重新 `get_download_url` 换新 URL 再下（旧 URL 作废，重试同一 URL 没用）。
- **电影天堂剧集可能缺集（2026-08-04 心灵猎人）**：电影天堂版 8 集磁链缺 09/10 两集（那两集磁链在 PikPak 始终无种源），磁力熊整季种子 10 集齐全。**剧集优先用磁力熊整季种子**，单集散磁链有缺集风险。换源后记得清理旧版临时文件（`rm -rf /tmp/<旧目录>`）+ 停掉旧下载进程，避免占带宽。
- **磁力熊 cilixiong.org 剧集磁链源（2026-08-04 怪奇物语实战）**：`/drama/<id>.html` 页面列出整季多个压制版本（RARBG x265 小体积 / SHORTBREHD BluRay x264 高清大体积），`web_extract` 直接提取 `magnet:?xt=urn:btih:` 明文。**用户偏好选最大的高清版**（见上文版本偏好）。dytt8899 站内搜不到的美剧（如怪奇物语）优先查磁力熊。BT蚂蚁 btmayi.cc 是导航站（列其他磁力搜索器），搜索结果需 JS 渲染，不如磁力熊直接。
- **压制组自带字幕检查（2026-08-04 怪奇物语 SHORTBREHD）**：种子文件夹常含 `Subs/` 子目录（VobSub 格式 `.sub`+`.idx` 对，16 文件 = 8 集 × 2）。**先检查种子文件夹内部结构再决定要不要找外挂字幕**——`file_list` 列出文件夹，若含 Subs 子目录则自带字幕（.idx 头部有 `# VobSub index file` + `size: 1920x1080` 确认清晰度），无需再去字幕站。
- **字幕站验证码（2026-08-04 实测）**：subhd.tv / zimuku.org 都有**云锁验证码**（curl 返回"网站防火墙"页面，subhd 里埋伪内容诱饵"YYeTs字幕组..."实为验证码页）；yyets.com 直连超时。**不要死磕字幕站**——优先找压制组自带字幕（Subs 文件夹 / mkv 内封字幕流），或直接告知用户。用户提供字幕站：yyets.com、subhd.tv、zimuku.org（需代理，遇验证码需浏览器过滑块）。

## 参考

- `references/colombiana-20260801.md` — 《致命黑兰》完整实战：磁链搜索路径、种子→btih 提取、站点可用性实测
- `references/madame-claude-20260801.md` — 《应召女王》第二次实战：多译名搜索、种子附件 id 定位、版本筛选
- `references/batch-4-movies-20260801.md` — 批量下载 4 部电影：多译名识别、CDN 全节点 503 恢复模式（等 10 分钟重取 URL）、广告文件过滤、批量 aria2 脚本
- `references/nysm3-nmsl-20260802.md` — 惊天魔盗团3 下载 + NMSL-011 换 2.6G 中字版：限速死局换版、jav_manager 处理番号、"中文字幕"标注不可靠、抽帧 OCR 字幕验证标准流程
- `references/beastie-girls-20260802.md` — 野兽女孩下载：假种子识别（时长验证）、换源、无字幕入库标注决策
- `scripts/btih_from_torrent.py` — 从 .torrent 提取 btih hash 的脚本

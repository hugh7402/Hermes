# 批量下载 4 部电影实战 — 2026-08-01

用户一次要求下载 4 部电影：《请做我的主人》《应召女王》《池畔谋杀案》《致命黑兰》。验证了**批量场景**的完整流程，含 PikPak CDN 503 故障恢复。

## 结果

| 电影 | 真实片名 | btih | 版本 |
|:----|:----|:----|:----|
| 请做我的主人 | Be.My.Master.2018（请做我的奴隶2） | D348F3BCD2B3257CD773BFC69E06B0A0E3E5B322 | 2.45GB BD1080P 日语中字 |
| 应召女王 | Madame.Claude.2021 | BA667B191E624DB68183159089FE33F795197212 | 2.72GB 1080p 中文字幕 |
| 池畔谋杀案 | Swimming.Pool.2003 | C61CDEE52F915D7F5709576B24C6FD2D2B76DE33 | 2.28GB 1080p（帖标英语中字） |
| 致命黑兰 | Colombiana.2011 | F3975BF8951151F344F44617637860E3A6BC2C2D | 3.25GB 1080p 中文字幕 |

全部经 1lou.me 种子附件 → btih 提取 → PikPak 离线成功。

## 片名识别要点

- **《请做我的主人》= Be My Master (2018)**，日本情色剧情片，导演城定秀夫，是《请做我的奴隶》(2012) 的续作。种子里文件名被过略成 `请做W的奴L2：请做W的主人`——BT 站常见规避词，不影响 btih。
- **《池畔谋杀案》= Swimming Pool (2003)**，台湾译名，大陆叫《泳池情杀案》，欧容导演。搜索时三个译名都要试。
- 中文译名差异大（大陆/台/港不同），`web_search` 轮换关键词：`"台译名" OR "港译名" OR "大陆译名" + 年份 + 1080p + 中字`。

## 批量下载脚本模式（PikPak CDN 503 恢复）

**现象**：4 个新取的 CDN URL 全部 `errorCode=29 status=503`，aria2 预分配文件后中断。这是 PikPak CDN 间歇性故障（非单文件限速）。

**处理**（已验证模式）：
1. 杀掉所有失败的 aria2 进程，`rm -f` 残留文件（含 `.aria2` 控制文件）
2. 写 `retry_movies.sh`：先 `sleep 600`（10 分钟）→ 重新 `get_download_url` 换新 URL（旧 URL 已过期）→ 重新启动全部 aria2 → `wait`
3. 后台跑（`terminal background=true` + notify_on_complete），完成后汇报

关键点：
- **旧 URL 重试无效**，必须重新调 `get_download_url` 拿新 URL
- 4 个文件并发下载用 shell 脚本 + `&` + `wait`，每个 aria2 独立进程、独立日志 `/tmp/dl_<片名>.log`
- URL 从 Python 写到 `/tmp/movie_urls.txt`（`名称|文件名|URL` 管道分隔），shell 用 `IFS='|' read` 解析——**注意 URL 本身含 `|` 时按最后 2 个字段解析**（`parts[0]` 名称、`parts[1]` 文件名、`'|'.join(parts[2:])` URL）
- PikPak 文件夹内广告文件（0 字节 .png/.doc/.pdf/.mkv）：`size > 100000000` 才取 URL，其余跳过

## 与单部下载的差异

- 每部电影一个参考文件太重，批量场景写一个总记录即可
- aria2 并发上限 5（用户 PikPak 策略），本批 4 部 + NMSL-011 刚好 5 个，不再加
- 所有磁链仍从 1lou.me 拿种子 → `scripts/btih_from_torrent.py` 提取，站内搜索比 web_search 更可控

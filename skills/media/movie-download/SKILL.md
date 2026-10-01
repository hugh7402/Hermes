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

## 🚨 用户规则：不要自动续下后续季 / 系列续作（2026-09-15 明确）

交付一季/一部之后，**不要自己接着下载后续季或同系列续作**。用户原话：

> “不要下载黑钱胜地第二季，我先看看第一季，如果好看我会告诉你下载”

- 可以**列出**后续季的可下性（hash / 源 / 体积）供用户决策，但**不要直接加离线、不要开始下载**
- 用户没明确说“继续下”之前，下一季一律不动
- 同理适用于系列电影、同一 UP 主/压制组的其他作品（例：B站搜到其他米兰纪录片时，先问再下）

## 🚦 第 0 步：开工前先确认「这片子存在 + 已上映」

用户报「片名 + 年份」时，**先用豆瓣 suggest 接口把同名条目一次列全**，别直接开搜资源站：

```bash
curl -s --noproxy '*' -A "$UA" "https://movie.douban.com/j/subject_suggest?q=<urlencode 片名>"
# → JSON 数组：[{"title":"街头霸王","year":"2026","type":"movie","id":"36344100"}, ...]
```

比 `web_search` 干净得多（无影评噪音），**是“这片名到底有哪几版”的最快证据**。

**实测案例（2026-10-01）**：用户要「美国片《街头霸王》，2006上映」。suggest 返回：
1994（尚格·云顿）/ 1994（日本动画）/ 2009（春丽传奇）/ 2014（暗杀拳）/ 2026（未上映）——
**2006 年根本没有这部片子**（「2006」只出现在 2006-11 卡普空宣布要拍新街霸电影的新闻里，
那部后来成了 2009 年的《春丽传奇》）。

**此时的做法**：**不要猜着下**。列出全部条目 + 用 `clarify` 让用户指认，用户确认后再开工。
（本次用户答「是2026刚上映的街头霸王」→ 才发现是未上映新片。）

### 🚨 未上映 = 无源，不是「找不到」

**上映日期 ≠ 有资源**。核实渠道：片方/发行方官网 + 猫眼 `maoyan.com/films/<id>`（中国内地档期最准）+ 豆瓣。

- 北美上映日还没到 → 全网无数字版。**不要报“找不到资源”，要报“还没上映”**
- **枪版通常上映后 1-3 天**就出现在国内站；**正片数字版一般 45-90 天**（流媒体/蓝光）
- 交付时把「北美上映日 / 台湾港澳 / 中国内地档期」一并查清报给用户

**三站搜一遍就足以证明无源**：SeedHub `/s/<中文片名>` + 悠悠MP4 `search.htm?keyword=` + 磁力熊 站内搜。
本次《街头霸王》三站均无 2026 版条目（SeedHub 只有 1994 版 id=3351、2009 春丽传奇 id=3281）。

### ⚠️ 「未上映新片资源」一律是木马

搜「<未上映片名> 电影 下载」会命中一批站点，声称提供「<年份>真人版<片名>电影流鼻血版本下载」，
实际下载物是 **24MB 安卓 APK**（实测 `m.shouyouuv.com`）。**必须主动警告用户别点。**

### 未上映时给用户的三条路

1. **挂 cron 每天查源**（推荐）——上映/出枪版后自动通知
2. **先下同 IP 的旧版垫着**（例：《街头霸王》1994 版 SeedHub 有 4K 升频 2160p HDR10 21.02GB +
   1080p 4.55/7.95/8.11GB 四个版本，但**均无中字标注**，要中字得另找）
3. **上映后用户再喊**

### 同一片名在 SeedHub 可能对应多个 movie id

用中文名搜 `/s/<kw>` 后**每个 id 都要点开看年份再挑**——
实测「街头霸王」→ `3351` = 1994 版、`3281` = 2009 春丽传奇。**别默认第一个命中就是你要的那部。**

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

### 🎬 47BT 压制组 —— 中字美剧/剧集首选源（2026-09-15 黑钱胜地实战）

国内压制组，命名 `[47BT][中文剧名+季数]英文名.季.2160p.WEB-DL.HEVC.AAC`，**mp4 内为中英双语硬字幕**（无字幕流，须 ffprobe + 抽帧 OCR 验证，见下）。

- **搜法**：BTDigg 用**中文剧名**搜（`https://btdig.com/search?q=黑钱胜地`）比搜英文名命中率高得多——中文名条目往往是国内压制组的中字版
- 实测该组覆盖 Ozark 全四季（S01-S04 均有 2160p）
- 单集 2-5GB，一季 10 集约 33.5GB；离线 + WebDAV 15 并发约 25 分钟拉完
- 种子内含「封面以及截图」子目录（webp/jpg）——入库时可一并保留

### 🎬 Apple TV+ 纪录片：悠悠MP4 是首选（2026-09-25 史前星球 S3 实战）

Apple TV+ 独家的自然纪录片（《史前星球》系列等）**有完整中文压制版**，走悠悠MP4 一次命中：

- `curl -sL --noproxy '*' -A "$UA" "https://www.uump4.cc/search.htm?keyword=<urlencode 中文名>"`
- 结果标题格式：`[BT下载][史前星球：冰川时代][全5集][WEB-MKV/28.95G][简繁英字幕][4K-2160P][H265][流媒体][Apple][BlackTV]`
- 取帖子页的 `.torrent` 直链 → `torrent_to_magnet.py` 得 btih
- **BlackTV / ParkTV / DDHDTV** 是 Apple TV+ 源常见压制组，均带**简繁英内封字幕**

**实测（史前星球 S3 4K 版）**：28.95GB / 5 集 / btih `aa5880c9d48b090d6637c094dcb45342c933e73d`；mkv 内**41 条字幕轨**（含 `chi,Simplified` + `chi,Traditional`）；视频 hevc 3840×2160 **10bit**（真 HDR 色深）+ eac3 5.1。
- 种子含 3 个 `更多电视剧集请访问高清剧集网官网（www.DDHDTV/BTHDTV/BPHDTV）.png` 广告 → 离线后移出视频、删广告、删空文件夹
- PikPak 离线 **~1 分钟就全完成**；WebDAV 5 并行实测 ~60MB/s，29GB 约 **7 分钟**

**同期搜索实测**：磁力熊站内搜索 POST 返回 302（改了）；电影天堂搜“史前星球”无结果；6V 搜索 URL 404。**中文名搜悠悠MP4 命中率最高**，BTDigg 返回 429 限流。

### 🎬 SeedHub —— 批量中字磁链的**最强来源**（2026-09-27 变形金刚全系列实战）

**可用域名：`www.seedhub.cc`**（⚠️ `seedhub.icu` 已死，`seedhub.cc` 直连 200 无需代理）。
每部片子有 **60~130 个版本**，且**每个版本都有中字/国英标注**，是找「国英多音轨+简繁中字」4K 版的首选。

**两步工作流：**

1. **搜索拿电影 id**：`https://www.seedhub.cc/s/<urlencode 关键词>` → 正则 `/movies/(\d+)/`
   （⚠️ `/search?keyword=` 会 403；`/index/search` 404；**只有 `/s/<kw>` 能用**）
2. **取版本列表**：`https://www.seedhub.cc/movies/<id>/`，每个版本一个 `<li>`：
   ```
   title="变形金刚5[国英多音轨+简繁英字幕].Transformers...2160p.x265.10bit.HDR.4Audio-MiniHD[36.64G]"
     href="/link_start/?seed_id=493331&movie_title=..."
   / <code class="size">36.64G</code> <code class="seed-feature">蓝光</code>...
   ```
3. **磁链就在 link_start 页面的 base64 里**（关键发现）：
   `GET /link_start/?seed_id=<id>&movie_title=x`（带 `Referer: /movies/<id>/`）
   → 页面 HTML 里搜 40+ 字符 base64 串 → `base64.b64decode()` → 得到 `magnet:?xt=urn:btih:<40位>`
   （例：`bWFnbmV0Oj94dD11cm46YnRpaDo3YTgy...` → `magnet:?xt=urn:btih:7a826b0a97...`）
   ⚠️ **磁链不在页面文本/属性里**，正则 `magnet:` 搜不到，必须做 base64 解码。

**站点特征**：所有版本标 `蓝光`/`4K`/`杜比` 特征码；末尾 `[xx.xxG]` 就是体积；
部分片只有网盘版（href 是 `?redirect_to=pan_id_xxx` 而非 `?seed_id=`）——那就是**无 BT 种子**，别硬找。

**实战数据**：变形金刚 1-5+大黄蜂+超能（SeedHub 电影 id 272/788/607/759/2710/115450/110779），
选 HDH 系压制组（SSDSSE / DreamHD / MiniHD）的「国英多音轨+简繁中字」4K 版，7 部共 **236.5GB**，
PikPak 离线 **60 秒全部完成**，WebDAV 7 并行 **90 MiB/s / 52 分钟**拉完。

### 🚨 跨文件系统 mv 的坑：`stat -f -c %d` 会返回 0！

本机 **`/tmp` 在 overlay，`/opt/data` 在 zfsv3**，是两个文件系统。但用
`[ "$(stat -f -c %d /tmp)" = "$(stat -f -c %d /opt/data)" ]` 判断时**两边都返回 `0`**（失败值，不是 device id）
→ 误判为“同一文件系统” → 用 `mv` 实际触发 **236GB 跨盘拷贝**，被 terminal 超时打断，
**留下一个名字对但字节数截断的目标文件**（`-rw-------` 权限，大小只有一半）。

**正确做法**：
- 不要用 `stat -f` 判文件系统；查挂载点用 `df /tmp /opt/data`（看 Mounted on 列）
- 跨盘入库用 **`cp` + 字节比对 + 删源**，脚本**放后台跑**（`background=true, notify=true`）
- 拷贝前先检查目标是否已存在且字节数一致（幂等），可避免重复拷
- 截断判断依据只有一条：`源字节数 == 目标字节数`，不要相信文件名字或 `mv` 的返回值

### 🎬 8ziyuan.com —— 磁链从搜索摘要直接拿（2026-09-27 变形金刚实战）

**关键技巧**：`www.8ziyuan.com/forum.php?mod=viewthread&tid=<id>` 被 **Cloudflare 拦 curl（403）**，
但 **`web_search` 的 `description` 里会直接带着明文 `magnet:?xt=urn:btih:<40位>`** —— 不必打开页面！
搜 `"片名" 国英双音轨 特效双字 1080P 磁力` 常能一次命中。

实测《变形金刚》2007 由此拿到 `magnet:?xt=urn:btih:47C9F0CF48A9C9995342C5E7D8CCCCD6D51D9362`，
倒入 PikPak 后 **10 秒就离线完成**，文件为：
`变形金刚1(蓝光国英双音轨特效双字幕).Transformers.2007.BD-1080p.X265.10bit.HDR10.2AUDIO.AAC.CHS.ENG-UUMp4.mp4`

**UUMp4（悠悠MP4 自家压制组）命名解读**：`2AUDIO` = 国英双音轨，`CHS.ENG` = 中英双字幕，
`BD-1080p.X265.10bit.HDR10` = HDR10 10bit。

⚠️ **实测该组文件字幕是「烧录硬字幕」**：`ffprobe -select_streams s` 无输出（无字幕流），
但抽帧 OCR（**必须补 `mp4` 后綴看到**）出了中英双语对白：900s `别担心 / No,no,no. No worries.`、
3600s `比《世界末日》劲爆一百倍我对天发誓 / This is easily a hundred times cooler than Armageddon...` → **合格**。

⚠️ **两件事一定告知用户**：
1. **画面顶部有硬水印** `悠悠MP4 www.uump4.me`（该压制组所有文件都有）
2. **体积/码率偏低**：1080p + 双音轨只有 3.48GB（视频码率 **2.99 Mbps**，144 分钟）—— 远低于“高清大版本”标准，
   交付时要主动说明，别当高清版报上去

### 🎬 高码率中字版常只有夸克网盘（BT 磁链根本不存在）

实测《变形金刚》2007 的 4K 中字版只有网盘渠道，**别在这上面死磕**：

| 版本 | 规格 | 体积 | 渠道 |
|---|---|---|---|
| FRDS | `Transformers.2007.BluRay.2160p.x265.10bit.HDR.4Audio.mUHD-FRDS` 国英音轨+特效字幕 | 34.43GB | 夸克网盘（melost.cn / haoke100.com）|
| THDBST@HDSky | 欧版原盘 原生中字 DIY 次世代国语 简繁特效 | 89.17GB | bdshare.org（需登入）|
| tvmkv | `[BD-MKV/34.43GB][国英多音轨/简繁英字幕][4K-2160P]` | 34.43GB | tvmkv.com 帖子**回复可见**（磁链不在 HTML 里）|

**发現它们的方式**：`web_search "片名 4K 国英音轨 特效字幕 磁力"` → 搜到目录站（melost.cn / haoke100 / pd.qq.com）
能看到 **文件清单**（确认规格）+ 网盘链接，但**磁链拿不到**。要如实告诉用户，并给 BT 可得的最优替代。

### 🏆 SeedHub —— 内嵌中字影视资源的头号来源（2026-09-27 变形金刚全系列实战）

**抖音/磁力熊/悠悠MP4全没中字版时，SeedHub 一次解决。** 本 skill 自带的 `scripts/seedhub_fetch.py` 已封装全部流程。

**域名**：用 `www.seedhub.cc`（直连 200，**无需代理**）。⚠️ `seedhub.icu` 已死（直连/代理均 HTTP 000）。

| 用途 | 正确写法 |
|---|---|
| 搜索 | `https://www.seedhub.cc/s/<urlencode 关键词>` ← **唯一可用**（`/search?keyword=` 一律 403）|
| 影片页 | `https://www.seedhub.cc/movies/<id>/` |
| 取磁链 | `https://www.seedhub.cc/link_start/?seed_id=<id>&movie_title=x`（**必须带 `-e <影片页URL>` Referer**）|

**🚨 磁链是 base64 藏在 link_start 页面里的**——页面里搜不到 `magnet:` 字符串，但有一段裸 base64：
```
bWFnbmV0Oj94dD11cm46YnRpaDo3YTgyNmIwYTk3NzU1M2RiZDkwMWM2NDFhMDk1ZjM5ODU4NDlkMWVk
解码 → magnet:?xt=urn:btih:7a826b0a977553dbd901c641a095f3985849d1ed
```
抓法：正则捞 `\b[A-Za-z0-9+/]{40,200}={0,2}\b` → 逐个 `base64.b64decode` → 取 `startswith('magnet:')` 的那个。

**影片页版本表解析**（一次拿到全部版本，含中文标注、体积、特征）：
```html
<a title="变形金刚5：最后的骑士[国英多音轨+简繁英特效字幕].Transformers.….UHD.BluRay[36.86G]"
   href="/link_start/?seed_id=493330&movie_title=…">…</a> / <code class="size">36.86G</code>
   <code class="seed-feature">蓝光</code><code class="seed-feature">4K</code></li>
```
正则：`title="([^"]{10,400})"[^>]*href="/link_start/\?seed_id=(\d+)[^"]*"[^>]*>.*?</a>\s*/\s*<code class="size">([^<]*)</code>(.*?)</li>`

**⚠️ `seed_id=` vs `redirect_to=pan_id_` —— 决定性的判据**：
- `href="/link_start/?seed_id=NNN"` → **有 BT 种子**，能解析出磁链 ✅
- `href="/link_start/?redirect_to=pan_id_NNN"` → **只有网盘链接（夸克/阿里/百度），没有磁链** ❌

**先数 `seed_id=` 的个数再动手**。实测《变形金刚：起源》(2024) 整页 96 个 link_start **全是 `pan_id_`** → 该片在 SeedHub 拿不到 BT 磁链，要去别处（该片至今只有网盘渠道）。

**实测命中率**：变形金刚系列 **7/8 部**一次拿到 `[国英多音轨+简繁中字]` 的 4K UHD 磁链（HDH 系压制组 **SSDSSE / DreamHD / MiniHD**），单部 25-39GB；每部影片页 56-133 个版本，其中带中文字样的 7-35 个。

**版本挑选：按「规格匹配」，不要按「体积最大」**（本 skill 的"高清大版本"偏好在这里会翻车）：
- ✅ 首选 `[HDR+杜比视界双版本][国英多音轨+简繁英特效字幕].<年份>.UHD.BluRay.2160p.x265.DV.HDR.TrueHD.Atmos-SSDSSE`
- ❌ 同片的 `...UHD.BluRay.REMUX...-NukeHD` 会到 60-77GB。**本次按"体积最大"自动挑，差点选中 61.92G 的 REMUX**，应选同规格 25.42G 的 DreamHD 版。
- 规则：**先锁定规格（2160p + 国英多音轨 + 简繁中字 + DV/HDR），再在同规格里挑体积大的**。

### ① 找磁链——站点可用性实测（2026-08-01）

| 站点 | 状态 | 说明 |
|:----|:----|:----|
| **磁力熊 cilixiong.org** | ✅ **影视剧首选源** | 用户 2026-08-04 定：**质量比电影天堂好**。⚠️ **cilixiong.com 域名已停放（2026-08-27 验证），用 `.org`**。`/drama/<id>.html` 整季页面列出多版本（2160p/1080p，含大小标注），`web_extract` 直接拿全部 `magnet:?xt=urn:btih:` 明文。优先 `web_search site:cilixiong.com 片名` |
| **磁力熊站内搜索（EmpireCMS）** | ✅ 2026-08-27 验证 | POST `https://www.cilixiong.org/e/search/index.php`，**必须带全参数** `classid=1,2&show=title&tempid=1&keyboard=关键词`（缺参数返回"信息提示"JS 跳转页，不是搜索结果）。需 `Referer` + UA，且**必须直连**（`curl --noproxy '*'`）——2026-09-16 实测：**走代理返回空/骨架页，直连 HTTP 200**。同类：国内影视站一律先直连试，别默认套代理。**电影结果在 `/movie/<id>.html`，剧集在 `/drama/<id>.html`**（旧版只记了 drama——电影分类在 movie 下）。压制组中字版常在这里，如 `摔跤吧！爸爸.2016.1080p.简繁中字￡CMCT梦幻.12GB` |
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

### 🎬 找内嵌中字版：悠悠MP4（2026-09-16 碟中谍8 实战，中字源命中率最高）

**磁力熊只有国际版无中字时，第一站转悠悠MP4**。本次磁力熊给的 4 个磁链全是 YTS/RMTeam 无字版，页面自己写“下载字幕请前往 Subhd/Zimuku”（= 不符合用户内嵌中字硬规则）；悠悠MP4 一次搜出 **40+ 个版本**，国语/中字版一应俱全。

- 搜索（**直连**）：`curl -sL --noproxy '*' -A "<UA>" "https://www.uump4.cc/search.htm?keyword=<urlencode 片名>"`
- 结果标题自带规格，直接筛：`[国英多音轨+简繁英双语特效字幕]` / `[简繁英字幕]` / `[国语配音/中文字幕]` / `[无字片源]`，加 `1080P` / `4K-2160P` 与体积
- 帖子页正文**没有磁链**，但页面里有 **`.torrent` 直链**（`https://bt.uump4.cc/btdown/YYYY/MM/DD/<hash>.torrent`）→ curl 下载后用 bencode 解析 info dict 得 btih 转磁链（`scripts/torrent_to_magnet.py`）
- 常见优质压制组：**DreamHD**（`片名[国英多音轨+简繁英双语特效字幕].2025.2160p.iTunes.WEB-DL.DDP.5.1.Atmos.HDR10+.H.265-DreamHD`，**字幕内封在 mkv**，不是外挂文件）；PandaQT 也常见
**版本挑选**：4K 2160p HDR10+ 30GB 级 / 1080p H.264 13GB 级（兼容性最好）。
⚠️ **但体积选择已被 2026-09-27 新规则覆盖：单片尽量≤1 0G，同档优先清晰度**（见上文规则段）。
下文提到的 30GB 级版本只在用户明确要求大版本时才选，并**主动说明 HDR/H.265 需要支持设备**。

**同日直连实测**：✅ 6V电影 66s6.cc、SeedHub seedhub.cc、飘花 piaohua.com、电影天堂 dytt8899.com、BT蚂蚁 btmayi.cc（导航站，`?s=` 只给其他搜索引擎入口，不给磁链）；❌ `1lou.me`/`btbuluo.net`/`grab4k.cn` 直连 HTTP 000（改用 `web_extract` 试）；⚠️ `hdchd.cc`/`space-empires.com` 等高清 Discuz 论坛（DreamHD/REMUX 首发，标题写明“国英多音轨+特效中文字幕”）**只剩 3-5KB 登录壳页，拿不到 magnet**——别在这耗时间，去悠悠MP4 找同版种子。

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

> ⚠️ **版本选择偏好——已变更（2026-09-27 用户明确，覆盖早前规则）**：
> **单片尽量 10G 以内，同档优先清晰度高的**。原话：“以后下载不要下载 30 多GB 大小一个的影片，尽量下载 10G 以内，优先清晰度高的下载”。
>
> 实操含义：
> - **先看体积，再看规格**——30-60G 的 REMUX / 4K 原盘不要选（即使带中字），除非用户特别要求
> - 在 **≤ ~11G** 的候选中挑**清晰度最高**的：4K/2160p + HDR > 4K 无 HDR > 1080p BluRay > WEB-DL
> - 实测最优档通常是 **`2160p.iTunes.WEB-DL.DD5.1.HDR.H.265-*`（BATWEB / PandaQT）**：约 9-11G，带 4K HDR + 国英多音轨 + 简繁英字幕，性价比最高
> - 其次 `UHD.BluRay.2160p...x265.10bit.HDR-ALT` 约 12-13G（稍超但源更好，可酌情）
> - 旧规则（2026-08-04“选最大版本”，如怪奇物语选 26.69G）**作废**，不要再按体积取最大

- 移入用 cp 后台 + 校验大小一致（rsync 未安装，用 `cp` + 手动对比字节数；跨文件系统 mv 会超时被截断）
- 移入后删 /tmp 源文件

## 无 BT 源的流媒体独家内容（DAZN / Netflix 原创纪录片等）→ B站 + yt-dlp

有一类片子**在 BT 圈根本不存在**：流媒体独家出品、无蓝光/DVD 发行的体育/平台自制纪录片（案例：AC米兰 DAZN 纪录片《我们在一起很好 / Stavamo bene insieme》2022，用户要下载）。

**无源判定**：BTDigg 用**原文名 + 平台名 + 中文名**三路搜都没有相关命中（注意排除同名噪音：搜 `Stavamo bene insieme` 只出无关意大利语杂志 → 就是没有），就**不要再在 BT 站上耗时间**，转 B站。

**替代路径：B站（bilibili）**——国内字幕组/球迷会搬这类片子，常带机翻中文字幕：

1. `web_search`：`B站 中文片名 原名 全片 bilibili BV`
2. 探测确认是**全片**：`yt-dlp --no-warnings --dump-json "https://www.bilibili.com/video/BVxxxx"` → 核 `title` / `uploader` / `duration`，**时长与豆蔻/IMDb 对得上**（案例 93.5 分钟 vs 豆蔻 93 分钟）才是全片；否则只是片段
3. 下载（带字幕）：
```bash
yt-dlp -f "bv*[height<=1080]+ba/b[height<=1080]/b" --merge-output-format mp4 \
  --write-subs --write-auto-subs --sub-langs "all" --embed-subs \
  --retries 5 --fragment-retries 10 \
  -o "<目标目录>/<中文名>.<外文名>.年份.%(ext)s" "<B站URL>"
```
4. B站**未登录**通常最高 1080p（1080p60/4K 要大会员）——**分辨率上限就是搬运源的上限**，如实告知用户“这是全网最佳可得版本”，不要承诺 4K
5. 交付时说明“BT 无源”的结论 + 画质现实（用户关心源质量，别假装下了高清版）

**⚠️ B站标题里的“机翻中文字幕”可能是空头支票**（2026-09-16 AC米兰纪录片实测）：标题明写“机翻中文字幕”，但 `yt-dlp --list-subs` 只列出 `danmaku`；B站 API `https://api.bilibili.com/x/player/v2?aid=<aid>&cid=<cid>` 返回 `subtitle.subtitles: []`；全片 9 个时间点抽帧 OCR 也只有球衣名/水印 → **实际零字幕**。**下载前先核这三项**，别下完才发现没字幕（aid/cid 从 `yt-dlp --dump-json` 输出里捞）。

**确认无字幕时不要放弃**：不搞外挂字幕、也不用退货——用 `ai-subtitle-pipeline` skill 走 ASR 转写 + AI 翻译 + 内嵌（本次 93.5 分钟意大利语纪录片端到端约 15 分钟，生成 1319 条中文字幕，成功率取决于 ASR 是否支持该语种）。

**yt-dlp 安装**（本机 .venv 用 uv，PEP 668 环境无 pip）：
```bash
uv pip install --python /opt/data/.venv/bin/python yt-dlp
```

实战细节（含 47BT 与 B站两条路的分工、字幕模式）见 `references/streaming-exclusive-bilibili.md`。

### 🚨 rclone 从云端拉回**必须加 `--include` 过滤**（2026-09-27 驯龙高手事故）

云端 `/Movie` 里可能压着**历史遗留目录**（实测 `周星馳全集.Stephen.Chow.1988-2017.BluRay` **67.9GB / 25 个文件**）。
若直接 `rclone copy pikpak:/Movie /tmp/xxx` 而不加过滤，**会把它们全部拉下来**（已误拉 4.1GB 才发现）。

**正确写法**：
```bash
rclone copy pikpak:/Movie /tmp/dest \
  --include "How.to.Train.Your.Dragon*" \   # ← 必写，按本次片名过滤
  --transfers 3 --buffer-size 32M -v
```
- 多部不同名时堆多个 `--include`；片名有中文就用中文片名通配
- 下载后**立刻 `ls` 目标目录确认只有本次内容**，别等跑完
- 一旦误拉：`ps -eo pid,cmd | awk '/[r]clone copy/ {print $1}'` 取 PID（**不要用 `pgrep -f`，见下**），kill 后 `rm -rf` 误拉的目录

### 🚨 `pgrep -f` 在 for 循环里也会自杀（2026-09-27 再次踩到）

已知 `pkill -f '<模式>'` 会匹配到**自己的命令行**而自杀。
**同样的问题也发生在 `for p in $(pgrep -f 'rclone'); do kill $p; done`** —— 你自己的
`bash -c` 命令行里包含 `rclone` 字样，于是 `pgrep` 把当前 shell 也匹进去了，
结果最后一条命令自己被 SIGTERM（表现为 `exit_code: -15`，后续命令未执行）。

**安全写法**：
```bash
# ✅ 用 ps + [x] 技巧排除自身
for pid in $(ps -eo pid,cmd | awk '/[r]clone copy/ {print $1}'); do kill "$pid"; done
# ✅ 或先看再杀
ps -eo pid,cmd | awk '/[r]clone copy/ {print}'
```

## 踩坑记录

- **🔑 PikPak token 失效（`invalidate refresh token token index 3 not found`）→ 重新登录刷新（2026-09-15 黑钱胜地）**：`.pikpak_token.json` 里存有 `username`/`password`/`device_id`，直接重新 login 即可，不要以为账号被封：
  ```python
  old = json.load(open('/opt/data/.pikpak_token.json'))
  client = PikPakApi(username=old['username'], password=old['password'], device_id=old['device_id'])
  await client.login()   # 登录后把新的 access/refresh/encoded_token + device_id 写回同一 JSON
  ```
  **device_id 必须沿用旧的**（换新 device_id 可能触发风控）。
- **🧹 删云端文件夹用 `rclone purge` 一步到位**：`delete` + `rmdir` 两步法在文件夹含**子目录**时 rmdir 会报 `directory not empty`（黑钱胜地案例：残留「封面以及截图」子目录）。直接 `rclone purge "pikpak:/Inbox-JAV/<文件夹>"` 递归删除，一步干净。
- **🔠 pikpakapi `path_to_id` 大小写敏感（2026-09-16）**：`await client.path_to_id('/inbox-jav')` 返回**空列表** → `r[0]['id']` 抛 `IndexError`；必须写 `/Inbox-JAV`（与云端目录名完全一致）。取不到 folder id 时先核对大小写，别怀疑账号或目录被删。
- **📊 离线进度别用 `offline_list()` 判断**：PikPak 任务**完成后即从 `offline_list()` 列表移除**，常返回 `tasks: []`（看起来像“任务没建成功”）。**可靠判定**：轮询云端目标文件夹 `file_list(parent_id=<folder_id>)` 累计子文件大小，接近预期体积（≥99.5%）或连续 3 次不增长即算离线完成，再启动 WebDAV 拉回（本次 4K 30GB 大片即用此法，另外在线文件夹刚创建时大小显示 0.00GB 属正常）。
- **🧩 shell cwd 陷阱**：若在 `/tmp/xxx` 里执行过命令又 `rmdir` 了该目录，后续 terminal 调用的 shell cwd 仍是已删目录 → 报 `cd: No such file or directory` / `Exit 126`。**修法**：下一个 terminal 调用显式传 `workdir=/opt/data`。
- **🚫 `pkill -f '<模式>'` 会杀掉自己（2026-09-15 停黑钱胜地 S02 时）**：`pkill -f` 匹配**整条命令行**，而你的 terminal 命令行里恰好包含那个模式字符串 → 把自己所在的 bash 连同后续命令一起 SIGTERM 掉（表现为 `exit_code: -15`、后半段命令没执行、状态不可信）。**正确做法**：先 `pgrep -af '<模式>'` 看命中哪些 PID 并确认没有自己，再 `kill <精确PID>`；停后台任务优先用 **process 工具的 session_id**（`process(action='kill', session_id='proc_xxx')`），不要用 pkill -f 匹配长模式。
- **⏱ 后台下载的“完成通知”可能只代表包装 shell 退出（2026-09-15 黑钱胜地）**：`terminal(background=True)` 里写 `nohup rclone copy ... &` 时，**包装 shell 退出就发完成通知**（几十秒后），而 rclone 还在跑——别把那条通知当“下载完成”。**两种安全写法**：① 前台跑 rclone（通知与下载同寿）；② 另起一个等待脚本 `while ls <目录>/*.partial >/dev/null 2>&1; do sleep 30; done` + `notify=true`，那才是真正的完成信号。判断完成也要看**两个条件**：`.partial` 数量归零 **且** rclone 进程（`pgrep -af 'bin/rclone'`）已退出。
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
- **🚨 WebDAV 对新移出文件同步延迟（2026-08-27 知无涯者实战）**：pikpakapi `file_batch_move` 把视频移出到 `Movie/` 根后，**rclone/WebDAV 可能数分钟看不到该文件**——`rclone lsf` 返回空、`--dir-cache-time 0s` 仍不可见，但 pikpakapi `file_list` 已确认文件在根目录。这是 **PikPak WebDAV 服务的索引同步延迟**（非 rclone bug）。**对策**：移出后不要立即下载，用后台脚本每 30-60s 探测 `timeout 50 /tmp/rclone lsf pikpak:/Movie | grep 文件名` 直到可见再启动 WebDAV 拉回（上限 ~30 分钟轮询）。

> 🚨 **写完这条后自己踩的坑（2026-09-25 史前星球 S3）**：不要给 `rclone lsf` / `lsl` 加 `--dir-cache-time 0s`！那是 **VFS 专用 flag**，`lsf`/`lsl` 会直接报 `Error: unknown flag: --dir-cache-time` 并**输出 0 条**。轮询脚本里 `grep -c` 永远得 0 → 看起来像“同步一直不到位”，实际文件早就在了（白等 6 分钟）。
> **判据**：轮询计数恒为 0 **且** `rclone lsf` 的 stderr 里有 `unknown flag`。**验证命令能否用**：先手动跑一次 `timeout 60 rclone lsf pikpak:/Movie`，确认能列出内容再写进循环。真延迟与命令写错都会表现为“看不到”，先排除后者。批量移出多文件后通常等几分钟即可见（5 部电影场景），**单文件移出后立即探测常遇延迟**——别以为移出失败，继续等。
- **🎨 HDR 片源抽帧 OCR 必须先色调映射（2026-09-27 变形金刚实战）**：4K UHD 片源（`color_transfer=smpte2084`、primaries `bt2020`）直接抽帧会得到**发灰的低对比画面**，OCR 识别率极差甚至完全识别不到字幕，容易误判成"无中字"。**必须先 tonemap 再 OCR**：
  ```bash
  ffmpeg -ss 3600 -i in.mkv -frames:v 1 -vf "zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p,scale=1280:-1" -y /tmp/f.jpg
  ```
  实测色调映射后中英双语硬字幕正常识别（900s → `别担心 / No,no,no. No worries.`；3600s → `比《世界末日》劲爆一百倍我对天发誓 / This is easily a hundred times cooler than Armageddon...`）。① ffmpeg 按内容探测格式，**扩展名异常也不用先改名**；② HDR 片还要注意水印——UUMp4 组画面顶部固定有 `悠悠MP4 www.uump4.me`。
- **⛔ 别把 python 脚本输出接 `| head -N`（2026-09-27 静默丢产物）**：`python3 x.py | head -80` 在 head 读满 80 行后关闭管道 → python 收到 **SIGPIPE 被杀**，**脚本末尾的 `json.dump(...)` 等副作用根本没执行**。症状极具误导性：**stdout 看着完全正常**，但产物文件不存在或是旧版本（本次白跑一轮抓取，报 `FileNotFoundError` 才发现）。**正确做法**：
  ```bash
  python3 x.py > /tmp/out.log 2>&1; echo "exit=$?"; tail -40 /tmp/out.log
  ```
  长输出脚本一律重定向到文件再读，不要用 head/tail 截管道。
- **批量离线/拉回性能基准（2026-09-27 变形金刚 7 部 236GB）**：7 个磁链**同时** `offline_download`（间隔 2s）→ **60 秒全部离线完成**；`rclone copy` **7 文件并行 + `--buffer-size 32M`**（7×32M≈224MB，本机 15.7G 内存扛得住）实测 **85-91 MiB/s**，236GB ETA 约 40 分钟。**注意 rclone 会预分配**，`du -sh` 立刻显示满体积、`df` 立刻扣减 —— 别把预分配当"已下完"，判据是 `.partial` 归零 + 进程退出。
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

- 写会议发言稿/汇报讲演稿（三段式、按时长控字数）用 `speech-draft` skill——与下载无关，但手法可复用：用户发来的方案 PDF / 配置表 / 现场照片是"一手素材源"，检索结果只配当背景
- `references/colombiana-20260801.md` — 《致命黑兰》完整实战：磁链搜索路径、种子→btih 提取、站点可用性实测
- `references/madame-claude-20260801.md` — 《应召女王》第二次实战：多译名搜索、种子附件 id 定位、版本筛选
- `references/batch-4-movies-20260801.md` — 批量下载 4 部电影：多译名识别、CDN 全节点 503 恢复模式（等 10 分钟重取 URL）、广告文件过滤、批量 aria2 脚本
- `references/nysm3-nmsl-20260802.md` — 惊天魔盗团3 下载 + NMSL-011 换 2.6G 中字版：限速死局换版、jav_manager 处理番号、"中文字幕"标注不可靠、抽帧 OCR 字幕验证标准流程
- `references/beastie-girls-20260802.md` — 野兽女孩下载：假种子识别（时长验证）、换源、无字幕入库标注决策
- `scripts/btih_from_torrent.py` — 从 .torrent 提取 btih hash 的脚本
- `references/streaming-exclusive-bilibili.md` — 流媒体独家纪录片（DAZN 案例）无 BT 源时走 B站 + yt-dlp 的完整实战：无源判定、BV 探测、下载参数、画质现实、字幕模式
- `references/zh-movie-sites-direct-20260916.md` — 国内影视站**直连 vs 代理**探测结果、悠悠MP4→.torrent→磁链工作流、DreamHD 命名解读、碟中谍8 版本挑选与 PikPak 判定细节
- `scripts/torrent_to_magnet.py` — .torrent → btih → magnet（含 tracker 拼装 + 文件清单 + 外挂字幕文件检测），比 `btih_from_torrent.py` 多输出文件结构和字幕明细
- `scripts/seedhub_fetch.py` — **SeedHub 抓取器（内嵌中字首选源）**：搜索 / 列版本 / 解析 base64 磁链 / 自动挑 4K 国英多音轨+简繁中字最优版。`search` `versions` `magnet` `best` 四个子命令
- `references/seedhub-scraping.md` — SeedHub 站点结构详解、版本命名解读、`seed_id` vs `pan_id` 判据、变形金刚全系列实战数据（含各片 movie_id 与已解析磁链）

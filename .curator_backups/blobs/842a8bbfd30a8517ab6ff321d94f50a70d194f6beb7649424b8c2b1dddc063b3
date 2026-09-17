# 流媒体独家内容：无 BT 源时走 B站 + yt-dlp

**案例**：AC米兰纪录片《我们在一起很好 / Stavamo bene insieme》（DAZN, 2022, 93分钟）——用户 2026-09-15 要求下载。

## 一、片源情报（先搞清楚是什么片）

搜索确认三件事：**原名 / 出品方 / 时长**。

| 项 | 值 | 来源 |
|---|---|---|
| 中文名 | 我们在一起很好（又译：我们在一起曾经那么美好） | 豆蔻 / 虎扑 |
| 意大利语原名 | **Stavamo bene insieme** | 豆瓣 subject/36237053、IMDb tt24079772 |
| 出品 | **DAZN**（体育流媒体），2022-10-13 意大利上映 | 同上 |
| 时长 | 93 分钟（B站搬运版 93.5 分钟） | 豆瓣 / yt-dlp 探测 |
| 内容 | 2002-2007 安切洛蒂时代 AC米兰欧冠之路 | — |

> 意大利语片名翻译提示：中文译名可能有两种（“我们在一起很好”/“我们在一起曾经那么美好”）。**搜 BT 时两种都试**，但真正决定能不能搜到的是**原文名 + 出品方**。

## 二、无 BT 源的判定（省时间）

BTDigg 走代理，三路搜：

```bash
timeout 35 curl -s --proxy http://127.0.0.1:10808 \
  -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" \
  "https://btdig.com/search?q=Stavamo+bene+insieme+Milan"
```

- `Stavamo bene insieme Milan` → 只出无关意大利语杂志（同名词噪音）
- `Milan documentario DAZN` → 只出比赛录像（DAZN 直播源），无该纪录片
- `我们在一起很好`（中文名）→ **无磁链**

**判据**：三路全无相关命中 → 这是流媒体独家内容，BT 圈没有片源。**不要再换关键词死磕**（流量片才有多版本压制，平台自制纪录片基本没有）。

## 三、B站路径（实际可行的那条）

搜索：`B站 中文片名 原名 全片 bilibili BV` 或 `site:bilibili.com 片名 纪录片 中字`

本案命中：`BV1sG4y1T7f3`（UP主 Kris汀克里斯）
- 标题已写明：**【AC米兰】《我们在一起很好》机翻中文字幕 纪录片 Stavamo bene insieme（2022）…**
- 同页还有多个**片段**（如 BV1g8411s7pt 只有 1:31）——务必用时长区分，别把片段当全片

### 探测

```bash
yt-dlp --no-warnings --dump-json "https://www.bilibili.com/video/BV1sG4y1T7f3"
```

关注字段：`title` / `uploader` / `duration`（秒，除 60 对分钟）/ `entries`（分P，本案 1） / `formats`。

本案返回：时长 93.5 分钟、单P、15 个格式（720p/1080p 各有 avc1 / hev1 / av01 三系）→ **确认全片**。

### 下载

```bash
yt-dlp \
  -f "bv*[height<=1080]+ba/b[height<=1080]/b" \
  --merge-output-format mp4 \
  --write-subs --write-auto-subs --sub-langs "all" --embed-subs \
  --no-warnings --newline --retries 5 --fragment-retries 10 \
  -o "/opt/data/.dl_tmp/milan/我们在一起很好.Stavamo.Bene.Insieme.2022.%(ext)s" \
  "https://www.bilibili.com/video/BV1sG4y1T7f3"
```

- `bv*[height<=1080]+ba` 视频+音轨分开下再合并（B站标准做法，需 ffmpeg，本机 `/usr/bin/ffmpeg` 已装）
- `--write-subs --write-auto-subs --embed-subs` 同时尝试 up主字幕和自动字幕；若是硬字幕则拿不到字幕文件（不影响观看）
- 93 分钟 1080p 量级不大，后台跑即可

### 画质现实（要如实说）

B站未登录上限通常 **1080p**（1080p60/4K 需大会员）。这已是该片的“全网最佳可得版本”——BT 无源、DAZN 需订阅。交付时直说，不要让用户以为下到了 4K。

## 四、与 47BT 路线的分工

| 内容类型 | 走哪条路 |
|---|---|
| 商业剧集/电影（有压制组） | BT：BTDigg 搜**中文名** → 47BT 等压制组 2160p 中字 → PikPak 离线 → WebDAV |
| 平台自制纪录片、体育独家、无发行的综艺 | B站：yt-dlp，接受 1080p + 机翻中字 |

两条路的**校验与入库规则完全一致**：ffprobe 核时长（对得上豆瓣/IMDb）→ 字幕确认（无字幕流就抽帧 OCR 查硬字幕）→ 入库 `/opt/data/Movie/`（电影名按 `中文名.外文名.年份.扩展名`）。

## 五、环境

- yt-dlp 未预装，用 uv 装进主 venv（PEP 668，无 pip）：`uv pip install --python /opt/data/.venv/bin/python yt-dlp`
- B站**国内直连**，不需代理；BTDigg / 磁力熊需代理（`http://127.0.0.1:10808`）

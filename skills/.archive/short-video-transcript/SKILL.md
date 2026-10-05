---
name: short-video-transcript
description: "Use when 抖音/短视频要提取口播稿与屏幕文字。"
tags: [抖音, douyin, 短视频, 口播稿, 文案提取, 字幕, 逐帧OCR, 转录, 视频文字]
trigger: 用户发来抖音/快手/视频号的分享链接（v.douyin.com/xxx 这类），并要求"视频里讲了什么""有哪些产品/品牌/价格""把内容列成表"，或要求提取短视频的文案、口播稿、屏幕文字、字幕
---

# 短视频口播稿提取（字幕烧在画面里的视频 → 文字）

## 何时用

- 用户丢来一条**抖音/快手分享链接**，问「视频里推荐的 XX 有哪些/多少钱/什么牌子」
- 需要把短视频的**口播内容**变成可检索、可列表格的文字
- 视频**没有可下载的字幕文件**，文字是**烧录在画面里**的（竖屏短视频绝大多数如此）

**何时不用**：
- 视频有字幕轨/CC 字幕 → 直接 yt-dlp `--write-subs` 拿（见 `ai-subtitle-pipeline`）
- 需要的是**成品中文字幕文件**（而非文字内容）→ `ai-subtitle-pipeline`（ASR 转写 + 翻译 + 内嵌）
- 网页视频列表批量下载 → `u9-download`

**与 `ai-subtitle-pipeline` 的分工**：那个走 **ASR（听声音）**、产出 srt 给播放器用；
本 skill 走 **OCR（看画面）**、产出纯文本给「提取信息/列价格表」用。
烧录字幕的竖屏短视频用 ASR 也能做，但一般拿不到本地 ASR 引擎且口播常带背景音乐——OCR 更稳。

---

## 四步法

```
① 分享链接 → 视频直链（短链是 JS 空壳，必须走解析 API）
② 下载 mp4
③ ffmpeg 每秒一帧 → 百炼 qwen-vl-ocr 逐帧识别字幕
④ 合并连续重复 → 带时间戳的口播稿
```

---

## ① 解析分享链接

短链形如 `https://v.douyin.com/aBF2SmpTDhM/`。

### 先看清楚哪些路走不通

```bash
UA="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 ..."
# 短链 302 → https://www.iesdouyin.com/share/video/<item_id>/
curl -s -I -L --noproxy '*' -m 25 -A "$UA" "https://v.douyin.com/<code>/" | grep -iE '^(HTTP|location)'
```

- ✅ **短链 302 能解析出 item_id**（直连即可，不需要代理）
- ⚠️ `iesdouyin.com/share/video/<id>/` 返回 HTTP 200 但**只有 ~30KB 的 JS 空壳**，
  `_ROUTER_DATA` 只有 1.4KB，**没有视频直链**，别在这里翻
- ⚠️ **yt-dlp 支持抖音但要 fresh cookies**（报 `Fresh cookies (not necessarily logged in) are needed`）
  —— 这是**需要 cookie**，不是"下不了"；没有 cookie 就走解析 API
- ⚠️ 旧接口 `/web/api/v2/aweme/iteminfo/?item_ids=<id>` → **HTTP 200 size=0**（空响应）
- ⚠️ `/aweme/v1/web/aweme/detail/?aweme_id=<id>` → **403 `Blocked by ArgusSecurityPlugin Uifid Not Found`**

### ✅ 可用方案：第三方解析 API

```bash
curl -s --noproxy '*' -m 30 -A "$UA" \
  "https://api.xingzhige.com/API/douyin/?url=https://v.douyin.com/<code>/" \
  -o parse.json
```

返回 JSON（实测 2026-10 可用）：

| 字段 | 内容 |
|---|---|
| `.data.author.name` | 作者名 |
| `.data.stat` | like / comment / collect / share / aweme_id / time |
| `.data.item.title` | **标题 + 话题标签**（常含关键信息，先读这个） |
| `.data.item.duration` / `size` / `width` / `height` | 时长秒数 / 字节 / 分辨率 |
| **`.data.item.url`** | **无水印 mp4 直链**（长度可达 700+ 字符） |
| `.data.item.ury` | 另一路 CDN 直链（备选） |

> 🚨 **`.data.item.url` 是长 URL，别用"只打印短值"的调试脚本**：
> 过滤 `len(s) < 200` 会把视频直链整个滤掉，看起来像"解析结果里没有视频地址"。
> 正确做法是直接 `json.load()` 后按 key 取。

---

## ② 下载

```bash
curl -s --noproxy '*' -m 120 -A "$UA" -e "https://www.douyin.com/" -L \
  "$VIDEO_URL" -o video.mp4
ffprobe -v error -show_entries format=duration,size \
  -show_entries stream=codec_name,width,height -of default=nw=1 video.mp4
```

抖音下发多为 **hevc**、竖屏（如 576×768）、码率很低（30MB / 9 分钟）——画质不影响 OCR。

---

## ③ 逐帧 OCR（本 skill 最关键的一步）

### 抽帧

```bash
ffmpeg -v error -i video.mp4 -vf fps=1 -q:v 2 frames/f%04d.jpg -y
```

`fps=1` → **帧号≈秒数**，后面重建时间轴直接用它。9 分钟视频 = 553 帧。

### OCR：百炼 qwen-vl-ocr + **prompt 铁律**

```
POST https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions
Authorization: Bearer $BAILIAN_API_KEY
{"model": "qwen-vl-ocr-latest",
 "messages": [{"role":"user","content":[
    {"type":"image_url","image_url":{"url":"data:image/jpeg;base64,<b64>"}},
    {"type":"text","text":"Text Recognition:"}]}]}
```

### 🚨 prompt 决定"出文字"还是"出坐标框"

`qwen-vl-ocr` 是**专用 OCR 模型**，输出形态取决于 prompt。实测（同一批帧）：

| prompt | 输出 |
|---|---|
| **`Text Recognition:`**（官方任务关键字） | ✅ 纯文字 |
| `OCR this image. Output only the text you see, nothing else.` | ✅ 纯文字 |
| `OCR this image. Output only the text you see, line by line, nothing else. If no text, output NONE.` | ❌ **一堆坐标元组**：`498,878,55,305,90` |

**症状极具欺骗性**：API 返回 200、`content` 非空、字数很多，
但内容是 `x1,y1,x2,y2,角度` 的检测框——**看起来像"成功 OCR 了 553 帧"，实际一个字都没识别到**。

**对策**：
- 统一用官方关键字 **`Text Recognition:`**，不要自创 prompt
- `Document Parsing:` 会出带结构的 JSON/HTML（要版面时用）
- **跑全量前先抽 3 帧验证**：打印出来的必须是中文，一旦看到逗号分隔的 5 个数字就立刻停
- 后处理加一道哨兵：`if re.fullmatch(r'[\d,\s]+', text): 判定为坐标输出，报错`

> 同一个坑在 PDF OCR 也适用（`pdf_ocr.py`），详见 `knowledge-base-maintenance` skill。

### 并发与成本

- **并发 6**：553 帧 ≈ 242 秒（每帧约 466 token）
- 每帧 `total_tokens` 从响应的 `usage` 字段读，**累加后换算费用**
- 实测：553 帧 / **272,282 token / ≈¥0.08**（百炼 qwen-vl-ocr 按 ¥0.3 元/M prompt token）

🤖 **用户硬要求（2026-09-21）**：AI 转录/字幕类任务**必须精确计量 token 与费用并写进交付报告**，
不能只说"很便宜"。脚本里就累计 `usage.total_tokens`，收尾打印。

### 断点续传

每 20 帧把结果 `json.dump` 到磁盘。553 帧跑 4 分钟，中途中断不能白跑。

---

## ④ 重建时间轴

```python
import json, os, re
items = sorted(((int(re.search(r'(\d+)', k).group(1)), v) for k, v in ocr.items()))
lines = []
for t, v in items:
    v = re.sub(r'\s+', '', v or '')
    if not v or v.upper() in ('NONE', '无文字'):
        continue
    if lines and lines[-1][1] == v:
        lines[-1][0].append(t)      # 连续同文本 → 合并，记起止秒
    else:
        lines.append([[t], v])
```

输出两份：
- `timeline.txt` — `[ 14s] 首先是campfish` 带时间戳，便于用户回看原片
- `script_full.txt` — 纯文本，便于再喂给 LLM 做整理/提取

**顺带修词汇**：OCR 会把形近字认错，做后续提取时要人工对照。
实测例子：**"北禾婵" → 被识成"北禾矾"**、**"柳莺" → "柳荫"**、**"杆子" → "杯子"**。
若下游要拿型号去搜商品，**这些必须回去对照原片或商品页校正**，不能直接把 OCR 结果当型号名。

---

## 踩坑清单

1. **`python3 x.py | head -N` 会 SIGPIPE 杀脚本** —— head 读满就关管道，python 收到 SIGPIPE 被杀，
   **脚本末尾的 `json.dump(...)` 根本没执行**。症状骗人：stdout 看着完全正常，产物文件不存在或是旧版。
   正确：`python3 x.py > out.log 2>&1; echo "exit=$?"; tail -40 out.log`。
2. **脚本路径**：写文件时落在父目录、运行时 `cd 子目录 && python3 x.py` → `can't open file`。
   用 `cd <脚本所在目录> && python3 <裸文件名>`。
3. **竖屏字幕位置**：字幕常在画面底部 **85%–91%**（576×768 下 y=652–700）。
   裁剪能提速，但顶部还可能有贴纸/角标，**先用全帧跑一轮再考虑裁剪**。
4. **别跳过 `.data.item.title`**：标题+话题标签常已包含作者想要的大部分信息，
   先读它，可能不需 OCR 就能答（例：标题已写明"20+ 款小物竿"）。
5. **用户发抖音文字里的"复制打开抖音"口令**（`:4pm XmQ:/` 之类）是无用噪声，只用其中的 URL。

---

## 验收基准

实测案例：9 分 13 秒抖音鱼竿测评（553 秒 / 576×768 / 29MB），
553 帧 OCR **242 秒 / 272,282 token / ≈¥0.08**，得到 466 段带时间戳口播稿，
从中提取出视频里提到的 18 款鱼竿品牌型号 + 作者对各款的优缺点原话。
详见 `references/douyin-xiaowugan-case-2026-10.md`。

---

## 参考

- `references/douyin-xiaowugan-case-2026-10.md` — 完整实战：解析结果字段、帧 OCR 脚本要点、
  时间轴重建、OCR 错字纠正表、下游（去京东/淘宝查价）衔接方式

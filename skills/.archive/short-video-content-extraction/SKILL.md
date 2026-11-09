---
name: short-video-content-extraction
description: Use when 用户发来抖音/短视频链接要提取内容。取无水印源→烧录字幕逐帧OCR→还原口播稿。
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
tags: [抖音, douyin, 短视频, 口播稿, 烧录字幕, 逐帧OCR, qwen-vl-ocr, 字幕提取, 无水印, 视频文案, 快手, 视频号, 帧OCR, Text Recognition]
trigger: 用户发来抖音/快手/视频号等短视频链接并要求「视频里讲了什么」「把内容整理成表格」「列了哪些型号/产品」「还原文案/口播稿」，或需要从无字幕文件的视频里抽取文字内容
trigger-notes: 若视频有独立字幕文件/需要翻译内嵌，那是 ai-subtitle-pipeline 的活；本 skill 只管「从画面里把字抠出来」
---

# 短视频内容提取（链接 → 逐帧 OCR → 人物口播稿）

**场景**：用户丢来一个抖音链接，说「帮我把视频里的 XX 列出来」。
这类竖屏视频**没有字幕文件、也没有可下载的字幕**，但**口播字幕烧录在画面里**——
逐帧 OCR 就能把整片口播稿还原成文字，再从中抽商品/型号/要点。

## 何时用 / 何时不用

| 用 | 不用 |
|---|---|
| 抖音/快手/视频号链接，要视频里讲了什么、列了哪些东西 | 有独立字幕文件的片子 → `ai-subtitle-pipeline`（ASR/翻译/内嵌） |
| 视频有烧录字幕（画面里有文字），要还原文案 | 要下载整部电影/剧集 → `movie-download` |
| 无音轨可用/不想跑 ASR，只要文字 | 只要视频标题/简介 → 解析 API 的 `data.item.title` 就够了，别下片 |

---

## 第一步：拿无水印直链（抖音实测通路，2026-10-01）

### 1) 解析短链
```bash
UA="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
curl -s -I -L --noproxy '*' -m 25 -A "$UA" "https://v.douyin.com/XXXXXX/" | grep -i '^location'
# → https://www.iesdouyin.com/share/video/<item_id>/?region=CN&mid=...
```

### 2) 分享页是 JS 空壳（别在这耗时间）
`www.iesdouyin.com/share/video/<id>/` 直连 HTTP 200，页面里有 `_ROUTER_DATA`，
但**只有 1-2KB**，装的是 ua/webId/renderInSSR 之类的 shell 信息，**没有播放地址**。

### 3) ❌ 走过不通的路（已验证，别重复试）

| 通路 | 实测结果 |
|---|---|
| `yt-dlp "<短链>"` | `ERROR: [Douyin] <id>: Fresh cookies (not necessarily logged in) are needed`（yt-dlp 2026.08.19） |
| `www.douyin.com/aweme/v1/web/aweme/detail/?aweme_id=<id>` | `403 Blocked by ArgusSecurityPlugin Uifid Not Found` |
| `www.iesdouyin.com/web/api/v2/aweme/iteminfo/?item_ids=<id>` | HTTP 200 但 **size=0**（空响应） |
| 直接读分享页 HTML 找 `play_addr` / `.mp4` | 空壳页里没有 |

### 4) ✅ 第三方解析 API（本会话实测可用）
```bash
curl -s --noproxy '*' -m 30 -A "$UA" \
  "https://api.xingzhige.com/API/douyin/?url=<urlencode 分享链接>"
# 返回：{"code":0,"msg":"解析成功","data":{"item":{"url":"<无水印 mp4 直链>",
#        "title":"...","duration":552.8,"size":29154469,"width":576,"height":768,...}}}
```
然后直接拉：
```bash
curl -s --noproxy '*' -A "$UA" -e "https://www.douyin.com/" -L "$URL" -o video.mp4
```

> ⚠️ 解析 API 的 JSON 里**视频直链字段可能超过 200 字符**——
> 写探测脚本时别用 `len(url) < 200` 过滤长字段，否则会把真正的直链漏掉、
> 误以为"解析没返回地址"。

`data.item.title` / `duration` / `size` 先给用户看一眼确认是**同一条视频**再往下跑
（避免解析到同作者的另一条）。

---

## 第二步：逐帧 OCR（把烧录字幕抠出来）

```bash
# 1) 抽帧：1 fps 就够（字幕换行通常 1-2 秒）
ffmpeg -v error -i video.mp4 -vf fps=1 -q:v 2 all/f%04d.jpg -y
# 2) 逐帧 OCR（百炼 qwen-vl-ocr，并发 6-8，带断点续传）—— 用 scripts/frame_ocr_batch.py
# 3) 连续重复帧合并 → 时间轴 → 全片口播稿
```

### 🚨 坑位 1：prompt 写错，qwen-vl-ocr 会吐**坐标**而不是文字

`qwen-vl-ocr` 是**专用 OCR 模型**，输出形态由 prompt 决定。本会话实测：

| prompt | 输出 |
|---|---|
| `请提取图片中所有文字，保持原文段落结构。只输出文字，不要加解释。` | ❌ 553 帧**全部**返回 `498,878,55,305,90` 这种 x1,y1,x2,y2,angle **坐标元组** |
| `OCR this image. Output only the text you see, line by line. If no text, output NONE.` | ❌ 坐标 |
| `OCR this image. Output only the text you see, nothing else.` | ✅ 文字 |
| **`Text Recognition:`**（官方任务关键字） | ✅ 文字，最稳 |

**判据**：输出形如 `数字,数字,数字,数字,数字` → prompt 被当成 **Text Detection** 任务了。
官方任务关键字：`Text Recognition:`（识别文字）/ `Text Detection:`（只出框）/ `Document Parsing:`（出 JSON/HTML 版式）。

**铁律：跑全量前先抽 3 帧试 prompt，看到中文再开批。**
553 帧白跑一轮 = 浪费 240 秒 + 25 万 token。

### 坑位 2：OCR 结果的"有效字幕"必须去重
1 fps 抽帧时同一句字幕会跨 2-3 帧，直接拼接会得到重复段落。**连续相同即合并**，只记起止秒数：
```python
if lines and lines[-1][1] == txt:   # 与上一条相同 → 延长它的时间段
    lines[-1][0].append(t)
else:
    lines.append([[t], txt])
```
实测 553 帧 → **466 段有效字幕**（9 分 13 秒视频），可直接读成完整口播稿。

### 坑位 3：`python3 x.py | head -N` 会 SIGPIPE 杀掉脚本，**产物不写盘**
`python3 x.py | head -130` → head 读满即关管道 → python 收 SIGPIPE 被杀，
**脚本末尾的 `json.dump(...)` 根本没执行**。症状极具误导性：**stdout 看着完全正常**，
但产物文件不存在或是上一版。本会话**两次**踩到同一坑。
```bash
# ✅ 一律重定向到文件再读
python3 x.py > /tmp/out.log 2>&1; echo "exit=$?"; tail -40 /tmp/out.log
```

---

## 成本计量（用户**明确要求**每次汇报 token 与费用）

百炼 `qwen-vl-ocr-latest` 实测 **≈450-490 token/帧**（576×768 竖屏 + 短 prompt）。

| 项目 | 实测值 |
|---|---|
| 553 帧 / 并发 6 | 199 秒 |
| token | 250,554（≈453/帧） |
| 费用 | **≈¥0.075**（按 0.3 元/M prompt token） |

交付时必须写清：**帧数 / token / 估算费用**（用户 2026-09-21 明确要求）。

---

## 引擎选型：百炼 vs 本地 rapidocr

本地 `rapidocr_onnxruntime`（`/opt/data/ocr_venv`）免费、离线，但**中文准确率明显不如百炼**：

| 帧 | 百炼 qwen-vl-ocr | 本地 rapidocr |
|---|---|---|
| t=300s | 既有那种**直男**的粗旷感 | 既有那种**查男**的粗旷感 |
| t=480s | 一整套下来才100多 | `180.` \| `主线始` \| `S` \| `壹桶` \| 整套下来100多（噪声混入） |

品牌名/型号名这类**关键字错一个字整个结果就废**（本会话产出的就是 18 款鱼竿型号表）。
→ **这类任务优先用百炼**；本地引擎只当免费预筛或百炼不可用时的兜底。

---

## 第三步：从口播稿抽结构化结果

OCR 出的是**逐句时间轴**，不是结构化清单。用户真正要的往往是「有哪些型号 + 价格」这类表。

做法：读完整口播稿 `script_full.txt`，按作者讲述顺序切段落，
**每出现一个新主体（型号/品牌/产品）就开一条记录**，把后续形容它的语句归到这条下面。

> ⚠️ **OCR 会把同音/形近字认错**，涉及**标识符**（型号、货号、人名）时必须二次确认：
> 本会话把「北禾**蝉**」认成「北禾**禅**」、把「柳**莺**」认成「柳**荫**」。
> 拿不确定的型号去平台搜，**搜不到就用相邻信息（品牌+品类+规格）反查**，
> 并在交付时说明"视频口播作 X，实际型号为 Y"。别把 OCR 错字直接当型号报给用户。

**下游联动**：拿到型号后要查价/列价格表 → 走 `cn-shopping-links` 的
「查价格」章节（京东价格掩码、真实价三条通道、交付格式偏好都在那里）。

---

## 交付格式

- 用户要**表格**就给 markdown 表格；要**排序**先声明排序依据
- **暴露不确定性**：OCR 可能错字、型号可能对不上，逐条标注
- 长文本只留原创口播稿，把作者原话按主题归到各条下面（用户可能核对原话）
- 中间产物写 `.tmp_tests/`，需要时用 `MEDIA:` 发给用户

## 参考

- `scripts/frame_ocr_batch.py` — 逐帧 OCR 批处理（并发 + 断点续传 + token/费用统计）
- `references/douyin-20261001.md` — 抖音小物竿视频实录：解析 API 响应结构、
  prompt 对照实验、去重结果、18 款型号 OCR 错字纠正表

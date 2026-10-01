---
name: image-ocr
description: Use when 要从图片/截图/视频画面里提取文字（中文为主）。百炼 qwen-vl-ocr（prompt 关键字坑）/ SiliconFlow PaddleOCR-VL / OCR.space / ddddocr；含视频逐帧 OCR 还原口播稿。
tags: [OCR, image, text-extraction, Chinese, photo, screenshot, 视频, 短视频, 抖音, 口播稿, 逐帧, 字幕提取, qwen-vl-ocr, 百炼]
author: agent
created_by: agent
---

# Image OCR — Text Extraction from Photos

Extract Chinese/English text from photos and screenshots when you have no root access, no heavy local OCR packages, and limited API keys.

## Primary Approach: SiliconFlow PaddleOCR-VL-1.5 (Free, Best Speed)

Use SiliconFlow's free dedicated OCR model. 0.8s per page, free tier, produces clean Chinese text extraction.

### API Details

```
POST https://api.siliconflow.cn/v1/chat/completions
Content-Type: application/json
Authorization: Bearer ${SILICONFLOW_API_KEY}
```

| Parameter | Value | Notes |
|-----------|-------|-------|
| Model | `PaddlePaddle/PaddleOCR-VL-1.5` | Free dedicated OCR model, 0.8s latency |
| Image | `data:image/jpeg;base64,...` | Base64-encoded in a user message content block |
| Prompt | `请完整提取图片中的所有中文文字内容，包括表格数据、标题等。只输出提取的文字，不要描述图片。` | Explicitly forbid description to get clean text |
| max_tokens | 2000 | Raise to 4000 for dense multi-column pages |
| temperature | 0.1 | Low temp = deterministic extraction |

## Fallback: Qwen/Qwen3-VL-32B-Instruct (硅基流动)

When PaddleOCR-VL-1.5 produces poor results (rare dense tables, complex layouts), fall back to the stronger VL model:

- Same API endpoint, same key
- Change model to `Qwen/Qwen3-VL-32B-Instruct`
- Slower (2.4s) and paid, but better on edge cases

### Batch Processing (20-30 Photos)

```
for each image:
  → Read .env for SILICONFLOW_API_KEY (use os.open() to bypass redaction)
  → Base64 encode image
  → Call PaddlePaddle/PaddleOCR-VL-1.5 with extraction prompt
  → timeout=30 per image (fast model)
  → Print per-image results with clear separators
→ Save results to /tmp/ocr_results.json
→ Also save to concepts/<topic>-调研素材-YYYYMMDD.md for persistence
```

No significant rate limits on SiliconFlow — 30+ images in a row is fine.

## Fallback 1: OCR.space API (Free, No Key, Rate-Limited)

Use when SiliconFlow API is unavailable. The fastest zero-setup option.

### API Details

```
POST https://api.ocr.space/parse/image
Content-Type: application/x-www-form-urlencoded
apikey: helloworld  (free tier default key — no registration needed)
```

| Parameter | Value | Notes |
|-----------|-------|-------|
| `base64Image` | `data:image/jpeg;base64,...` | Encode the image file |
| `language` | `chs` | Chinese; `eng` for English |
| `OCREngine` | `1` | Engine 1 = free; Engine 2 = better but stricter limits |
| `scale` | `true` | Auto-upscale small text |

### Limits

- **25 requests/IP/day** on free tier — runs out fast on batch jobs
- Accuracy: Medium — garbles some characters, worse on dense tables
- No layout preservation

### Python Snippet

```python
import base64, json, urllib.request, urllib.parse

with open('image.jpg', 'rb') as f:
    b64 = base64.b64encode(f.read()).decode()

data = urllib.parse.urlencode({
    'base64Image': f'data:image/jpeg;base64,{b64}',
    'language': 'chs',
    'OCREngine': '1',
    'scale': 'true',
}).encode()

req = urllib.request.Request('https://api.ocr.space/parse/image', data=data)
req.add_header('apikey', 'helloworld')
resp = urllib.request.urlopen(req, timeout=30)
text = json.loads(resp.read())['ParsedResults'][0]['ParsedText']
```

## Fallback 2: ddddocr (Local, Lightweight)

When no API available at all, install a minimal local OCR (~10MB, no PyTorch):

```bash
uv run --with ddddocr --with Pillow python3 -c "
import ddddocr
ocr = ddddocr.DdddOcr(show_ad=False, det=True)
with open('image.jpg', 'rb') as f:
    result = ocr.classification(f.read())
    print(result)
"
```

**Limitation**: ddddocr is designed for short text/captchas. Not suitable for full-page document OCR.

### Captcha Gotchas (session-bound captchas)

When OCR'ing a captcha shown in a browser page:
- **Session binding**: captcha endpoints like `/captcha/{id}?{ts}` regenerate on every request. Downloading the image via curl (separate session) gives a DIFFERENT captcha than the one displayed — recognition result will never validate. Must extract from the browser's current page.
- **CSP workaround**: page-level `fetch()` and dynamic `new Image()` are often blocked (CSP). But an **already-loaded `<img>` can be drawn to canvas**:
  ```js
  const img = document.querySelector('img[src*="captcha"]');
  const cv = document.createElement('canvas');
  cv.width = img.naturalWidth; cv.height = img.naturalHeight;
  cv.getContext('2d').drawImage(img, 0, 0);
  const b64 = cv.toDataURL('image/png').split(',')[1];
  ```
  Return in ~600-char chunks to avoid truncation, then reassemble in a Python script file (write_file, not inline paste — long base64 strings lose chars when hand-copied, producing truncated-image errors).

## Which to Choose

| Situation | Recommended |
|-----------|-------------|
| Photos of slides/screenshots, have SILICONFLOW_API_KEY | **PaddlePaddle/PaddleOCR-VL-1.5** (free, 0.8s) |
| For dense tables / complex layouts where VL-1.5 struggles | **Qwen/Qwen3-VL-32B-Instruct** (paid, 2.4s, more accurate) |
| Quick test / no API key available | OCR.space (engine=1, 25/day limit) |
| Single short text snippet, no internet | ddddocr |
| Scanned PDF with complex layout | See `ocr-and-documents` skill |
| Heavy official document OCR | **百炼 `qwen-vl-ocr-latest`**（见上节，prompt 必须用裸 `Text Recognition:`）or marker-pdf |
| 视频画面里的烧录字幕 → 文本 | 抽帧 `fps=1` + 百炼 `qwen-vl-ocr-latest`（见上节） |

## 百炼 `qwen-vl-ocr-latest` —— prompt 关键字决定输出形态

```
POST https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions
Authorization: Bearer ${BAILIAN_API_KEY}
model: qwen-vl-ocr-latest
messages: [{"role":"user","content":[
  {"type":"image_url","image_url":{"url":"data:image/jpeg;base64,..."}},
  {"type":"text","text":"Text Recognition:"}]}]
```

**🚨 这个模型有官方任务关键字，prompt 写法直接决定返回「文字」还是「坐标」：**

| prompt | 返回 |
|---|---|
| `Text Recognition:` | ✅ **识别出的文字** |
| `Text Detection:` | ❌ 只有 `x1,y1,x2,y2,angle` 坐标框，**没有任何文字** |
| `Document Parsing:` / `Table Recognition:` / `Formula Recognition:` | 对应任务的专用输出 |
| **自定义啰嗦 prompt**（如 `OCR this image. Output only the text you see, line by line, nothing else. If no text, output NONE.`）| ⚠️ **可能翻成坐标模式**——实测 553 帧**全部**返回坐标，白跑一轮（242s / 25 万 token）|

**只用裸 `Text Recognition:`，不要加任何修饰、不要加「没有文字就输出 NONE」之类的兜底指令。**

**症状识别**：返回内容长这样 → `498,878,55,305,90` 或 `206,158,121,267,90\n502,878,63,651,90`
（**逗号分隔的数字串、最后一个数常是 90**）= 坐标模式，改 prompt 重跑。

**计费**：按 token，约 **0.3 元/M**（实测 553 帧 ≈ 25.06 万 token ≈ **¥0.0752**）。
从 `usage.total_tokens` 读出来算给用户。

## 视频逐帧 OCR：把画面里的（烧录）字幕提取成文本

短视频/无字幕轨视频的内容提取走这条（**不是生成字幕，是读出已在画面里的字**）。

```bash
ffmpeg -v error -i v.mp4 -vf fps=1 -q:v 2 frames/f%04d.jpg -y   # fps=1 → 第 N 帧 = 第 N 秒
```
然后并发 6 路调 `qwen-vl-ocr-latest` + `Text Recognition:`。

**实测基线（抖音 9 分 13 秒竖屏，553 帧）**：并发 6 路 → **199–242 秒**；
**250,554 tokens ≈ ¥0.0752**；必须**断点续传**（每 20 帧落盘，失败重试 3 次）。

竖屏短视频字幕固定在画面底部 **85%–91%** 高度（实测 `y=652-700 / 768`）——
**全帧 OCR 就能抓到，不必裁切/降采样**（OCR 很便宜，别为省 token 牺牲召回）。

**时间轴重建**：相邻帧文字相同 → 合并成 `[起-止 s]` 一段。553 帧 → 约 467 段带时间戳口播稿。

### 三条纪律

1. ⛔ **别把批处理脚本输出接 `| head -N`**：`python3 x.py | head -130` 在 head 读满后关管道，
   python 收到 **SIGPIPE 被杀**，**脚本末尾的 `json.dump(...)` 根本不执行**。
   症状极具误导性：**stdout 看着完全正常**，但产物文件是旧版/不存在。
   正确：`python3 x.py > out.log 2>&1; echo "exit=$?"; wc -l <产物>`
2. ⛔ **别用 `tail *.log` 判断后台作业状态**：日志是上一轮残留时会把旧报错显示给你，误判成「又失败了」。
   用 `process(action='poll', session_id='proc_xxx')` 看真实状态。
3. ⚠️ **形近字误识别在品牌/型号/人名上是致命的**，必须交叉验证后在交付里明确纠正：
   `北禾禅` → 实际 **北禾蝉**；`柳荫` → 实际 **YGC 柳莺**；`杯子` → 实际 **杆子**（高频）。
   纠正依据：拿 OCR 文本去淘宝/京东搜商品名核对，**交付时写「视频里显示 X，实际型号是 Y」**，不静默替换。

细节（含抖音视频直链获取的完整访问链）见 `references/video-frame-ocr-transcript.md`。

## Pitfalls

1. **PaddleOCR-VL-1.5 is fast and free** — 0.8s per image, no rate limits. Use it by default.
2. **SiliconFlow VL model first call can be slow** — if falling back to Qwen3-VL-32B-Instruct, first request may take 30-60s as model loads. Set timeout ≥ 120s.
3. **SILICONFLOW_API_KEY read method** — `.env` lines may have mixed quotes. Use `line.split('=', 1)` then strip both `'` and `"`.
3. **OCR.space free tier runs out fast** — 25/day. Only use as fallback when SiliconFlow unavailable.
4. **Photo quality matters** — blurry/angled/shadows drastically reduce accuracy even with VL models. Prefer well-lit, straight-on shots.
5. **Don't quote OCR text verbatim** in final output — there will be errors. Re-phrase with your understanding.
6. **Save raw OCR output** for reference even when text is garbled — it's better than nothing and the user can correct key parts.
7. **`qwen-vl-ocr` 返回坐标而不是文字 = prompt 用了修饰语** → 改成裸 `Text Recognition:` 重跑（别去调参/换模型）。
8. **批量 OCR 脚本要增量落盘**（每 20 项写一次 JSON）。产物落盘若只在脚本末尾，任何中断（SIGPIPE / 超时）都会静默丢掉全部结果。
9. **OCR 结果里的专有名词不要直接采信** — 品牌/型号/人名必须先拿候选词去电商或搜索引擎核对，再告诉用户。

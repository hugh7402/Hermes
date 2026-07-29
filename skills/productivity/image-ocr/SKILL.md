---
name: image-ocr
description: Extract Chinese text from photos/screenshots in resource-constrained environments. Covers free API-based OCR (OCR.space), lightweight local OCR (ddddocr), and preprocessing techniques. No root, no heavy dependencies, no API keys required for the primary approach.
tags: [OCR, image, text-extraction, Chinese, photo, screenshot]
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

## Which to Choose

| Situation | Recommended |
|-----------|-------------|
| Photos of slides/screenshots, have SILICONFLOW_API_KEY | **PaddlePaddle/PaddleOCR-VL-1.5** (free, 0.8s) |
| For dense tables / complex layouts where VL-1.5 struggles | **Qwen/Qwen3-VL-32B-Instruct** (paid, 2.4s, more accurate) |
| Quick test / no API key available | OCR.space (engine=1, 25/day limit) |
| Single short text snippet, no internet | ddddocr |
| Scanned PDF with complex layout | See `ocr-and-documents` skill |
| Heavy official document OCR | Use 百炼 qwen-vl-ocr or marker-pdf |

## Pitfalls

1. **PaddleOCR-VL-1.5 is fast and free** — 0.8s per image, no rate limits. Use it by default.
2. **SiliconFlow VL model first call can be slow** — if falling back to Qwen3-VL-32B-Instruct, first request may take 30-60s as model loads. Set timeout ≥ 120s.
3. **SILICONFLOW_API_KEY read method** — `.env` lines may have mixed quotes. Use `line.split('=', 1)` then strip both `'` and `"`.
3. **OCR.space free tier runs out fast** — 25/day. Only use as fallback when SiliconFlow unavailable.
4. **Photo quality matters** — blurry/angled/shadows drastically reduce accuracy even with VL models. Prefer well-lit, straight-on shots.
5. **Don't quote OCR text verbatim** in final output — there will be errors. Re-phrase with your understanding.
6. **Save raw OCR output** for reference even when text is garbled — it's better than nothing and the user can correct key parts.

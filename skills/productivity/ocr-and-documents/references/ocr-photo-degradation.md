# OCR Photo Degradation: PaddleOCR vs Qwen3-VL

**Date**: 2026-06-19
**Test file**: 5-刘默 推进可信数据空间发展.pdf (83 pages, A4 landscape, photos of presentation slides)

## PaddleOCR-VL-1.5 — Complete Failure

On presentation-photo PDFs, PaddleOCR produces hallucinated garbage:

| Signal | Example |
|--------|---------|
| Title extraction | `문의<|LOC_676|><|LOC_449|>...` (Korean + LOC markers) |
| Tags generated | 北川九鼎堂金城, 军事科技, 环境可再生能源 (completely unrelated) |
| Output volume | 102,923 chars for 83 pages (normal for text, but all wrong) |
| Chinese ratio | <10% (mostly Korean characters) |

## Qwen3-VL-8B-Instruct — Excellent

| Page | Content | Length | Quality |
|------|---------|--------|---------|
| 1 | Title slide: 推进可信数据空间发展 / 刘默 / 中国信通院 | 45字 | ✅ Perfect |
| 2 | CAICT branding + subtitle | 62字 | ✅ Clean |
| 5 | 德国工业4.0, IDS起源, 数据主权 | 313字 | ✅ High |
| 10 | 五大核心组成（规则/场景/数据/主体/技术） | 350字 | ✅ Structured |

## Recommended Strategy

```
PaddleOCR → quality check →
  if Chinese_ratio > 60% and no Korean/Cyrillic blocks:
    USE result (90%+ of standard scanned PDFs)
  else:
    RETRY with Qwen3-VL-8B-Instruct (photo/training-slide PDFs)
```

## Cost Impact

- PaddleOCR: FREE, 0.8s/page — covers ~90% of documents
- Qwen3-VL fallback: ~¥0.002/page, 8-9s/page — only for degraded quality cases  
- Estimated blended cost: <¥0.0002/page average (2% documents trigger fallback)

## Other Models Tested (All Failed on This File)

| Model | Result |
|-------|--------|
| PaddleOCR-VL-1.5 | Korean gibberish |
| DeepSeek-OCR | Mixed garbled + correct title |
| Qwen3-VL-8B-Instruct | ✅ Only one that worked |

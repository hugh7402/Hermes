# OCR Performance Comparison (Updated 2026-06-18)

## Current Recommendation: PaddleOCR-VL-1.5

| Model | Platform | Latency | Price/Page | Quality | Status |
|-------|----------|---------|------------|---------|--------|
| **PaddleOCR-VL-1.5** 🥇 | SiliconFlow | 0.8s | FREE | Good | ✅ Current |
| qwen3-vl-flash | 百炼 | 0.8s | ¥0.00015 | Good | Backup |
| qwen3-vl-plus | 百炼 | 1.5s | ¥0.001 | Better | — |
| Qwen3-VL-8B | SiliconFlow | 2.4s | Paid | Good | Old |
| Qwen3-VL-32B | SiliconFlow | 2.4s | Paid | Best | — |
| EasyOCR CPU | Local | 77s | Free | Medium | Too slow |
| PaddleOCR | Local | ❌ | — | — | Incompatible |

## Evolution

| Date | Model | Reason |
|------|-------|--------|
| 2026-06-18 | **PaddleOCR-VL-1.5** | Free, 3x faster than Qwen3-VL-8B, dedicated OCR |
| 2026-06-16 | Qwen3-VL-8B | Good but 2.4s, paid |
| Earlier | 百炼 qwen-vl-max | Free credits exhausted, 403 errors |

## Configuration

Script: `/opt/data/pdf_ocr.py`
```python
API_URL = "https://api.siliconflow.cn/v1/chat/completions"
MODEL = "PaddlePaddle/PaddleOCR-VL-1.5"
```

API key: `SILICONFLOW_API_KEY` in `.env`, read via `os.open()` fd bypass.

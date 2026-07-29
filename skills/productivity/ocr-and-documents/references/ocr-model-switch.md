# OCR 模型切换记录 (2026-06-18)

## 当前方案

| 项目 | 详情 |
|------|------|
| 模型 | `PaddlePaddle/PaddleOCR-VL-1.5` |
| 平台 | SiliconFlow |
| API | `https://api.siliconflow.cn/v1/chat/completions` |
| 延迟 | 0.8s/页 |
| 价格 | 免费 |
| 实现 | `/opt/data/pdf_ocr.py` |

## 切换历史

| 日期 | 从 | 到 | 原因 |
|------|------|------|------|
| 2026-06-18 | `Qwen/Qwen3-VL-8B-Instruct` (2.4s) | `PaddleOCR-VL-1.5` (0.8s) | 3x faster, 免费 |

## SiliconFlow 可用视觉模型

```
PaddlePaddle/PaddleOCR-VL-1.5     ← 当前
Qwen/Qwen3-VL-8B-Instruct
Qwen/Qwen3-VL-30B-A3B-Instruct
Qwen/Qwen3-VL-32B-Instruct
```

## 备选方案

| 模型 | 平台 | 延迟 | 价格 | 备注 |
|------|------|------|------|------|
| qwen3-vl-flash | 百炼 | 0.8s | ¥0.15/¥1.5 | SF不可用 |
| Qwen3-VL-32B | SF | 2.4s | 收费 | 识别最准 |

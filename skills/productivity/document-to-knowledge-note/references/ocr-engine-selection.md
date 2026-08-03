# OCR 引擎选型实测（2026-08-01 用户确认）

> 本机：CPU-only（Intel i3-N305, 8核, 15GB RAM, 无 GPU）。Python 3.13。
> 用户明确："以后所有OCR，优先用本地RapidOCR，效果不好再换成PaddleOCR-VL（现 API）"。

## 优先级

| 优先级 | 引擎 | 部署 | 单页耗时 | 备注 |
|:---:|:---|:---|:---:|:---|
| 1️⃣ | **RapidOCR**（rapidocr_onnxruntime） | 本地 `/opt/data/ocr_venv` | 5-50s（首次加载模型约48s） | 离线免费无超时；中文排版识别质量高（标点/换行规范） |
| 2️⃣ | PaddleOCR-VL-1.5（SiliconFlow API） | 云端 | 20-40s（含排队，60% 超时重试） | 仅本地效果不好时降级 |

## RapidOCR 安装与用法

```bash
uv venv /opt/data/ocr_venv
uv pip install --python /opt/data/ocr_venv/bin/python3 rapidocr_onnxruntime pymupdf
```

```python
from rapidocr_onnxruntime import RapidOCR
ocr = RapidOCR()                       # 首次实例化加载模型约48s
result, _ = ocr('/tmp/page.png')       # 输入 png 路径
text = '\n'.join(line[1] for line in result)
```

PDF 页转 png：`page.get_pixmap(dpi=150).save('/tmp/page.png')`（dpi=150 平衡质量与速度）。

实测质量：政府指南正文（黑体/宋体混排、条款编号）识别干净，标点/换行规范，优于云端 API 输出。

## SiliconFlow PaddleOCR-VL-1.5 已知问题（2026-08-01 实测）

- 约 60% 请求报 `The read operation timed out`（模型端点偶发故障/排队）
- 单页超时后重试 3 次会卡 3-6 分钟，27 页文档实测 18 分钟
- 251 个空壳文档全量回填若用 API 需 30-40 小时；本地 RapidOCR 预计 5-8 小时
- 恢复判断：带小图 payload 调 chat/completions，<30s 返回即恢复

## 相关脚本

- `/opt/data/scan_pdfs.py` — 全库 PDF 体检（PyMuPDF 探测页数/文字量/图片页/文字页），输出 `/tmp/pdf_scan_report.csv` 标 SUSPECT/EMPTY
- `/opt/data/re_ocr_shells.py` — 批量回填空壳 md（读 csv → 逐个 OCR → 覆盖写回），支持 `--only`/`--limit`；内置 ocr_pdf() 为 API 版，批量跑前应改本地引擎
- `/opt/data/ingest_docs.py` — `_pdf_probe()` + `_needs_ocr()` 结构判定（文字<50 / 页数≥3且文字<800 / 图片页占比>50% / ≥32MB且文字<2000 → OCR）

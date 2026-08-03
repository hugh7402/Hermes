# 本地 RapidOCR 批量修复方案 — 2026-08-01 用户拍板

## 背景

全库扫描发现 472 个 PDF 中 **364 个是扫描件**（无文字层），910 个 concepts md 中 **304 个 <2KB 疑似空壳**（正文丢失）。根因：`ingest_docs.py:70` 用 `len(text)<50` 判断是否扫描件，MarkItDown 提取出标题/通知文字（>50 字）就误判"文字版"，跳过 OCR，正文全丢。

## 用户选型决定（硬性，2026-08-01）

**OCR 优先用本地 RapidOCR**，效果不好再换云端 PaddleOCR-VL-1.5（SiliconFlow，会超时不稳定）。

- 本地 RapidOCR：`/opt/data/ocr_venv`（`rapidocr_onnxruntime` + `pymupdf`），CPU 5-50s/页，质量高（标点换行规范）
- 云端备用：SiliconFlow `PaddlePaddle/PaddleOCR-VL-1.5` API——2026-08-01 实测**连续 read timeout**（200KB 小图也 94s 超时），不可作默认

## 诊断工具

### 全库扫描（判断哪些 PDF 是扫描件）

`/opt/data/scan_pdfs.py` → 输出 `/tmp/pdf_scan_report.csv`，列含 文件/页数/文字层字符数/SUSPECT 标记。
SUSPECT 判定：文字层 <800 且页数≥3，或图片页占比高。

### 空壳判定（相对阈值，关键！）

**不要用绝对阈值（如 md < 3000B）**——62 页的文档只有 3.8KB 明显也是空壳，绝对阈值会漏掉。
正确标准：**md 大小 < 3000B，或 每页不足 150B**（62 页文档至少应 9KB+）：

```python
if not (sz >= 3000 and sz >= pages * 150):  # 是空壳，需要 OCR
```

## 批量修复脚本

`/opt/data/re_ocr_shells.py`（**必须用 ocr_venv 的 python 跑**）：

```bash
/opt/data/ocr_venv/bin/python3 re_ocr_shells.py --workers 4
```

- 多进程并行（`ProcessPoolExecutor`，8 核 i3-N305 用 4 workers，每个 ~50% CPU）
- 逐页：`fitz` dpi=150 渲染 PNG → RapidOCR 识别 → 文本拼装（带 `[第 N/总 页]` 分隔）
- **断点续跑**：完成记录写入 `/tmp/re_ocr_done.json`，重跑跳过已处理文件
- 结果写回 concepts/*.md，覆盖空壳；输出 `[N/M] OK/FAIL/SKIP 文件名 | 页数 | md大小 | 耗时`
- 参数：`--only 关键词`（单文件测试）、`--limit N`、`--workers N`

## 踩坑

- **csv 行解包**：scan_pdfs 输出的行有 6 列，`process_one` 要 `item[0]/item[1]/item[2]` 取前 3 列，不能直接解包成 3 个变量
- **RapidOCR 首次加载慢**：模型加载 10-20s，单页 43-67s（dpi 100 和 150 速度几乎一样，瓶颈在 CPU 推理不在图片大小），dpi 150 质量更好，不用降
- **多进程 + RapidOCR**：每个 worker 独立加载模型，不要共享实例
- **pymupdf EmptyFileError**：零字节 PDF 直接 `fitz.open()` 会崩，检查 `os.path.getsize() > 0`
- **临时 PNG 清理**：每页渲染到 `/tmp/ocr_p{i}_{pid}.png`，处理完删掉，防 /tmp 堆积

## 修复 ingest_docs.py（防再犯）

- 用 `_pdf_probe()` 结构探测（页数/文字量/图片页/文字页占比）替代 `len(text)<50`
- 判定规则：页数≥3 且文字<800、图片页占比>50%、大文件文字<2000 → 强制走 OCR

## 相关文件

- `/opt/data/re_ocr_shells.py` — 批量修复脚本（v2 本地 RapidOCR 版）
- `/opt/data/scan_pdfs.py` — 全库扫描
- `/opt/data/ocr_venv/` — RapidOCR + pymupdf venv
- `/opt/data/pdf_ocr.py` — 单文件 OCR 脚本（云端版，备用）
- `/opt/data/ingest_docs.py` — 入库脚本（已 patch `_pdf_probe`）

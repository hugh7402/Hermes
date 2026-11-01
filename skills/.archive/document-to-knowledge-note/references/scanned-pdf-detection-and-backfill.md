# 扫描件 PDF 判定与空壳回填（2026-08-01 事故复盘）

## 事故经过

用户发现《上海市数据局发布可信数据空间建设运营指南附全文下载.pdf》入库后只有 567 字。
排查：该 PDF 27 页中 20 页是纯扫描图片（无文字层），仅封面+结尾有 518 字符文字层。
旧 `ingest_docs.py` 逻辑 `len(text) < 50` 判定为"文字版"，跳过 OCR，正文全丢。

## 根因

MarkItDown 对"图文混合 PDF"提取出的文字 = 封面/通知/结尾的少量文字层，不反映正文。
只看总文字量无法区分"真文字版"与"扫描件+少量文字层"。

## 修复后的判定逻辑（已合入 /opt/data/ingest_docs.py）

```python
def _needs_ocr(filepath, markitdown_text):
    size = os.path.getsize(filepath)
    if not markitdown_text or len(markitdown_text) < 50:
        return True
    if size >= 32 * 1024 * 1024 and len(markitdown_text) < 2000:
        return True
    probe = _pdf_probe(filepath)  # (pages, total_text, img_pages, text_pages)
    if not probe:
        return False
    pages, total, img_pages, text_pages = probe
    if pages >= 3 and total < 800:
        return True
    if img_pages > 0 and pages >= 2 and text_pages / pages < 0.5:
        return True
    return False
```

`_pdf_probe` 通过 `uv run --with pymupdf python3 -c '...'` 子进程调用（主进程无 fitz），
返回 `[pages, total_text_chars, img_pages, text_pages]`。

## 全库体检脚本 /opt/data/scan_pdfs.py

```bash
cd /opt/data && uv run --with pymupdf python3 scan_pdfs.py
```

- 遍历 `WebChat BackUp/文档/**/*.pdf`（472 个）
- 输出 `/tmp/pdf_scan_report.csv`：file, pages, text_chars, text_pages, img_pages, flag
- flag: SUSPECT（可能丢正文）/ EMPTY（几乎无文字）/ ERR
- 判定：`pages>=3 and (total<800 or (img_pages>0 and text_pages/pages<0.5))`

## 空壳识别（相对阈值，2026-08-01 修正）

已入库笔记与扫描 PDF 对应关系判定——**不能只看绝对大小**：
- 空壳 = `md < 3000B` **或** `md < pages * 150`（每页不足 150B 即空壳）
- 反例：62 页的《Token驱动智能经济研究报告》md 有 3.8KB，但每页仅 ~61B → 仍是空壳
- 实测按此修正后空壳数从 252 升到 264

```bash
# 全部 <2KB 的 md（疑似空壳）
cd "/opt/data/Obsidian Vault/Obsidian Vault/concepts" && for f in *.md; do
  sz=$(stat -c %s "$f"); if [ $sz -lt 2000 ]; then echo "$sz $f"; fi; done | sort -n
```

实测：910 个 md 中 304 个 <2KB，其中 252 个与扫描 PDF 对应 = 需要回填（相对阈值修正后 264）。

## 回填流程（v2 — 本地 RapidOCR）

1. 从 `/tmp/pdf_scan_report.csv` 取 SUSPECT 且判定为空壳的文件列表
2. 用 **v2 批量脚本**（本地 RapidOCR，不用 API）：

```bash
cd /opt/data && /opt/data/ocr_venv/bin/python3 re_ocr_shells.py --workers 4
```

- **必须用 `/opt/data/ocr_venv/bin/python3`**（RapidOCR + pymupdf 装在该 venv；`uv run --with pymupdf` 跑的是另一个 Python，找不到 rapidocr_onnxruntime）
- `--workers N` 并行（i3-N305 8 核实测 4 最优）；`--only "关键词"` 单文档；`--limit N` 限量
- 断点续跑：`/tmp/re_ocr_done.json` 记录已完成，中断重跑自动跳过
- 单页 43-67s（dpi=150）；降 dpi 到 100 提速不明显（瓶颈在模型推理）
4. 字数验证 md 是否达到相对阈值

## OCR API 注意（SiliconFlow，仅降级用）

- `pdf_ocr.py` 用 dpi=200 渲染页面 PNG → base64 → PaddleOCR-VL-1.5
- 若 API 连续 read timeout（200KB 图 90s+ 无响应）：先测 `https://api.siliconflow.cn/v1/models` 是否 200；
  模型端点故障时降 dpi 到 100 测试小图，仍超时说明服务端问题，等恢复再跑，不要死等
- 每批 OCR_BATCH_SIZE=20 页，防止单请求超时
- **2026-08-01 实测：约 60% 请求 read timeout，逐页重试 3 次会卡 3-6 分钟/页，批量不可用——本地 RapidOCR 是默认引擎**

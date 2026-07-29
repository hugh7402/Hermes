# 扫描件 PDF 大批量入库

当 `WebChat BackUp/文档/` 下新增大量扫描件 PDF 集合时（如 318 文件中 78% 为扫描件），
逐个 OCR 极慢，需要专门的分批策略。

## 典型场景

用户将外部资料合集放入 `WebChat BackUp/文档/数据资产文件合集/`，
内有 16 个子文件夹、314 个 PDF + 4 个 DOCX，
扫描件占比约 78%（pymupdf 提取文字 < 50 字符）。

## 分批策略

### 1. 快速分类

先用 pymupdf 扫描前 50 个文件判断文本型 vs 扫描件比例：

```python
import fitz
doc = fitz.open(filepath)
text = ''.join(page.get_text() for page in doc)
if len(text.strip()) < 50:
    # 扫描件，需要 OCR
else:
    # 文本型，30s 内搞定
```

### 2. 专用批处理脚本

不要用通用 `ingest_docs.py`（它也是逐个处理，但有 MAX_PER_RUN=20 限制且与其他来源共用）。

专用脚本 `scripts/batch_ingest_assets.py` 的设计：

| 参数 | 值 | 理由 |
|------|-----|------|
| PER_RUN | 5 | 扫描件慢，5 个一批刚好 |
| TIMEOUT_PER_FILE | 600s | 大 PDF 页数无上限，10 分钟够处理 500+ 页 |
| OCR 引擎 | pdf_ocr.py (PaddleOCR-VL-1.5) | 约 0.8s/页 |
| 去重 | `.ingested` MD5 hash | 与主入库管道共用同一个去重文件 |
| 跳过策略 | OCR/提取失败也写 hash | 防止下次反复试同一个坏文件 |

### 3. Cron 调度

```bash
# 每天 4 次，每次 5 个 = 20 个/天
# 配合每天 9:00 的通用文档入库（20 个/天）
# 合计 40 个/天 → 318 文件约 8 天清完
```

cron 创建参数：`no_agent=True`（脚本自包含，无需 LLM）。

### 4. 处理中的坑

- **OCR 失败的文件**：PaddleOCR 对纯图片格式/手写体可能失败，直接跳过写 hash
- **超时文件**：600s 内跑不完的 OCR → `subprocess.TimeoutExpired` → 跳过写 hash（防反复试）
- **文件名特殊字符**：中文书名号 `《》`、括号 `【】`、空格 → 不能走 shell glob 展开，必须用 `Path.glob()` 或 `subprocess.run([...] + batch)`
- **页数无上限**：`MAX_OCR_PAGES = 99999` 已取消页数限制，完整入库
- **note_enhance 衔接**：每篇入库后自动调用 `note_enhance.py` 生成摘要+标签+关联

## 脚本位置

`/opt/data/scripts/batch_ingest_assets.py`
（同时复制到 `~/.hermes/scripts/batch_ingest_assets.py` 供 cron 使用）

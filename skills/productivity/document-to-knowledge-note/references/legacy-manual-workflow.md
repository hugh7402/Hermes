# Legacy Manual Document-to-Obsidian Workflow

> **Archived from `document-to-obsidian` skill (2026-06-18).**  
> The automated pipeline in `document-to-knowledge-note` (`ingest_docs.py` + cron) supersedes this manual flow.  
> Preserved for reference — use when the automated pipeline is unavailable or for one-off manual conversions.

## 文件类型 → 提取工具

| 格式 | 工具 | 安装命令 |
|------|------|----------|
| `.docx` | `python-docx` | `uv run --with python-docx` |
| `.pdf` | `pymupdf` | `uv run --with pymupdf` |
| `.pptx` | `markitdown[pptx]` | `uv run --with "markitdown[pptx]" python3 -m markitdown` |
| `.xls` | `xlrd` | `uv run --with xlrd` |

## 提取流程

### 1. 读取文件

**DOCX**: 提取段落 + 表格，表格用 Markdown table 呈现。
```bash
uv run --with python-docx python3 -c "
from docx import Document
doc = Document('文件路径')
for p in doc.paragraphs:
    if p.text.strip(): print(p.text)
for i, t in enumerate(doc.tables):
    for r in t.rows:
        print(' | '.join(c.text.strip() for c in r.cells))
"
```

**PDF**: pymupdf 逐页提取文本。
```bash
uv run --with pymupdf python3 -c "
import pymupdf
doc = pymupdf.open('文件路径')
for i, page in enumerate(doc):
    text = page.get_text()
    if text.strip():
        print(f'\n--- PAGE {i+1} ---')
        print(text[:4000])
"
```

**PPTX**: markitdown 直接转 Markdown（含 slide 编号和备注）。
```bash
uv run --with "markitdown[pptx]" python3 -m markitdown "文件路径"
```

**XLS**: xlrd 逐 sheet 逐行读取。
```bash
uv run --with xlrd python3 -c "
import xlrd
wb = xlrd.open_workbook('文件路径')
for name in wb.sheet_names():
    sh = wb.sheet_by_name(name)
    for r in range(min(sh.nrows, 120)):
        vals = [str(sh.cell_value(r, c)) for c in range(sh.ncols)]
        print(' | '.join(vals))
"
```

### 2. 结构化 Markdown

提炼原则：
- **精简**：去掉冗余措辞，保留关键信息（数据、结论、问题、风险）
- **结构化**：用表格呈现对比/清单类信息，用列表呈现层级关系
- **元数据**：顶部加 YAML frontmatter 风格的引用块（来源、日期、关联笔记）
- **关联**：用 `[[笔记名]]` 建立 Obsidian wikilink

模板结构：
```markdown
# 标题

> **来源**：xxx | 日期 | 版本
> **关联**：[[相关笔记]]

---

## 一级章节

### 二级章节

| 列1 | 列2 |
|-----|-----|
| ... | ... |

---
```

### 3. 写入 Obsidian

Obsidian Vault 路径：`/opt/data/Obsidian Vault/Obsidian Vault/`

## 陷阱

1. **execute_code 阻塞**：改用 `terminal()` 直接执行，或将脚本先 `write_file` 到 `/tmp/`。
2. **中文文件名**：脚本内用 glob 或绝对路径字符串避免转义问题。
3. **Obsidian 权限**：Vault 目录可能属主为 root。先 `chmod -R 777` 尝试修复。
4. **XLS vs XLSX**：`.xls` 用 xlrd，`.xlsx` 用 openpyxl。

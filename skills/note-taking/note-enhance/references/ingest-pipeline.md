# 文档自动入库流水线

## 概述

从 `WebChat BackUp/文档/` 自动扫描、转换、增强、入库的完整流水线。

## 脚本

- **入口**：`/opt/data/ingest_docs.py` — 主控脚本
- **增强**：`/opt/data/note_enhance.py` — 生成 YAML frontmatter
- **去重**：`/opt/data/Obsidian Vault/Obsidian Vault/.ingested` — MD5 已处理记录

## 流水线步骤

```
WebChat BackUp/文档/
  │
  ├── .docx → python-docx 提取段落+表格
  ├── .pdf  → pymupdf 提取文本
  ├── .pptx → python-pptx 提取幻灯片文本
  ├── .xls  → openpyxl (fallback: xlrd) 提取工作表
  │
  ▼
concepts/<文件名>.md
  │  - 自动添加 # 标题（若无）
  │  - 添加 > **原始文件**：元数据行
  │
  ▼
note_enhance.py 增强
  │  - 摘要：5条 × 分隔
  │  - 标签：10个关键词
  │  - 关联：[[wikilink]] 双向链接
  │
  ▼
Vault 就绪 ✅
```

## 支持格式

| 格式 | Python 库 | 备注 |
|------|-----------|------|
| `.docx` | python-docx | 段落+表格结构 |
| `.pdf` | pymupdf | 文本 PDF |
| `.pptx` | python-pptx | 幻灯片文本 |
| `.xlsx` | openpyxl | 新版 Excel |
| `.xls` | xlrd | 旧版 Excel（openpyxl 失败时 fallback） |

## 去重机制

使用 MD5 哈希记录已处理文件，存入 `.ingested` 文件。相同内容不会重复入库。

如需重新处理：删除 `.ingested` 文件。

**陷阱**：子目录中的文件首次入库没问题，但初次跑脚本时若 `glob('*')`（非递归），子目录文件不被处理，它们的 MD5 也不会被记录。后续改为 `glob('**/*')` 后，子目录文件才被扫描到。

## 子目录扫描

`ingest_docs.py` 使用 `Path.glob('**/*')` 递归扫描所有子目录。用户常按项目组织子目录（如 `01_联通材料/`、`陕西民政/`、`消防十五五规划/`、`协同创新仿真实验平台_北京数据局/`）。

⚠️ 曾用 `glob('*')` 只扫顶层，导致子目录中的大量文档被忽略。已修复为 `**/*`。

## 空内容文件处理

某些 docx/xlsx/pptx 文件内容全为空（占位模板、截图表无文本等），但文件体积 >0、MD5 恒变。每次跑都会出现在"待处理"列表中，但 `convert_to_markdown()` 返回空字符串，脚本跳过不标记已处理 → **死循环**。

**处理方式**：手动计算 MD5 写入 `.ingested` 文件跳过：
```python
h = hashlib.md5(Path(filepath).read_bytes()).hexdigest()
with open('.ingested', 'a') as f:
    f.write(f'{h}\n')
```

## Cron 配置

- **Job ID**：`c3e92b82c93a`
- **调度**：每日 9:00（`0 9 * * *`）
- **Toolsets**：`terminal`, `file`
- **模式**：`agent`（2026-06-22 从 `no_agent` 改为 `agent`，避免调度器 120s 硬超时）
- **脚本路径**：`/opt/data/scripts/ingest_docs.py`（cron 的副本，与主脚本同步）

**Cron 超时**：cron `no_agent` 模式有 120s 硬超时限制。`ingest_docs.py` 内部调用 `note_enhance.py`（subprocess timeout=300s）和大 PDF OCR（timeout=400s）。若待处理文件多（20+），单次 cron run 会超时失败。**解决方案**：改用 `agent` 模式，不受调度器超时限制。

## 标题处理规则

转换后的文本如果没有 `# 一级标题`，脚本会自动添加（从文件名推断）。
已有 H1 的文档，在标题后插入原始文件元数据。

## 去重合并规则

同一主题多版本时：

1. 比较正文长度，保留明显更完整的（1.5x 以上）
2. 正文量接近时，保留正文多的，合入另一版的 `related` 链接
3. 新版本用更干净的标题
4. **关键**：先写临时路径再 rename，避免输出=源文件导致数据丢失

# ingest_docs.py: 文档自动入库坑点和维护

## cron 模式选择

该 cron 任务已从 `no_agent` 模式改为 **Agent 模式**（2026-06-21）。

原因：no_agent 模式的 120s 硬超时导致 OCR 大 PDF（83 页培训照片）稳定超时。Agent 模式用 terminal 工具调用脚本，脚本内部 300s/400s subprocess timeout 生效。

Agent 模式的缺点：消耗少数 token（deepseek-chat ≈ ¥0.0005/次），可忽略。

## 文件去重机制

脚本用 MD5 hash 去重，标记文件保存在 Obsidian vault 根目录的 `.ingested` 文件。

```python
PROCESSED_LOG = f"{VAULT}/.ingested"  # 实际路径
```

每个已处理文件的 MD5 hash 一行追加到 `.ingested`。下次扫描时对比 hash 跳过已处理的。

### 排查步骤

1. 计算文件 hash: `python3 -c "import hashlib; print(hashlib.md5(open('path/to/file','rb').read()).hexdigest())"`
2. 查 `.ingested`: `grep <hash> /opt/data/Obsidian\ Vault/Obsidian\ Vault/.ingested`
3. 若不在，且文件内容为空（转换 0 产出），手动标记：`echo <hash> >> /opt/data/Obsidian\ Vault/Obsidian\ Vault/.ingested`

## MAX_PER_RUN 临时调整

当需要短时间内处理大量堆积文件（如 30+ 新文件），可临时调低 `MAX_PER_RUN` 避免单次超时：

```bash
sed -i 's/MAX_PER_RUN = 20/MAX_PER_RUN = 5/' /opt/data/ingest_docs.py
# 跑几轮...
# 处理完后恢复：
sed -i 's/MAX_PER_RUN = 5/MAX_PER_RUN = 20/' /opt/data/ingest_docs.py
```

恢复后再次运行确认 `📭 无新文档`。

## 单个文档强制重入库（跳过 MD5 去重）

用户要求"重新处理某文档入库"时（如《陕西智慧民政一体化平台月度报告2026年7月》），直接跑 `ingest_docs.py` 无效——MD5 去重会跳过已处理文件。**手动单文档入库流程**：

1. 先确认源 PDF 是否文字层完整（决定走不走 OCR）：
   ```python
   # pymupdf 探测：pages/text_chars/img_pages/text_pages
   # 文字页占比高、图片页极少 → MarkItDown 结果直接可用，无需 OCR
   ```
   （《陕西智慧民政月度报告》：27页、13668字、27/27文字页、仅1图片页 → 不需要 OCR）
2. MarkItDown 转换 → 提取标题 → 写 `concepts/<名>.md`（含原始文件 + 转换时间 frontmatter）
3. `hashlib.md5(源文件.read_bytes()).hexdigest()` 追加到 `.ingested` 标记已处理
4. 标题提取注意：表格开头（`| （2026 年 7 月）|`）会被误当标题——正文行优先，或 `len>60` 时用人工标题

⚠️ 不要在一个 `timeout` 终端命令里串 MarkItDown+写文件——转换本身可能就吃掉超时。拆成独立脚本文件（写 `/opt/data/` 下）再执行。


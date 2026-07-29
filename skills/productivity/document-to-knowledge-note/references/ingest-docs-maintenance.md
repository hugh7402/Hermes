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

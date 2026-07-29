# 思源笔记集成

详见独立技能 `siyuan-integration`（`note-taking/siyuan-integration`）。

## 快速摘要

- **数据源**：`/opt/data/INBOX_FILES/workspace/data/`（思源 .sy JSON 格式）
- **主脚本**：`/opt/data/siyuan_sync.py`（提取 + 增强 + 入库）
- **目标目录**：`VAULT/00-INBOX/`（不与 concepts 混合）
- **Cron**：`5652f5032fe5`，每天 17:00，`no_agent` 模式
- **文件名**：思源 doc_id（英文数字），中文标题在 YAML `title`
- **帮助文档**：直接跳过，不提取不归档
- **增强方式**：先 copy 到 concepts 临时目录（note_enhance 路径限制），增强后搬回 00-INBOX

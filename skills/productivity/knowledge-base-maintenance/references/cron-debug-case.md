# Cron Broken Pipe 排查案例

## 故障现象

Cron job `c3e92b82c93a` "每日文档自动入库" 执行失败，error。

## 排查路径

1. **定位会话**：`session_search` 找到 cron 会话，只有 1 条消息（技能加载），无 agent 响应
2. **查日志**：`/opt/data/logs/errors.log` 关键行：
   ```
   Stream stale for 180s — no chunks received.
   model=deepseek-v4-pro context=~10,313 tokens
   [Errno 32] Broken pipe
   ```
3. **根因**：上下文 ~10,313 tokens（note-enhance + llm-wiki 两个技能），DeepSeek v4 Pro 
   180 秒内未生成任何 token → 流超时断开。3 次重试全部同样超时。

## 修复

切换为 `no_agent: true` 模式，脚本直跑不经过 LLM。

## 踩坑

- **符号链接**：`ln -sf` 创建的链接在 cron 沙箱中解析到 `/opt/data/ingest_docs.py`，超出 `/opt/data/scripts/` 范围被拦截
- **cp 报 same file**：因符号链接指向自身，需先 `unlink` 再 `cp` 真实文件

## 最终效果

| 指标 | 修复前 | 修复后 |
|------|--------|--------|
| 耗时 | ~10 分钟超时 | 55 秒 |
| Token | ~10k × 3 | 0 |
| 状态 | ❌ error | ✅ ok |
| 月费用 | ~¥0.30 | ¥0 |

## 通用教训

- 简单脚本任务优先用 `no_agent` 模式，零 LLM 开销
- cron 脚本放 `/opt/data/scripts/`，用真实文件不用符号链接
- Python 依赖缺失时用 shell 包装 + `uv run --with`
- `session_search` + `errors.log` 是排查 cron 故障的首选入口

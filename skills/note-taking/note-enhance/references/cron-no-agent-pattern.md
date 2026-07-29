# Cron no_agent 模式：Agent 上下文溢出超时

## 问题症状

cron 作业状态 `error`，错误信息：`RuntimeError: [Errno 32] Broken pipe`

日志特征：
```
Stream stale for 180s — no chunks received. model=deepseek-v4-pro context=~10,313 tokens
API call failed after 3 retries. [Errno 32] Broken pipe
```

## 根因

Agent 模式 cron 加载多个技能（如 `note-enhance` + `llm-wiki`），总上下文膨胀到 ~10k+ tokens。DeepSeek v4 Pro（以及类似模型）在收到大上下文后长时间无响应，超过 180s 流超时阈值后断开连接，每次重试同样超时（3 次 × 180s = 9 分钟浪费）。

## 修复

改用 `no_agent` 模式，跳过 LLM，由调度器直接执行脚本：

```bash
hermes cron edit <job_id>
# 设置：no_agent=true, script=ingest_docs.py
```

## 部署注意事项

1. 脚本必须放在 `~/.hermes/scripts/` 或 `$HERMES_HOME/scripts/` 下，且为**真实文件**（非符号链接）
2. 符号链接会被沙箱拦截：`Blocked: script path resolves outside the scripts directory`
3. 解决：先 `unlink` 符号链接，再 `cp` 真实文件副本

## 判断标准

什么时候该用 no_agent：
- ✅ 自包含脚本，不需要 LLM 推理
- ✅ Cron 任务有明确输入输出
- ✅ 脚本已有错误处理

什么时候该用 Agent：
- ✅ 需要理解和处理多样化的输入
- ✅ 需要决策判断
- ✅ 输出格式不固定

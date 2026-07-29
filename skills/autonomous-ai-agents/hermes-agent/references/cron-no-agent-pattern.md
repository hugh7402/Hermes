# Cron no_agent 模式：从 Broken Pipe 到零 Token

## 问题场景

Cron 作业加载大型技能（如 llm-wiki, note-enhance）后，LLM 上下文膨胀到 ~10,000+ tokens，导致 DeepSeek API 超时（180s 无响应 → Broken pipe），重试 3 次全部失败。

## 根因

DeepSeek v4 Pro 处理大上下文（~10k tokens）时，在 180s 内无法生成第一个 token。技能内容越丰富，模型越难启动。

## 解决方案：no_agent 模式

将 Cron 从 `Agent + 技能` 模式改为 `no_agent + 脚本` 模式：

```
之前: Agent 加载 note-enhance + llm-wiki → LLM 理解规则 → 手动执行
之后: no_agent, script=ingest_docs.py → 调度器直跑脚本
```

### 关键步骤

1. 脚本必须放在 `$HERMES_HOME/scripts/` 或 `~/.hermes/scripts/` 下
2. **不能使用符号链接** — 调度器会解析真实路径并检查是否在 scripts 目录内，符号链接指向外部路径会被拦截
3. 必须复制真实文件副本（`unlink` 旧链接 → `cp` 真实文件）
4. Shell 包装脚本（.sh）适用于需要特定环境的 Python 脚本（如 `uv run --with pkg`）

### 效果对比

| 维度 | Agent 模式 | no_agent |
|------|-----------|----------|
| 耗时 | ~10 分钟超时 | 55 秒 |
| Token | ~10k × 3 重试 | 0 |
| 成本 | ~¥0.30 | ¥0 |
| 可靠性 | 偶尔超时 | 100% |

## 适用判断

**用 no_agent 当：**
- 任务是跑一个自包含脚本（如文档转换、巡检、数据抓取）
- 脚本已包含所有业务逻辑，且脚本能在 120s 内完成
- LLM 不需要做推理/决策

**用 Agent 当：**
- 任务需要判断、推理、多步决策
- 输出需要自然语言生成
- 需要工具调用组合
- 脚本可能运行超过 120s（如大规模 OCR、PDF 转换）

## 重要限制：no_agent 的 120s 硬超时

no_agent 模式由调度器直接管理脚本进程，脚本超时时间为 **120s（硬限制，不可配置）**。如果脚本可能超过这个时间（例如 OCR 大 PDF、批量转换几十个文件），no_agent 会稳定超时失败。

### 解决方案：因需选模式

| 条件 | 推荐模式 |
|------|---------|
| 脚本 ≤ 120s 能跑完 | **no_agent**（零 Token，最稳定） |
| 脚本 > 120s（OCR/批量转换） | **Agent 模式**（脚本写循环，由 Agent 用 terminal 工具调用，不受 120s 限制） |
| 需要 LLM 判断/汇总 | **Agent 模式** |

### Agent 模式迁移步骤

将 cron 任务从 no_agent 改为 agent 模式（不需要脚本路径）：

```bash
# 原来（no_agent）：
cronjob create --script 'ingest_docs.py' --no_agent true

# 改为（agent 模式）：
cronjob create --prompt '运行 cd /opt/data && python3 ingest_docs.py，处理后汇总结果' --no_agent false
```

关键变化：
1. 移除 `script` 参数，改为 `prompt` 指令
2. Agent 用 `terminal` 工具调用脚本，timeout 取决于 Agent 模型响应速度而非脚本调度器的 120s
3. 脚本内部的 subprocess timeout（300s/400s）生效，不会再被上层调度器截断
4. 脚本多次循环调用也由 Agent 自行管理，不受调度器单次限制

注意：Agent 模式会消耗 Token，但 cost 可忽略（deepseek-chat 约 ¥0.0005/次调用），远优于脚本超时失败的代价。

## 实例

```bash
# Cron 创建
cronjob create \
  --name "每日文档自动入库" \
  --schedule "0 9 * * *" \
  --script "ingest_docs.py" \
  --no_agent true \
  --deliver origin
```

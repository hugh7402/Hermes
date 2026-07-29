---
name: weixin-gateway-troubleshooting
description: >-
  微信 iLink gateway 问题排查：限流、连接断开、session过期、投递失败。
  含 config.yaml 配置、限流参数调优、cron 投递错峰策略。
version: 1.0.0
author: Emma
---

# 微信 iLink Gateway 问题排查

## 限流问题（最常见）

### 现象
cron 投递失败，日志报：
```
iLink sendmessage rate limited; cooldown active for 30.0s
delivery error: Weixin send failed: iLink sendmessage rate limited
```

### 根因
- weixin.py 默认限流参数太敏感：`THRESHOLD=1, WINDOW=30s, OPEN=30s`
- 多个 cron 在相近时段发消息（如8:30、15:30、19:30），冷却一直不消退

### 关键：gateway 不读 .env

**重要：** gateway 由 s6 管理，启动脚本用 `with-contenv`，**只从 `/run/s6/container_environment/` 读环境变量**，不从 `/opt/data/.env` 读。

往 `.env` 加 `WEIXIN_RATE_LIMIT_CIRCUIT_THRESHOLD=3` **不会生效**。

### 正确修复

weixin.py 代码从两个来源读参数（优先级：config.extra > os.getenv）：

```python
extra.get("rate_limit_circuit_threshold") or os.getenv("WEIXIN_RATE_LIMIT_CIRCUIT_THRESHOLD", "1")
extra.get("rate_limit_circuit_window_seconds") or os.getenv("WEIXIN_RATE_LIMIT_CIRCUIT_WINDOW_SECONDS", "30.0")
extra.get("rate_limit_circuit_open_seconds") or os.getenv("WEIXIN_RATE_LIMIT_CIRCUIT_OPEN_SECONDS", "30.0")
```

需要在 `config.yaml` 的 `weixin.extra` 段写入。

### 操作步骤

编辑 `/opt/data/config.yaml`，在 `telegram:` 前面插入：

```yaml
weixin:
  extra:
    rate_limit_circuit_threshold: 3        # 原来=1
    rate_limit_circuit_window_seconds: 60  # 原来=30
    rate_limit_circuit_open_seconds: 15    # 原来=30
    send_chunk_retries: 10
    send_chunk_retry_delay_seconds: 3.0
    send_chunk_delay_seconds: 3.0
```

### 让配置生效

修改 config.yaml 后 gateway 需重启。在容器内（非 root）较难杀进程，可尝试：

- `s6-svc -t /run/service/gateway-default`（需要 s6-svc 在 PATH 中）
- 或在 Docker host 上执行容器 restart

### 坑：.env 中带 export 前缀不会生效

`.env` 中用 `export KEY=VALUE` 格式写入时，python-dotenv 会把 `export ` 作为变量名的一部分，导致 os.getenv 读到的是空的。必须用纯 `KEY=VALUE` 格式。

### 方案B：关闭重试避免加剧限流

如果腾讯 iLink 服务端限流严格，调大阈值也无法缓解，可以彻底关闭 chunk 重试（默认 4 次），限流后直接放弃，不反复重试加剧冷却：

```yaml
weixin:
  extra:
    send_chunk_retries: 0        # 0 = 不重试，限流即放弃
```

### 验证

修改 config.yaml 后检查 gateway 日志：
```bash
grep "rate limited\|send failed\|cooldown" /opt/data/logs/gateway.log | tail -10
```

## Session 过期问题

### 现象
```
[Weixin] Session expired; pausing for 10 minutes
```

### 修复
- `hermes gateway setup`（需 PTY 模式）→ Weixin → Reconfigure → 扫码
- 或删除旧 token 重新配置

## 文件投递（send_message 不可用）

Agent 会话内没有 `send_message` 工具（Hermes 设计上 agent 不能主动发消息）。投递文件使用 cron 一次性任务：

```
cronjob(action="create", name="发文件",
  prompt="将文件 /path/to/file 投递到当前用户。",
  schedule="1m")
```

## cron 投递错峰策略

当前 cron 分布：

| 任务 | 时间 | 建议 |
|:----|:---:|:----|
| 每日文档自动入库 | 08:30 | ✅ 可 |
| 思源笔记同步入库 | **19:30** | ← 移到 19:00 |
| 每日核心股分析报告 | **15:30** | ← 移到 15:00 |
| 知识库月度健康巡检 | 每月1日 09:00 | ✅ 可 |

多个 cron 时间避开同一分钟，至少间隔 15 分钟。

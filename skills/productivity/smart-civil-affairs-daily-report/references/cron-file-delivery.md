# Cron 递送 Word 文件到微信

当需要在微信中发送 Word 文档但 agent 会话内没有 `send_message` 工具时，
使用一次性 cron 作业作为递送通道。

## 何时使用

- 日报/周报生成后需要把 .docx 文件发给用户
- 任何需要在微信上收到文件附件的场景

## 标准步骤

1. 首先生成文件到确知路径
2. 正常回复用户告知文件已生成 + 摘要
3. 创建一次性 cron 投递作业：

```python
cronjob(
    action="create",
    name="发送[文件名]到微信",
    prompt=f"将文件 {path} 投递到当前用户。文件已存在，大小{N}KB。直接发送即可。",
    schedule="1m"   # 最小间隔 1 分钟
)
```

## 注意事项

- `schedule="1m"` 是最小值，实际会有约 1 分钟延迟
- cron 作业的 `deliver` 默认是 `origin`（投递回当前对话）
- 文件生成和 cron 投递是两步，不要等 cron 执行完再回复用户
- 可以在 cron 运行时先回复文本摘要给用户

## ⚠️ 微信限流

微信 iLink 桥接经常限流（`iLink sendmessage rate limited; cooldown active for 30.0s`）。
这是 iLink 的频率限制，而非文件投递逻辑问题。

**症状**：cron 投递显示 `last_delivery_error` 但作业已执行，微信上收不到文件。

**应对**：
1. 生成文件后**先回复用户摘要 + 文件路径**，确保用户有备用获取方式
2. cron 投递作为"额外尝试"，不依赖它作为唯一交付通道
3. 多 cron 可能扎堆触发限流，可考虑错开不同 cron 的执行时间

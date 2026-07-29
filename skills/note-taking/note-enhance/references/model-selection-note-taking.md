# 笔记辅助 AI 模型选型

思源笔记 AI 辅助场景（摘要、标签、改写、关联发现）的模型对比实测。

## 测试方法

同一 prompt（笔记摘要任务），分别调用各平台/模型，记录延迟和输出质量。

## 实测结果 (2026-06-18)

| 平台 | 模型 | 延迟 | 输出 tokens | 评价 |
|------|------|:---:|:---:|------|
| DeepSeek 官方 | `deepseek-chat` | 1.31s | 48 | ⚡ 精准简洁 |
| DeepSeek 官方 | `deepseek-v4-flash` | 2.89s | 200 | 空响应 ❓ |
| 百炼 | `deepseek-v4-flash` | 4.34s | 398 | 啰嗦冗余 |

## 最终推荐

### 日常主力：DeepSeek 官方 `deepseek-chat`

```
API 地址：https://api.deepseek.com/v1
模型 ID：deepseek-chat
价格：   ¥1/M 入，¥2/M 出（¥0.3/月，每天50次）
```

选择理由：
- **速度**：1.3s vs 4.3s（百炼 v4-flash），笔记场景对延迟敏感
- **简洁**：48 tokens vs 398 tokens，输出精准不啰嗦
- **成本**：输出 tokens 少 8 倍，费用相应降低
- **稳定**：DeepSeek 官方直连，不经过托管转发

### 深度分析：百炼 `qwq-plus`

```
API 地址：https://dashscope.aliyuncs.com/compatible-mode/v1
模型 ID：qwq-plus
价格：   ¥1.6/M 入，¥4/M 出
场景：   长文深度分析、复杂知识关联发现
```

### 轻量备用：百炼 `qwen-plus`

```
模型 ID：qwen-plus
价格：   ¥0.8/M 入，¥2/M 出
场景：   翻译、格式化、简单改写
```

## 百炼平台文本模型价格速查 (2026-06)

| 模型 | 输入 ¥/M | 输出 ¥/M | 思考模式 |
|------|:---:|:---:|:---:|
| qwen3.7-max | 12 | 36 | ✓ |
| qwen3.7-plus | 2 | 8 | ✓ |
| qwen3.6-flash | 1.2 | 7.2 | ✓ |
| qwen-max | 2.5 | 10 | ✓ |
| qwen-plus | 0.8 | 2 | ✓ |
| qwen-flash | 0.15 | 1.5 | ✓ |
| qwq-plus | 1.6 | 4 | 仅思考 |
| deepseek-v4-pro | 12 | 24 | ✓ |
| deepseek-v4-flash | 1 | 2 | ✗ |
| deepseek-v3.2 | 2 | 3 | ✓ |
| glm-5.2 | 8 | 28 | ✓ |
| kimi-k2.7-code | 6.5 | 27 | 仅思考 |

## 关键发现

- **v4 不一定比 v3 好**：笔记摘要场景，deepseek-chat (V3) 比 deepseek-v4-flash 快 3 倍、输出更简洁
- **百炼托管有延迟加成**：同模型，百炼比官方慢 1-2 秒（多一跳转发）
- **模型越大 ≠ 笔记场景越好**：大模型倾向长篇大论，小模型反而更干脆
- **思源配多模型**：主力用 deepseek-chat，深度分析切 qwq-plus，备用 qwen-plus

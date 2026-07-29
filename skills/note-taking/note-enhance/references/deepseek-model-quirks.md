# DeepSeek 模型使用技巧（百炼平台）

## 模型对比

| | deepseek-v4-pro | deepseek-v4-flash |
|------|------|------|
| **类型** | 推理模型（MoE+CoT） | 标准模型 |
| **内部思考** | ✅ 消耗大量输出 token | ❌ 无 |
| **适用场景** | 长文摘要、复杂推理 | 短输出（标签、分类） |
| **百炼定价** | 入¥2/百万tokens 出¥8/百万tokens | 入¥1/百万tokens 出¥2/百万tokens |

## 核心陷阱：v4-pro 空响应

**症状**：API 返回 HTTP 200，但 `choices[0].message.content` 为空字符串，`finish_reason: length`。

**根因**：v4-pro 是推理模型，先用输出 token 做内部 CoT 思考，再输出可见响应。`max_tokens` 设太低（如 200-500）时，所有 token 消耗在思考阶段，可见输出为空。

**解法**：`max_tokens` 至少设为 **1200**，摘要类任务可设到 1500-2000。

## 何时用哪个

| 任务 | 模型 | max_tokens |
|------|------|:--:|
| 摘要提炼（5条×分隔） | v4-pro | 1200 |
| 关键词标签（10个逗号分隔） | v4-flash | 200 |
| 关联发现（wikilink列表） | v4-flash | 200 |
| 长篇文档分析 | v4-pro | 2000 |

## 备选模型（百炼平台）

| 模型 | 用途 | 价格 |
|------|------|------|
| `qwen3.7-max` | 旗舰推理，可研/标书 | 入¥20/出¥60（10倍于 deepseek） |
| `qwen-vl-max` | 图像识别（替代被墙的 Gemini） | 按量 |
| `qwen-long` | 千万 token 上下文，全文分析 | 入¥20/出¥60 |

## 环境状态

- DeepSeek API Key：`.env` 中的 `DEEPSEEK_API_KEY`
- 百炼 API Key：`.env` 中的 `BAILIAN_API_KEY`（217 个可用模型）
- SiliconFlow Key：`.env` 中的 `SILICONFLOW_API_KEY`（Qwen3-VL-8B 视觉）
- Google API：已配置但 GFW 阻断，不可用

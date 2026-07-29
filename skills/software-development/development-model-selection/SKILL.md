---
name: development-model-selection
description: Use when developing skills/tools/agents and need to select a model for a subtask. Load llm-model-selection to choose, don't guess.
version: 1.0.0
tags: [开发, 模型选择, workflow]
trigger: 开发 skill/智能体/工具时，需要为子任务选模型时自动加载
requires-skills: [llm-model-selection]
---

# 开发中的模型选择规则

## 规则来源

用户 2026-07-29 明确要求：开发 skill 过程中需要选模型时，统一用 `llm-model-selection` skill，不凭记忆或偏好直接指定。

## 工作流

```
需要为子任务选模型
    │
    ├─ 是默认开发模型？ → 直接用（GLM-5.2 / DeepSeek-V4-Pro）
    │
    └─ 不是默认开发模型？ → 加载 llm-model-selection → 按评测结果选
```

## 何时触发

- 不确定子任务用哪个模型性价比最高
- 评估新 API/工具适合哪个模型
- 凭记忆想直接指定模型时 → **停，先走选择流程**
- 用户问"用哪个模型好"时

## 默认开发模型（不走选择流程）

| 角色 | 模型 |
|:---|:---|
| 🥇 主模型 | zai-org/GLM-5.2（硅基流动） |
| 🥈 备用 | deepseek-ai/DeepSeek-V4-Pro（硅基流动） |

只有**子任务特定模型选择**才需要走 `llm-model-selection`。

## 常见陷阱

1. **凭记忆选模型** — 模型性价比和评测结果会变化，永远先查 llm-model-selection
2. **把开发主模型和子任务模型混为一谈** — 开发本身用固定模型，子任务选模型才走选择流程

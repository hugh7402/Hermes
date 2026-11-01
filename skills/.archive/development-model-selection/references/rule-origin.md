# 模型选择规则由来

## 对话记录（2026-07-29）

用户说：「请记住，以后在开发skill过程中，筛选模型时，统一用llm-model-selection skill来选择模型」

这句话是在 skill 大清理之后说的——当时删了 44 个冗余 skill，保留了 excalidraw、llm-model-selection、report-generator 三个作为工具类 skill。

用户特意强调了「统一用」，说明这不是可选建议，是刚性规则。

## 为何单独成 skill

用户偏好已存 memory，但 skill 是更合适的载体——因为：
1. `agent-smart-development` 是手动创建的 skill，后台无法自动更新
2. 这个规则涉及跨 skill 协作（development + model-selection），适合独立成 skill
3. 需要 `requires-skills: [llm-model-selection]` 确保自动加载

## 关联 skill

- `agent-smart-development` — 智能体开发主流程 skill，内含默认开发模型配置
- `llm-model-selection` — 模型评测和选择工具，本 skill 的依赖

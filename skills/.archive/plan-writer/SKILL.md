---
name: plan-writer
description: "Use when user asks to write, draft, or design a formal plan/方案/报告/proposal. Retrieves knowledge base, uses SiliconFlow deepseek-v4-pro (2.5折), two-round architecture → full text, outputs to OutPut Box."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [plan, writing, government, policy, proposal]
    related_skills: [note-enhance, obsidian]
---

# 方案智能体 (Plan Writer)

## Overview

专门用于撰写政务信息化方案、报告、建议书。使用硅基流动 deepseek-ai/DeepSeek-V4-Pro（当前 2.5 折优惠，47s，技术准确度 8.0/10），采用两轮制（架构设计 → 全文一次生成），检索 Obsidian 知识库获取真实参考内容，输出到 OutPut Box 并微信推送。

## When to Use

- 用户要求撰写方案、报告、建议书、规划文档
- 用户说"帮我写一个XX方案""起草XX报告""设计XX架构"
- 需要结合知识库内容生成正式文档
- 触发词：方案、报告、建议书、规划、起草、撰写、设计

Don't use for:
- 简单的笔记记录
- 日常对话问答
- 代码编写

## Workflow

### 完整流程（两轮制，v2）

```
用户提需求
    ↓
1. 运行 python3 /opt/data/skills/productivity/plan-writer/scripts/write_plan.py "需求" "名称"
    ↓
2. 第1轮：检索知识库 → deepseek-v4-pro 设计架构（1次API调用）
3. 第2轮：架构+知识库 → deepseek-v4-pro 一次生成全文（1次API调用）
    ↓
4. 输出到 /opt/data/OutPut Box/ + 微信推送
    ↓
5. 询问用户是否需要修改
```

总计 **2 次 API 调用**，v1 的逐章撰写（27次调用）已废弃。

## 模型配置

- **模型**: deepseek-ai/DeepSeek-V4-Pro (硅基流动平台)
- **优势**: 技术准确度高(8.0/10)、内容质量满分(10/10)、当前2.5折优惠
- **API**: https://api.siliconflow.cn/v1/chat/completions
- **Key**: SILICONFLOW_API_KEY（.env 中）
- **⚠️ 注意**: 思考型模型需 max_tokens ≥ 8000 否则 content 为空

## 知识库检索

检索范围：
- `/opt/data/Obsidian Vault/Obsidian Vault/concepts/` — WebChat 文档（585篇）
- `/opt/data/Obsidian Vault/Obsidian Vault/00-INBOX/` — 思源笔记

检索逻辑：
- 从用户需求中提取关键词
- 对知识库所有 .md 文件做关键词匹配
- 按相关性排序，取 Top 10

## 输出规范

- 格式：Markdown，含 YAML frontmatter
- 文件名：`方案-YYYYMMDD-HHMM.md` 或用户指定
- 路径：`/opt/data/OutPut Box/`
- 风格：政府公文规范，正式专业
- 幻觉控制：无法确认的信息标注"[待确认]"

## 风格要求

方案的每一章撰写时，强制遵循以下风格：

1. **用语正式专业** — 使用"应""须""可"等规范用语
2. **结构清晰** — 先总述、再分述、最后小结
3. **数据有据** — 引用知识库中的真实数据，不编造
4. **术语统一** — 同一概念全文使用相同表述
5. **段落均衡** — 每段 3-5 句，避免过长或过短

## 常见方案模板

### 项目建设方案
```
一、项目背景与依据
二、需求分析
三、总体设计
四、技术方案
五、实施计划
六、保障措施
七、经费概算
```

### 工作汇报
```
一、工作进展
二、存在问题
三、下步计划
四、需要协调事项
```

## Common Pitfalls

1. **逐章撰写导致超时** — v1 架构解析出 27 章，每章一次 API 调用，总超 20 分钟。v2 改为两轮制（架构+全文），仅 2 次调用。
2. **不检索知识库** — 没有知识库支撑的方案是空壳，缺乏真实数据。
3. **模型选错** — 方案撰写禁用 qwen3.7-max/plus（输出<1000字）。当前选用硅基流动 deepseek-v4-pro（2.5折优惠，性价比最优）。备选 deepseek-chat（推理最强，76分）。
4. **deepseek-v4-pro 需大 max_tokens** — 该模型为思考型，推理消耗约 400 tokens，需设 max_tokens≥8000 否则 content 为空。
5. **OutPut Box 权限** — Docker 挂载目录可能 root 属主。写入前若 Permission denied，删除并重建目录即可（hermes 属主）。

## References

本次评测结果（2026-06-19 9模型单章节方案撰写）：

| 模型 | 延迟 | 推理 | 质量 | 幻觉 | 准确 | 总分 |
|------|------|:--:|:--:|:--:|:--:|:--:|
| deepseek-chat | 29.8s | 8 | 9 | 7 | 6.0 | **76** 🥇 |
| kimi-k2.7-code | 80.0s | 3 | 9 | **10** | **8.5** | 70 🥈 |
| deepseek-v4-flash | 21.9s | 5 | 10 | 4 | 7.0 | 64 🥉 |
| deepseek-v3.2 | 53.3s | 3 | 10 | 7 | 5.5 | 60 |
| deepseek-v4-pro | 47.2s | 2 | 10 | 4 | 8.0 | 56 |
| deepseek-reasoner | 36.8s | 1 | 10 | 4 | 6.5 | 50 |
| kimi-k2.6 | 27.0s | 1 | 10 | 4 | 6.5 | 50 |
| qwen3.7-max | 58.1s | 3 | 7 | 4 | 4.5 | 45 |
| glm-5.2 | 49.1s | 2 | 7 | 4 | 5.5 | 44 |

结论：
- deepseek-chat 推理最强、方案质量最高
- kimi-k2.7-code 零幻觉、技术栈最准确
- 但考虑性价比——硅基流动 deepseek-v4-pro 当前 2.5折，综合得分 56 且技术准确度高(8.0)，是成本最优选择
- 3.7 代模型（qwen3.7-max, glm-5.2）全面垫底
- `references/model-selection-matrix.md` — 三平台模型选型原则与生产矩阵

## Verification Checklist

- [ ] 方案含 YAML frontmatter（title, date, source）
- [ ] 输出到 `/opt/data/OutPut Box/`
- [ ] 至少检索了 3 篇以上知识库笔记
- [ ] 使用 deepseek-ai/DeepSeek-V4-Pro（硅基流动），非其他模型
- [ ] 采用两轮制（2次API调用），非逐章撰写
- [ ] 输出到 `/opt/data/OutPut Box/` + 微信推送
- [ ] 无法确认的信息标注"[待确认]"

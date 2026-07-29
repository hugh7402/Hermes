# Agent / Function-Calling Benchmark — 2026-06-19

## Context
User asked which model is best for Hermes Agent (an autonomous tool-calling agent).
Tested 4 models on OpenAI-style `tools` parameter to measure tool selection accuracy,
latency, cost, and reasoning token waste.

## Why This Matters
Hermes Agent is NOT a chatbot — it's a tool-calling agent. Every user message may
trigger multiple model calls (tool selection → tool execution → result interpretation
→ next action). Model requirements differ from chat:
- **Tool-calling accuracy** (selecting the right function with right args)
- **Low latency per call** (5 tool calls × 20s = 100s task — unacceptable)
- **Minimal reasoning overhead** (thinking tokens delay every tool decision)
- **64K+ context** (Hermes requirement per official docs)

## Setup
- 3 scenarios: simple tool call, multi-param tool call, tool selection judgment
- 2 tools defined: `search_vault(query, limit)`, `create_note(title, content)`
- `tool_choice: auto`, `temperature: 0.1`, `max_tokens: 4096`
- 4 models × 3 platforms

## Models Tested

| Label | Platform | Model | Pricing (¥/M in/out) |
|-------|----------|-------|:---:|
| glm5.2 | 智谱官方 | glm-5.2 | 0.5 / 0.5 |
| v4pro-ds | DeepSeek官方 | deepseek-v4-pro | 3.1 / 6.2 |
| ds-chat | DeepSeek官方 | deepseek-chat | 1.0 / 2.0 |
| qwen3.7max | 百炼 | qwen3.7-max | 2.0 / 6.0 |

## Results

| Model | Scenario | Latency | Tool Called | Correct? | Cost | Reasoning Tokens |
|-------|----------|:---:|:---:|:---:|:---:|:---:|
| glm5.2 | simple | 7.8s | search_vault | Y | ¥0.0002 | 33 |
| glm5.2 | multi-param | 6.0s | search_vault | Y | ¥0.0002 | 22 |
| glm5.2 | select | 14.7s | search_vault | **N** (should be create_note) | ¥0.0002 | 133 |
| v4pro-ds | simple | 1.5s | search_vault | Y | ¥0.0017 | 18 |
| v4pro-ds | multi-param | 1.5s | search_vault | Y | ¥0.0018 | 32 |
| v4pro-ds | select | 1.5s | search_vault | **N** (should be create_note) | ¥0.0018 | 28 |
| **ds-chat** | simple | 0.9s | search_vault | Y | ¥0.0005 | **0** |
| **ds-chat** | multi-param | 1.2s | search_vault | Y | ¥0.0005 | **0** |
| **ds-chat** | select | 1.3s | search_vault | **N** (should be create_note) | ¥0.0005 | **0** |
| qwen3.7max | simple | 2.7s | search_vault | Y | ¥0.0013 | 53 |
| qwen3.7max | multi-param | 2.1s | search_vault | Y | ¥0.0013 | 49 |
| qwen3.7max | select | 20.6s | **create_note** | **Y** ✅ | ¥0.0075 | 636 |

## Summary

| Model | Avg Latency | Tool Accuracy | Avg Cost | Avg Reasoning Tokens |
|-------|:---:|:---:|:---:|:---:|
| **ds-chat** | **1.1s** ✅ | 2/3 | **¥0.0005** ✅ | **0** ✅ |
| v4pro-ds | 1.5s | 2/3 | ¥0.0018 | 26 |
| qwen3.7max | 8.5s | **3/3** ✅ | ¥0.0034 | 246 ❌ |
| glm5.2 | 9.5s | 2/3 | ¥0.0002 | 63 |

## Key Findings

### 1. deepseek-chat is optimal for Hermes Agent
- **Fastest**: 1.1s avg (Agent with 5 tool calls = 5.5s total vs 47s for glm-5.2)
- **Cheapest practical**: ¥0.0005/call (glm-5.2 is cheaper at ¥0.0002 but 9x slower)
- **Zero reasoning waste**: non-reasoning model, doesn't "think" before tool calls
- **Hermes native support**: built-in `deepseek` provider, `DEEPSEEK_API_KEY` already configured

### 2. qwen3.7-max has best tool selection but unusable
- Only model that correctly chose `create_note` for "新建笔记" prompt (3/3 accuracy)
- But 636 reasoning tokens on that call (20.6s latency, ¥0.0075 cost)
- For Agent use, 20s per tool decision is unacceptable — 5 calls = 100s+

### 3. Reasoning models are bad for Agent tool-calling
Reasoning models (glm-5.2, v4-pro, qwen3.7-max) "think" before EVERY tool call.
In an Agent loop with N tool calls, reasoning overhead multiplies:
- 5 calls × glm-5.2 (9.5s) = 47.5s task
- 5 calls × ds-chat (1.1s) = 5.5s task
The user perceives this as the agent being "slow" or "hung".

### 4. Simple tool selection is easy; contextual judgment is hard
All 4 models correctly called `search_vault` for "搜索" prompts.
Only qwen3.7-max recognized "新建笔记" implied `create_note` not `search_vault`.
This suggests non-reasoning models may need more explicit system prompts for
tool selection — but the latency tradeoff still favors them.

## Hermes Official Docs Notes
- Hermes requires **64K+ context** minimum (most hosted models meet this)
- Built-in providers supporting Chinese models: `deepseek` (DeepSeek official),
  `z-ai` (智谱/Zhipu), `alibaba` (百炼/DashScope)
- Auxiliary model slots (title gen, vision, compression, approval, web extract)
  can be overridden independently — use cheap/fast models for these
- `hermes config set model.provider deepseek` + `hermes config set model.default deepseek-chat`

## Recommendation
For Hermes Agent main model: **deepseek-chat** (DeepSeek official)
- 5x faster than glm-5.2, 3x cheaper than v4-pro, zero reasoning waste
- Trade-off: slightly weaker tool selection (may need clearer system prompts)
- For deep analysis tasks, route to v4-pro via skills or auxiliary slots

Status: **Recommended to user, pending approval** (2026-06-19)

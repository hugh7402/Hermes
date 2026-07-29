# Agent Development Model Benchmark — 2026-06-27

## Context
User asked: "对现有模型进行测试，看哪个最合适做智能体开发"
Scope expanded from 智谱-only to cross-platform (7 platforms × 8 models) to find
the best model for agent development (tool-calling, code generation, instruction
following).

## Why This Differs from 2026-06-19 Agent Benchmark
The 2026-06-19 benchmark tested **4 models** with **OpenAI-style `tools` parameter**
(3 scenarios). This benchmark covers **8 models** with **free-form text prompts**
(4 scenarios) — tool selection via text instruction, not native tool API. This
complements the earlier benchmark and validates rankings across both methods.

## Methodology

### Test Cases (4 tasks, representative of agent development)

| # | Task | Type | What It Tests | Scoring |
|---|------|------|---------------|---------|
| 1 | "明天北京会不会下雨" → search_weather | Tool selection (clear) | Function name + arg extraction (10pts) |
| 2 | "记下我的灵感" → create_note | Tool selection (fuzzy) | Context understanding — not search, but create note (7pts max) |
| 3 | 智能体开发介绍 + 3个技术点 + 总结 | Instruction following | Format compliance, section ordering, Markdown (10pts) |
| 4 | CSV解析排序 Python函数 | Code generation | Function structure, error handling, type hints (10pts) |

**Settings**: `temperature: 0.1`, `max_tokens: 2000` (8000 for SiliconFlow V4-Pro)

### Models Tested

| Label | Platform | API Endpoint | Model ID | Price ¥/M in/out |
|-------|----------|-------------|----------|:---:|
| **deepseek-v4-flash** | DS官方 | api.deepseek.com | deepseek-chat | 1 / 2 |
| deepseek-v4-pro | DS官方 | api.deepseek.com | deepseek-reasoner | 4 / 16 |
| glm-5.2 | 智谱 | open.bigmodel.cn | glm-5.2 | 5 / 20 |
| glm-5.1 | 智谱 | open.bigmodel.cn | glm-5.1 | 2 / 8 |
| qwen3.7-max | 百炼 | dashscope.aliyuncs.com | qwen3.7-max | 4 / 20 |
| qwen-max | 百炼 | dashscope.aliyuncs.com | qwen-max | 4 / 12 |
| qwen-plus | 百炼 | dashscope.aliyuncs.com | qwen-plus | 0.8 / 2 |
| DS-V4-Pro-Si | 硅基流动 | api.siliconflow.cn | deepseek-ai/DeepSeek-V4-Pro | 1 / 4 |

## Results

### Ranking by Composite Score

| Rank | Model | Platform | Avg Score | Avg Latency | Cost (4 calls) | Composite |
|:---:|:---|:---|:---:|:---:|:---:|:---:|
| 🥇 | **deepseek-v4-flash** | **DS官方** | **9.2** | **2.0s** | **¥0.0019** | **91.5** |
| 🥈 | **qwen-plus** | **百炼** | **8.8** | **4.4s** | **¥0.0024** | **85.0** |
| 🥉 | qwen-max | 百炼 | 8.8 | 5.9s | ¥0.0074 | 77.9 |
| 4 | DS-V4-Pro-Si | 硅基 | 8.8 | 14.8s | ¥0.0095 | 69.5 |
| 5 | deepseek-v4-pro | DS官方 | 9.2 | 8.4s | ¥0.0473 | 68.3 |
| 6 | qwen3.7-max | 百炼 | 9.2 | 26.1s | ¥0.1166 | ~44 |
| 7 | glm-5.2 | 智谱 | 6.2 | 23.2s | ¥0.1152 | 44.1 |
| 8 | glm-5.1 | 智谱 | 4.5 | 17.2s | ¥0.0361 | 33.6 |

### Per-Task Scores

| Model | Platform | 工具1(天气) | 工具2(模糊) | 指令遵循 | 代码生成 | 均分 |
|:------|:---------|:---:|:---:|:---:|:---:|:---:|
| deepseek-v4-flash | DS官方 | **10** | **7** | **10** | **10** | **9.2** |
| deepseek-v4-pro | DS官方 | **10** | **7** | **10** | **10** | **9.2** |
| qwen3.7-max | 百炼 | **10** | **7** | **10** | **10** | **9.2** |
| qwen-plus | 百炼 | **10** | **7** | 8 | **10** | **8.8** |
| qwen-max | 百炼 | **10** | **7** | 8 | **10** | **8.8** |
| DS-V4-Pro-Si | 硅基 | **10** | **7** | 8 | **10** | **8.8** |
| glm-5.2 | 智谱 | **10** | **1** 🔴 | **4** 🔴 | **10** | **6.2** |
| glm-5.1 | 智谱 | 4 | **4** | 0 🔴 | **10** | **4.5** |

## Key Findings

### 1. 🥇 deepseek-v4-flash is the undisputed champion for agent development
- **13× faster than reasoning models**: 2.0s vs 26.1s (qwen3.7-max)
- **Zero reasoning overhead**: Non-reasoning models don't "think" before tool calls
- **Perfect scores** on 3 of 4 tasks
- **Cheapest**: ¥0.0019 for 4 calls (vs ¥0.1166 for qwen3.7-max)

### 2. 🥈 qwen-plus is the best runner-up
- 8.8/10 quality at 4.4s latency, ¥0.0024 cost
- Excellent value: 0.8/2 ¥/M pricing
- Lacks 2pts on instruction following vs flash (8 vs 10)

### 3. 🔴 Reasoning models are categorically BAD for agent development
**Three independent benchmarks (2026-06-19 tools API, 2026-06-19 daily chat, 2026-06-27 text prompts) all converge on the same conclusion:**

- **Latency is fatal**: In an Agent loop with N tool calls, every call is a painful wait
  - deepseek-v4-flash: 2.0s/call → 5 calls = 10s
  - qwen3.7-max: 26.1s/call → 5 calls = 130s (user gives up)
- **Token waste**: Reasoning tokens consume the output budget
  - glm-5.2 on tool test 2: 2000/2000 tokens consumed with NO content output
  - glm-5.2 on instruction following: 1956 reasoning tokens, content truncated
- **Edge case failure**: glm-5.2 scored 1/10 on fuzzy tool selection — model "thought"
  so hard about the answer that it never actually OUTPUT the answer

### 4. Bailian model name gotcha
- `qwen-3.7-max` (with hyphen) → **HTTP 404**
- `qwen3.7-max` (without hyphen) → ✅ **Works**
- Always verify model name format before benchmarking

### 5. qwen3.7-max has equal quality but unusable speed
- 9.2/10 quality score (same as flash)
- But 26.1s latency = 13× slower
- Only worth using for one-shot deep analysis where latency doesn't matter

## Recommendations

| Use Case | Model | Why |
|----------|-------|-----|
| **Agent main model** 🎯 | **deepseek-v4-flash** (DS官方) | 2.0s, ¥0.0019, zero reasoning waste |
| **Agent fallback** | **qwen-plus** (百炼) | 4.4s, ¥0.0024, stable |
| **Deep analysis** | deepseek-v4-pro (DS官方) | 9.2 quality, tolerable for one-shots |
| **NOT for agent** | glm-5.2, glm-5.1, qwen3.7-max | 20-26s latency, reasoning waste, content truncation |

## Full Raw Output

### deepseek-v4-flash (DS官方)
- 工具调用-天气: 0.6s | 10/10 | 0 reasoning | 18 output tokens
- 工具调用-模糊: 0.8s | 7/10 | 0 reasoning | 34 output
- 指令遵循: 3.5s | 10/10 | 0 reasoning | 282 output
- 代码生成: 2.9s | 10/10 | 0 reasoning | 386 output
- **Avg: 2.0s | 9.2/10 | ¥0.0019**

### qwen-plus (百炼)
- 工具调用-天气: 0.7s | 10/10 | 0 reasoning | 16 output
- 工具调用-模糊: 0.8s | 7/10 | 0 reasoning | 21 output
- 指令遵循: 5.1s | 8/10 | 0 reasoning | 309 output
- 代码生成: 11.0s | 10/10 | 0 reasoning | 705 output
- **Avg: 4.4s | 8.8/10 | ¥0.0024**

### qwen-max (百炼)
- 工具调用-天气: 1.6s | 10/10 | 0 reasoning | 16 output
- 工具调用-模糊: 2.1s | 7/10 | 0 reasoning | 22 output
- 指令遵循: 11.2s | 8/10 | 0 reasoning | 208 output
- 代码生成: 8.6s | 10/10 | 0 reasoning | 230 output
- **Avg: 5.9s | 8.8/10 | ¥0.0074**

### DS-V4-Pro-Si (硅基流动, 2.5折)
- 工具调用-天气: 2.6s | 10/10 | 27 reasoning | 45 output
- 工具调用-模糊: 9.0s | 7/10 | 247 reasoning | 269 output
- 指令遵循: 6.7s | 8/10 | 51 reasoning | 274 output
- 代码生成: 40.9s | 10/10 | 1060 reasoning | 1681 output
- **Avg: 14.8s | 8.8/10 | ¥0.0095**

### deepseek-v4-pro (DS官方)
- 工具调用-天气: 1.6s | 10/10 | 90 reasoning | 109 output
- 工具调用-模糊: 3.5s | 7/10 | 269 reasoning | 305 output
- 指令遵循: 5.2s | 10/10 | 121 reasoning | 436 output
- 代码生成: 23.4s | 10/10 | 1645 reasoning | 2000 output
- **Avg: 8.4s | 9.2/10 | ¥0.0473**

### qwen3.7-max (百炼) — correct model name: qwen3.7-max (no hyphen)
- 工具调用-天气: 2.8s | 10/10 | 82 reasoning | 116 output
- 工具调用-模糊: 8.0s | 7/10 | 366 reasoning | 417 output
- 指令遵循: 46.8s | 10/10 | 2337 reasoning | 2572 output
- 代码生成: 46.9s | 10/10 | 2018 reasoning | 2577 output
- **Avg: 26.1s | 9.2/10 | ~¥0.1166**

### glm-5.2 (智谱)
- 工具调用-天气: 2.5s | 10/10 | 61 reasoning | 79 output
- 工具调用-模糊: **34.2s** | **1/10** | **2000/2000 tokens consumed, NO content**
- 指令遵循: 32.7s | 4/10 | 1956 reasoning, content truncated
- 代码生成: 23.4s | 10/10 | 1050 reasoning | 1574 output
- **Avg: 23.2s | 6.2/10 | ¥0.1152**

### glm-5.1 (智谱)
- 工具调用-天气: 4.5s | 4/10 | 199 reasoning | 221 output (markdown code fence wrapping)
- 工具调用-模糊: 8.5s | 4/10 | 386 reasoning | 416 output (wrong format)
- 指令遵循: **26.6s** | **0/10** | **1983 reasoning, content empty**
- 代码生成: 29.0s | 10/10 | 1282 reasoning | 1768 output
- **Avg: 17.2s | 4.5/10 | ¥0.0361**

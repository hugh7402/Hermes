# Daily Chat Benchmark — 2026-06-19

## Context
User requested comparison of glm-5.2 vs deepseek-v4-pro for daily conversation (Hermes chat model).
Added deepseek-chat (non-reasoning) and tested across 3 platforms.

## Setup
- 5 scenarios: greeting, knowledge QA (智慧民政), Chinese rewrite, logic analysis, proposal outline
- 4 models × 3 platforms
- max_tokens=2048-4096 (large enough for reasoning models)
- temperature=0.7

## Models Tested

| Label | Platform | Model | Pricing (¥/M in/out) |
|-------|----------|-------|:---:|
| glm5.2-zhipu | 智谱官方 | glm-5.2 | 0.5 / 0.5 |
| v4pro-silicon | 硅基流动 (2.5折) | deepseek-ai/DeepSeek-V4-Pro | 3.0 / 6.0 |
| v4pro-deepseek | DeepSeek官方 | deepseek-v4-pro | 3.1 / 6.2 |
| ds-chat-deepseek | DeepSeek官方 | deepseek-chat | 1.0 / 2.0 |

## Results Summary

| Model | Avg Latency | Cost/Chat | Avg Reasoning Tokens | Avg Content Length |
|-------|:---:|:---:|:---:|:---:|
| glm5.2-zhipu | 24.5s ❌ | ¥0.0007 | 794 | 906c |
| v4pro-silicon | 18.2s | ¥0.0044 | 494 | 384c |
| v4pro-deepseek | 15.5s | ¥0.0062 | 642 | 593c |
| **ds-chat-deepseek** | **4.5s** ✅ | **¥0.0006** | **0** | 479c |

## Per-Scenario Latency

| Scenario | glm-5.2 | v4pro-硅基 | v4pro-官方 | ds-chat |
|----------|:---:|:---:|:---:|:---:|
| Hello/weather | 18.0s | 7.8s | 5.0s | **1.4s** |
| 智慧民政 QA | 28.5s | 13.0s | 19.1s | **3.0s** |
| Chinese rewrite | 17.3s | 11.8s | 14.6s | **1.1s** |
| Logic analysis | 21.7s | 29.5s | 17.9s | **4.7s** |
| Proposal outline | 37.0s | 28.9s | 20.7s | **12.3s** |

## Key Findings

### 1. Reasoning models are catastrophic for daily chat
glm-5.2 burns 639 reasoning tokens to answer "你好，今天天气怎么样？" — taking 18 seconds to produce 63 characters. For real-time conversation, this is unusable.

### 2. Non-reasoning deepseek-chat wins decisively
5x faster than glm-5.2 (4.5s vs 24.5s), same cost (¥0.0006 vs ¥0.0007/chat), zero reasoning waste. Content quality sufficient for daily chat (government domain knowledge accurate, proposal outlines well-structured).

### 3. v4-pro too expensive for casual chat
At ¥0.0044-0.0062/chat (7-10x ds-chat), with reasoning overhead and 15-18s latency, v4-pro is overkill for daily conversation. Reserve for deep analysis / proposal writing.

### 4. glm-5.2 content quality is highest
When it eventually responds, glm-5.2 produces the most detailed, well-structured output (906c avg vs 479c for ds-chat). Best for async tasks where latency doesn't matter, worst for interactive chat.

## Timing Bug Discovered
Initial benchmark showed 0.1s latency for DeepSeek models — this was a measurement bug:
```python
# BUG: urlopen returns when headers arrive, not when body is complete
resp = urllib.request.urlopen(req, timeout=90)
latency = time.time() - t0  # ← only measures header time!
data = json.loads(resp.read())  # ← body read happens here, not measured

# FIX: measure after resp.read()
resp = urllib.request.urlopen(req, timeout=120)
body = resp.read()
latency = time.time() - t0  # ← correct: includes body transfer time
```

## Recommendation
Switch Hermes daily chat from glm-5.2 to deepseek-chat (DeepSeek official).
- 5x faster (4.5s vs 24.5s)
- Same cost (¥0.0006 vs ¥0.0007/chat)
- Zero reasoning token waste
- Quality sufficient for daily conversation

Status: **Pending user approval** (user asked for comparison, results presented 2026-06-19)

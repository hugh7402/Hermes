# 三平台模型全场景 Benchmark (2026-06-18)

## 13-Model × 3-Scenario Full Matrix

3 scenarios: Knowledge accuracy (场景A), Logical reasoning (场景B), Instruction following (场景C).
Scoring: speed (60%) + precision/output-tokens (40%).

| Rank | Model | Platform | Avg Lat | Avg Tok | Overall | Notes |
|------|-------|----------|---------|---------|---------|-------|
| 1 | deepseek-chat | DeepSeek | 2.7s | 235t | ⭐⭐⭐⭐⭐ | Fast, accurate, best all-around |
| 2 | qwen-turbo | 百炼 | 2.1s | 255t | ⭐⭐⭐⭐ | Fast but hollow content |
| 3 | qwen-max | 百炼 | 5.7s | 190t | ⭐⭐⭐⭐ | Good speed, copies placeholders |
| 4 | Qwen2.5-32B | SF | 8.2s | 165t | ⭐⭐⭐⭐ | — |
| 5 | deepseek-reasoner | DeepSeek | 4.8s | 484t | ⭐⭐⭐⭐ | Deepest reasoning |
| 6 | deepseek-v4-flash | 百炼 | 4.3s | 576t | ⭐⭐⭐⭐ | Good but verbose |
| 7 | qwen-plus | 百炼 | 6.5s | 281t | ⭐⭐⭐ | — |
| 8 | deepseek-v3.2 | 百炼 | 5.9s | 255t | ⭐⭐⭐ | Good quality |
| 9 | DeepSeek-V3 | SF | 8.4s | 253t | ⭐⭐⭐ | Proxy overhead |
| 10 | Qwen2.5-72B | SF | 12.7s | 210t | ⭐⭐ | Slow for chat |
| 11 | glm-5.2 | 百炼 | 19.9s | 1215t | ⭐⭐ | Verbose |
| 12 | qwen3.7-max | 百炼 | 24.7s | 1334t | ⭐ | Too slow |
| 13 | qwen3.7-plus | 百炼 | 26.8s | 1454t | ⭐ | Too slow |

## Quality Deep-Dive

### Knowledge Accuracy (场景A: 智慧民政 policy Q&A)
- **deepseek-chat**: ✅ Specific (一网通办 + 社会救助/养老数据共享 + 殡葬婚姻治理)
- **deepseek-reasoner**: ✅ Most accurate (智慧养老 + 低收入监测 + 基层治理)
- **qwen-turbo**: ❌ Vague ("提升服务水平")
- **qwen-max**: ❌ Generic ("线上化便捷化" not民政-domain)

### Instruction Following (场景C: template-filling)
- **deepseek-chat**: ✅ Filled real business content
- **deepseek-reasoner**: ✅ Filled real content
- **deepseek-v3.2**: ✅ Filled real content
- **qwen-max**: ❌ Copied placeholders verbatim ("事项1", "风险描述")

### Logical Reasoning (场景B: task scheduling)
- All models arrived at correct answer (12 weeks, can complete)
- **deepseek-reasoner**: Most thorough step-by-step
- **deepseek-chat**: Clear and concise

## OCR Comparison

| Model | Platform | Latency | Price | Notes |
|-------|----------|---------|-------|-------|
| **PaddleOCR-VL-1.5** 🥇 | SiliconFlow | 0.8s | FREE | Dedicated OCR |
| qwen3-vl-flash | 百炼 | 0.8s | ¥0.15/¥1.5 | Fast |
| qwen3-vl-plus | 百炼 | 1.5s | ¥1/¥10 | — |
| qwen-vl-max | 百炼 | 1.6s | ¥1.6/¥4 | — |
| Qwen3-VL-8B | SiliconFlow | 2.4s | Paid | Old default |
| Qwen2.5-VL-72B | SiliconFlow | ❌ 403 | — | Unavailable |

## Text-to-Image

| Model | Platform | Latency | Status |
|-------|----------|---------|--------|
| Z-Image-Turbo | SiliconFlow | 4.7s | ✅ Current |
| z-image-turbo | 百炼 | ❌ 403 | Auth mismatch |

## Key Findings

1. **最新 ≠ 最好**: All 3.7-gen (glm-5.2, qwen3.7-max/plus) 22-54s, 10x slower
2. **deepseek-v4-pro broken on 百炼**: 2 empty responses confirmed
3. **百炼 < DeepSeek官方**: Same model via proxy 2-3x slower
4. **qwen-max copies placeholders**: Poor at structured output tasks
5. **PaddleOCR-VL-1.5 is best OCR**: Free, dedicated, 0.8s on SiliconFlow
6. **deepseek-reasoner best for deep analysis**: Thorough reasoning, rich output

## Model Selection Principles (User 2026-06-18)

1. **效果第一** — speed + accuracy + precision + content quality
2. **其次性价比** — pick cheaper when quality comparable
3. **换模型需同意** — user consent required before switching

## Current Assignments

| Workload | Platform | Model | Latency | Cost |
|----------|----------|-------|---------|------|
| Hermes Chat | DeepSeek 官方 | deepseek-chat/reasoner | 2.7-4.8s | ¥1-4/¥2-16 |
| Note Enhancement | 百炼 | qwen-max | 7s/note | ¥2.5/¥10 |
| OCR | SiliconFlow | PaddleOCR-VL-1.5 | 0.8s | FREE |
| Image Gen | SiliconFlow | Z-Image-Turbo | 4.7s | Free credits |

# 13-Model × 3-Scenario Benchmark (2026-06-18)

Full benchmark of all available models across three platforms for Hermes dialogue selection.

## Methodology

3 scenarios designed to test different dimensions:
- **场景A**: Knowledge accuracy (factual Q&A about 智慧民政)
- **场景B**: Logical reasoning (task scheduling with dependencies)
- **场景C**: Instruction following (template-filling with strict format)

Scoring: speed (60% weight) + precision/output-tokens (40% weight)

## Results

| Rank | Model | Platform | Avg Latency | Avg Tokens | Speed | Precision | Overall |
|------|-------|----------|-------------|------------|-------|-----------|---------|
| 1 | deepseek-chat | DeepSeek | 2.7s | 235t | 5.0 | 4.0 | 4.6 |
| 2 | qwen-turbo | 百炼 | 2.1s | 255t | 5.0 | 4.0 | 4.6 |
| 3 | qwen-max | 百炼 | 5.7s | 190t | 4.0 | 5.0 | 4.4 |
| 4 | Qwen2.5-32B | SiliconFlow | 8.2s | 165t | 4.0 | 5.0 | 4.4 |
| 5 | deepseek-reasoner | DeepSeek | 4.8s | 484t | 5.0 | 3.0 | 4.2 |
| 6 | deepseek-v4-flash | 百炼 | 4.3s | 576t | 5.0 | 3.0 | 4.2 |
| 7 | qwen-plus | 百炼 | 6.5s | 281t | 4.0 | 4.0 | 4.0 |
| 8 | deepseek-v3.2 | 百炼 | 5.9s | 255t | 4.0 | 4.0 | 4.0 |
| 9 | DeepSeek-V3 | SiliconFlow | 8.4s | 253t | 4.0 | 4.0 | 4.0 |
| 10 | Qwen2.5-72B | SiliconFlow | 12.7s | 210t | 3.0 | 4.0 | 3.4 |
| 11 | glm-5.2 | 百炼 | 19.9s | 1215t | 3.0 | 2.0 | 2.6 |
| 12 | qwen3.7-max | 百炼 | 24.7s | 1334t | 2.0 | 2.0 | 2.0 |
| 13 | qwen3.7-plus | 百炼 | 26.8s | 1454t | 2.0 | 2.0 | 2.0 |

## Quality Deep-Dive

### Knowledge Accuracy (场景A)
- **deepseek-chat**: ✅ Accurate, specific (一网通办 + 社会救助/养老数据共享 + 殡葬婚姻治理)
- **deepseek-reasoner**: ✅ Most accurate (智慧养老 + 低收入监测 + 基层治理)
- **qwen-turbo**: ❌ Vague ("提升服务水平" no specifics)
- **qwen-max**: ❌ Generic ("线上化便捷化" not民政-domain)

### Instruction Following (场景C)
- **deepseek-chat**: ✅ Perfect — filled real business content
- **deepseek-reasoner**: ✅ Perfect — filled real content
- **deepseek-v3.2**: ✅ Perfect — filled real content
- **qwen-turbo**: ⚠️ Followed format but content hollow ("系统模块A")
- **qwen-max**: ❌ Copied placeholders verbatim ("事项1", "风险描述")

### Logical Reasoning (场景B)
- All models arrived at the correct answer (3 months = 12 weeks, can complete).
- **deepseek-reasoner**: Most thorough step-by-step reasoning
- **deepseek-chat**: Clear and concise
- **qwen-max**: Good reasoning but 13.4s (5x slower than chat)

## OCR Comparison

| Model | Platform | Latency | Price | Notes |
|-------|----------|---------|-------|-------|
| PaddleOCR-VL-1.5 | SiliconFlow | 0.8s | FREE | Dedicated OCR |
| qwen3-vl-flash | 百炼 | 0.8s | ¥0.15/¥1.5 | Fast, cheap |
| qwen3-vl-plus | 百炼 | 1.5s | ¥1/¥10 | Good quality |
| qwen-vl-max | 百炼 | 1.6s | ¥1.6/¥4 | Legacy |
| Qwen3-VL-8B | SiliconFlow | 2.4s | Paid | Previous default |
| Qwen2.5-VL-72B | SiliconFlow | ❌ 403 | - | Not available |

Note: OCR quality comparison used AI-generated images (poor Chinese rendering). Real scanned documents may differ.

## Text-to-Image Comparison

| Model | Platform | Latency | Status |
|-------|----------|---------|--------|
| Z-Image-Turbo | SiliconFlow | 4.7s | ✅ Current |
| z-image-turbo | 百炼 | ❌ 403 | Auth/endpoint issue |

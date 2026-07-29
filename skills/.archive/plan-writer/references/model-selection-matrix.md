# 三平台模型选型矩阵 (2026-06-18)

## 选型原则

1. **效果第一** — 速度 + 准确率 + 精准度 + 内容优质，综合评估
2. **其次性价比** — 效果差距不大时选便宜的
3. **换模型必请示用户**

## 生产模型矩阵

| 用途 | 平台 | 模型 | 延迟 | 价格 ¥/M | 选型理由 |
|------|------|------|------|-----------|------|
| Hermes 对话 | DeepSeek 官方 | `deepseek-chat` | 1.5s | 1/2 | 最快最准 |
| 方案撰写 | 百炼 | `deepseek-v3.2` | 73s | 2/3 | 推理最强、零幻觉 |
| 笔记增强 | 百炼 | `qwen-max` | 7s | 2.5/10 | 快准狠 |
| OCR | SiliconFlow | `PaddleOCR-VL-1.5` | 0.8s | 免费 | 最快免费 |
| 文生图 | SiliconFlow | `Z-Image-Turbo` | 4.7s | 免费额度 | 可用 |

## 淘汰模型

| 模型 | 淘汰原因 |
|------|------|
| qwen3.7-max/plus | 延迟40-54s，方案输出<1000字 |
| glm-5.2 | 延迟20-54s，冗余2000+ tokens |
| deepseek-v4-pro(百炼) | 需8000 max_tokens，推理耗405t才产出 |
| deepseek-v4-flash(百炼) | 幻觉控制弱(2/4) |

## API 端点

| 平台 | 端点 | Key 变量 |
|------|------|------|
| DeepSeek 官方 | `https://api.deepseek.com/v1` | `DEEPSEEK_API_KEY` |
| 百炼(阿里云) | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `BAILIAN_API_KEY` |
| SiliconFlow | `https://api.siliconflow.cn/v1` | `SILICONFLOW_API_KEY` |

## 基准测试脚本

```bash
# Hermes 对话测试
python3 /opt/data/skills/mlops/llm-model-selection/scripts/benchmark_providers.py

# 方案撰写测试
python3 << 'PYEOF'
... (见 plan-model-benchmark.md)
PYEOF
```

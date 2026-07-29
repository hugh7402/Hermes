# 百炼 (Bailian) API for Hindsight Local Embedded

## API Endpoint

```
https://dashscope.aliyuncs.com/compatible-mode/v1
```

This is the OpenAI-compatible endpoint. All requests use standard `/chat/completions` and `/models` paths.

## Recommended Models for Memory Extraction

Memory extraction is a lightweight task (entity extraction, summarization, linking). Use the cheapest model that handles Chinese well:

| Model | Cost (per M tokens) | Notes |
|-------|---------------------|-------|
| `qwen-turbo` | ¥3 / ¥6 (in/out) | Cheapest, fast, good enough for extraction ✅ |
| `qwen-plus` | ¥4 / ¥12 | Slightly better quality |
| `qwen-max` | ¥20 / ¥60 | Overkill for memory extraction |
| `qwen3.7-max` | ¥12 / ¥36 | Heavy — use for document enhancement, not memory |
| `glm-5.1` | ¥6 / ¥24 | Good for Chinese, entity recognition strong |

**Default choice**: `qwen-turbo` — it's 5-10x cheaper than other options and quality is sufficient for the backend memory extraction task.

## API Key

- Env var: `BAILIAN_API_KEY` (in `$HERMES_HOME/.env`)
- Copied to `HINDSIGHT_LLM_API_KEY` for Hindsight plugin consumption
- Region: 华北2 (Beijing) — `dashscope.aliyuncs.com`

## Verification Command

```bash
/opt/hermes/.venv/bin/python3 -c "
import json, urllib.request
env = {}
with open('/opt/data/.env') as f:
    for line in f:
        if '=' in line and not line.startswith('#'):
            k, v = line.strip().split('=', 1)
            env[k] = v
key = env.get('BAILIAN_API_KEY', '')
req = urllib.request.Request('https://dashscope.aliyuncs.com/compatible-mode/v1/models')
req.add_header('Authorization', f'Bearer {key}')
resp = urllib.request.urlopen(req, timeout=10)
data = json.loads(resp.read())
print(f'Bailian API OK — {len(data[\"data\"])} models available')
"
```

## Full Config Template

```json
{
  "mode": "local_embedded",
  "llm_provider": "openai_compatible",
  "llm_model": "qwen-turbo",
  "llm_base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
  "bank_id": "hermes",
  "recall_budget": "mid",
  "recall_prefetch_method": "recall",
  "memory_mode": "hybrid",
  "auto_retain": true,
  "retain_async": true,
  "retain_every_n_turns": 1,
  "retain_context": "对话上下文标签",
  "auto_recall": true
}
```

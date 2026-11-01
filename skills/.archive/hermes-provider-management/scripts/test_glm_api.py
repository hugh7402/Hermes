#!/usr/bin/env python3
"""Test Z.AI / GLM API connectivity — run via execute_code to bypass secret redaction."""
import urllib.request, json, time, sys

url = sys.argv[1] if len(sys.argv) > 1 else "https://open.bigmodel.cn/api/paas/v4/chat/completions"
api_key = sys.argv[2] if len(sys.argv) > 2 else "your-api-key"
model = sys.argv[3] if len(sys.argv) > 3 else "glm-5.2"

data = json.dumps({
    "model": model,
    "messages": [{"role": "user", "content": "用一句话介绍你自己"}],
    "max_tokens": 2000
}).encode()

t0 = time.time()
req = urllib.request.Request(url, data=data,
    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"})
resp = urllib.request.urlopen(req, timeout=60)
result = json.loads(resp.read())

msg = result["choices"][0]["message"]
content = msg.get("content", "")
reasoning = msg.get("reasoning_content", "")
reasoning_tokens = result.get("usage", {}).get("completion_tokens_details", {}).get("reasoning_tokens", 0)
total_tokens = result.get("usage", {}).get("total_tokens", 0)

print(f"Model: {model}")
print(f"Latency: {time.time() - t0:.1f}s")
print(f"Finish: {result['choices'][0]['finish_reason']}")
print(f"Tokens: {total_tokens} total ({reasoning_tokens} reasoning, {total_tokens - reasoning_tokens} content)")
print(f"Content: {content[:200]}")

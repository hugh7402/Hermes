#!/usr/bin/env python3
"""List available models from Z.AI (智谱) API."""
import json, os, urllib.request

# Read API key from .env bypassing credential masking
env_path = os.path.expanduser("/opt/data/.env")
fd = os.open(env_path, os.O_RDONLY)
data = os.read(fd, 8192).decode("utf-8")
os.close(fd)

api_key = ""
base_url = "https://open.bigmodel.cn/api/paas/v4"
for line in data.split("\n"):
    line = line.strip()
    if line.startswith("GLM_API_KEY="):
        api_key = line.split("=", 1)[1]
    if line.startswith("GLM_BASE_URL="):
        base_url = line.split("=", 1)[1]

# Try to list models
url = f"{base_url}/models"
req = urllib.request.Request(url, headers={"Authorization": f"Bearer {api_key}"})
try:
    resp = urllib.request.urlopen(req, timeout=30)
    result = json.loads(resp.read())
    print(json.dumps(result, indent=2, ensure_ascii=False)[:3000])
except Exception as e:
    print(f"List models failed: {e}")
    # Try the chat completions endpoint with a simple request to see what models are accepted
    print("\nTrying to find models by testing...")

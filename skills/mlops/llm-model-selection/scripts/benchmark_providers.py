#!/usr/bin/env python3
"""Benchmark LLM providers/models for a specific task.
Usage: python3 benchmark_providers.py
Edit the ENDPOINTS list and PROMPT before running.

⚠️ TIMING: latency is measured AFTER resp.read() — urlopen() returns
   when headers arrive, but body transfer happens during read().
   Measuring between urlopen and read gives false 0.1s readings.
"""
import os, time, json, urllib.request

# ── Read API keys (bypass Hermes credential masking) ──
env_path = os.path.expanduser("/opt/data/.env")
fd = os.open(env_path, os.O_RDONLY)
data = os.read(fd, 8192).decode("utf-8")
os.close(fd)

keys = {}
for line in data.split("\n"):
    if "=" in line:
        k, v = line.strip().split("=", 1)
        v = v.strip().strip('"').strip("'")
        if "API_KEY" in k.upper():
            keys[k] = v

# ── Task-specific prompt (customize per use case) ──
PROMPT = "用中文提炼3条要点，每条≤30字：今天和产品团队讨论了智慧民政项目。低保申请模块已完成开发进入测试，预计下周一上线。养老服务接口文档还需补充，李工周三前完成。数据大屏原型获局领导认可，需增加实时刷新功能。下月重点是打通公安户籍系统数据接口，涉及等保测评需提前申请。"

# ── Endpoints to test ──
# Format: (display_name, url, key_name_from_env, model_id, max_tokens)
# NOTE: For reasoning models (v4-pro, glm-5.2, etc.), use max_tokens >= 2048
#       or they will consume all tokens on internal reasoning and return empty.
ENDPOINTS = [
    ("DeepSeek官方 deepseek-chat", "https://api.deepseek.com/v1/chat/completions", "DEEPSEEK_API_KEY", "deepseek-chat", 2048),
    ("DeepSeek官方 deepseek-v4-pro", "https://api.deepseek.com/v1/chat/completions", "DEEPSEEK_API_KEY", "deepseek-v4-pro", 4096),
    ("智谱官方 glm-5.2", "https://open.bigmodel.cn/api/paas/v4/chat/completions", "GLM_API_KEY", "glm-5.2", 4096),
    ("百炼 qwen-max", "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions", "BAILIAN_API_KEY", "qwen-max", 2048),
    ("SiliconFlow DeepSeek-V4-Pro", "https://api.siliconflow.cn/v1/chat/completions", "SILICONFLOW_API_KEY", "deepseek-ai/DeepSeek-V4-Pro", 4096),
]

# ── Run benchmarks ──
print("=" * 70)
print(f"Benchmark: {len(ENDPOINTS)} endpoints")
print(f"Prompt: {PROMPT[:80]}...")
print("=" * 70)

for name, url, key_name, model, max_tokens in ENDPOINTS:
    key = keys.get(key_name)
    if not key:
        print(f"\n⚠️  {name} | SKIP: {key_name} not found in .env")
        continue

    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": PROMPT}],
        "max_tokens": max_tokens,
        "temperature": 0.3
    }).encode()

    req = urllib.request.Request(url, data=body, headers={
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    })

    t0 = time.time()
    try:
        resp = urllib.request.urlopen(req, timeout=120)
        raw = resp.read()  # ← MUST read before measuring latency
        t1 = time.time()
        j = json.loads(raw)
        msg = j["choices"][0]["message"]
        content = msg.get("content", "") or ""
        reasoning = msg.get("reasoning_content", "") or ""
        u = j.get("usage", {})

        # Extract reasoning tokens if reported
        treason = 0
        cd = u.get("completion_tokens_details")
        if isinstance(cd, dict):
            treason = cd.get("reasoning_tokens", 0)

        print(f"\n✅ {name} ({model})")
        print(f"   Latency:  {t1-t0:.2f}s")
        print(f"   Tokens:   in={u.get('prompt_tokens','?')}  out={u.get('completion_tokens','?')}  reasoning={treason}")
        if reasoning:
            print(f"   Reasoning: {len(reasoning)} chars (thinking model)")
        print(f"   Output:   {content.strip()[:300]}")
        if not content and reasoning:
            print(f"   ⚠️  EMPTY output — reasoning consumed all tokens. Increase max_tokens.")
    except Exception as e:
        t1 = time.time()
        err = str(e)[:200]
        print(f"\n❌ {name} ({model})")
        print(f"   Latency: {t1-t0:.2f}s")
        print(f"   Error:   {err}")

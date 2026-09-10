#!/bin/bash
# 12:05 检测：DeepSeek V4.1 Flash 发布后主/备模型状态
export PATH=/opt/data/.venv/bin:$PATH
cd /opt/data/.tmp_tests
python3 - <<'PYEOF'
import json, os, urllib.request, time, datetime

print(f"=== 检测时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===")

def get_key(name):
    with open('/opt/data/.env') as f:
        for line in f:
            if line.startswith(name):
                return line.split('=', 1)[1].strip().strip("\"'")
    return None

# 1. DeepSeek 官方模型列表（对比基线: v4-flash/v4-pro/v4-flash-vision-exp）
k = get_key('DEEPSEEK_API_KEY')
req = urllib.request.Request('https://api.deepseek.com/v1/models',
                             headers={'Authorization': f'Bearer {k}'})
try:
    models = json.loads(urllib.request.urlopen(req, timeout=20).read())
    ids = [m['id'] for m in models.get('data', [])]
    print('官方模型列表:', ids)
    has_v41 = any('v4.1' in i.lower() or 'v41' in i.lower() for i in ids)
    print('官方出现V4.1独立标识:', has_v41)
except Exception as e:
    print('官方模型列表 ERROR:', e)

# 2. 官方 v4-flash 实测连通（12:00 后应已路由到 V4.1）
try:
    body = json.dumps({"model": "deepseek-v4-flash",
                       "messages": [{"role": "user", "content": "回复OK两字"}],
                       "max_tokens": 10}).encode()
    req2 = urllib.request.Request('https://api.deepseek.com/chat/completions',
                                  data=body, method='POST',
                                  headers={'Content-Type': 'application/json',
                                           'Authorization': f'Bearer {k}'})
    t0 = time.time()
    resp = json.loads(urllib.request.urlopen(req2, timeout=30).read())
    dt = time.time() - t0
    model_used = resp.get('model', '?')
    usage = resp.get('usage', {})
    print(f'官方 v4-flash 实测: OK ({dt:.1f}s) model={model_used}')
    # 计费提示：pricing 变化可通过响应头或 usage 间接看，主要看能通
except Exception as e:
    print('官方 v4-flash 实测 ERROR:', e)

# 3. 硅基流动 V4-Flash（V4.0 备用）可用性
k2 = get_key('SILICONFLOW_API_KEY')
try:
    body2 = json.dumps({"model": "deepseek-ai/DeepSeek-V4-Flash",
                        "messages": [{"role": "user", "content": "回复OK两字"}],
                        "max_tokens": 10}).encode()
    req3 = urllib.request.Request('https://api.siliconflow.cn/v1/chat/completions',
                                  data=body2, method='POST',
                                  headers={'Content-Type': 'application/json',
                                           'Authorization': f'Bearer {k2}'})
    t0 = time.time()
    resp2 = json.loads(urllib.request.urlopen(req3, timeout=30).read())
    dt = time.time() - t0
    print(f'硅基流动 V4-Flash(V4.0备用) 实测: OK ({dt:.1f}s) model={resp2.get("model","?")}')
except Exception as e:
    print('硅基流动 V4-Flash 实测 ERROR:', e)

# 4. 当前 Hermes 配置
with open('/opt/data/config.yaml') as f:
    cfg = f.read()
import re
m = re.search(r'^model:\s*\n(.*?)(?=^\S|\Z)', cfg, re.M | re.S)
print('--- config.yaml model 段 ---')
print(m.group(0).strip() if m else '未找到 model 段')
PYEOF

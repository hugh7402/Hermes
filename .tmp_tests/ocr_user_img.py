#!/usr/bin/env python3
"""OCR 用户发来的图片（SiliconFlow PaddleOCR-VL-1.5）"""
import base64, json, os, urllib.request

# 读 key
key = None
with open('/opt/data/.env') as f:
    for line in f:
        if line.startswith('SILICONFLOW_API_KEY'):
            key = line.split('=', 1)[1].strip().strip("'\"")
assert key, 'key not found'

img_path = '/opt/data/cache/images/img_a51916285d2e.jpg'
with open(img_path, 'rb') as f:
    b64 = base64.b64encode(f.read()).decode()

payload = {
    "model": "PaddlePaddle/PaddleOCR-VL-1.5",
    "messages": [{
        "role": "user",
        "content": [
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
            {"type": "text", "text": "请完整提取图片中的所有文字内容，包括标题、正文、表格数据等，按原布局顺序输出。只输出提取的文字，不要描述图片。"}
        ]
    }],
    "max_tokens": 3000,
    "temperature": 0.1
}

req = urllib.request.Request(
    'https://api.siliconflow.cn/v1/chat/completions',
    data=json.dumps(payload).encode(),
    headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {key}'}
)
try:
    resp = json.loads(urllib.request.urlopen(req, timeout=120).read())
    print(resp['choices'][0]['message']['content'])
except Exception as e:
    print('ERROR:', e)
    # try read body of error
    try:
        import traceback; traceback.print_exc()
    except: pass

"""补 OCR 失败页：对指定页码逐一重试，最多3次，成功后写入对应分片文件"""
import sys, os, json, base64, urllib.request, time, re

API_URL = "https://api.siliconflow.cn/v1/chat/completions"
MODEL = "PaddlePaddle/PaddleOCR-VL-1.5"
PDF = "/opt/data/WebChat BackUp/文档/20260819_具身智能训练场研究报告2026年发布.pdf"
FAILED_PAGES = [1, 4, 8, 12, 13, 20, 25, 30, 31, 34, 46, 49, 51, 54]  # 1-based

def get_api_key():
    fd = os.open("/opt/data/.env", os.O_RDONLY)
    try:
        data = os.read(fd, 8192).decode()
        for line in data.split('\n'):
            if line.startswith('SILICONFLOW_API_KEY='):
                return line.split('=', 1)[1].strip().strip('"').strip("'")
    finally:
        os.close(fd)
    return None

def ocr_page(image_b64):
    payload = json.dumps({
        "model": MODEL,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": "请提取图片中所有文字，保持原文段落结构。只输出文字，不要加解释。"},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}}
            ]
        }],
        "max_tokens": 4000
    }).encode()
    api_key = get_api_key()
    req = urllib.request.Request(API_URL, data=payload)
    req.add_header("Authorization", f"Bearer {api_key}")
    req.add_header("Content-Type", "application/json")
    resp = urllib.request.urlopen(req, timeout=180)
    data = json.loads(resp.read())
    return data["choices"][0]["message"]["content"]

import fitz
doc = fitz.open(PDF)
results = {}
for pg in FAILED_PAGES:
    i = pg - 1
    ok = False
    for attempt in range(3):
        try:
            pix = doc[i].get_pixmap(dpi=200)
            img_b64 = base64.b64encode(pix.tobytes("png")).decode()
            text = ocr_page(img_b64)
            results[pg] = text
            print(f"第{pg}页 ✓ 第{attempt+1}次尝试 ({len(text)}字)")
            ok = True
            break
        except urllib.request.HTTPError as e:
            print(f"第{pg}页 ✗ HTTP {e.code} (尝试{attempt+1}/3)，等30s")
            time.sleep(30)
        except Exception as e:
            print(f"第{pg}页 ✗ {e} (尝试{attempt+1}/3)，等10s")
            time.sleep(10)
    if not ok:
        print(f"第{pg}页 ✗✗ 3次全失败")
    time.sleep(1)

doc.close()
out = '/tmp/ocr_retry.json'
json.dump(results, open(out, 'w'), ensure_ascii=False)
print(f"\n补录 {len(results)} 页，保存 {out}")

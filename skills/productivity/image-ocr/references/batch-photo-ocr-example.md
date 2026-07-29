# 批量调研照片 OCR 处理（实战案例）

2026-07-28 处理 "陕农经"平台调研 29 张照片的完整流程。用两种 OCR 方案依次尝试：
- **首选**: SiliconFlow Qwen3-VL-32B-Instruct（效果好，无限额）
- **兜底**: OCR.space engine=1（免费但 25次/天）

## 步骤

### 1. 检查图片

```bash
ls -laS /opt/data/cache/images/img_*.jpg | head -35
```

典型调研照片 140-270KB 每张。确定图片路径和数量。

### 2. 方案 A: SiliconFlow VL 模型（推荐）

```python
import base64, json, urllib.request

with open('/opt/data/.env') as f:
    for line in f:
        if line.startswith('SILICONFLOW_API_KEY'):
            key = line.split('=', 1)[1].strip().strip("'").strip('"')
            break

images = sorted([f for f in os.listdir('.') if f.startswith('img_') and f.endswith('.jpg')])
results = {}

for idx, img_file in enumerate(images):
    with open(img_file, 'rb') as f:
        b64 = base64.b64encode(f.read()).decode()
    
    body = json.dumps({
        'model': 'Qwen/Qwen3-VL-32B-Instruct',
        'messages': [{
            'role': 'user',
            'content': [
                {'type': 'image_url', 'image_url': {'url': f'data:image/jpeg;base64,{b64}'}},
                {'type': 'text', 'text': '请完整提取图片中的所有中文文字内容，包括表格数据、标题等。只输出文字，不要描述图片。'}
            ]
        }],
        'max_tokens': 2000,
        'temperature': 0.1
    }).encode()
    
    req = urllib.request.Request('https://api.siliconflow.cn/v1/chat/completions', data=body, headers={
        'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'
    })
    resp = urllib.request.urlopen(req, timeout=120)
    text = json.loads(resp.read())['choices'][0]['message']['content']
    results[img_file] = text
    print(f'[{idx+1}/{len(images)}] {img_file}: {len(text)} chars')

with open('/tmp/ocr_results.json', 'w') as f:
    json.dump(results, f, ensure_ascii=False)
```

### 3. 方案 B: OCR.space（兜底，SiliconFlow 不可用时）

```python
import base64, json, urllib.request, urllib.parse, os, time

images = sorted([f for f in os.listdir('.') if f.startswith('img_') and f.endswith('.jpg')])

results = {}
for idx, img_file in enumerate(images):
    with open(img_file, 'rb') as f:
        b64 = base64.b64encode(f.read()).decode()
    
    for engine in [1, 2]:
        try:
            data = urllib.parse.urlencode({
                'base64Image': f'data:image/jpeg;base64,{b64}',
                'language': 'chs',
                'OCREngine': str(engine),
                'scale': 'true',
            }).encode()
            
            req = urllib.request.Request('https://api.ocr.space/parse/image', data=data)
            req.add_header('apikey', 'helloworld')
            resp = urllib.request.urlopen(req, timeout=30)
            result = json.loads(resp.read())
            
            if result.get('OCRExitCode') == 1:
                text = result.get('ParsedResults', [{}])[0].get('ParsedText', '').strip()
                if len(text) > 20:
                    results[img_file] = text
                    break
        except Exception as e:
            pass
        time.sleep(0.5)
    
    if (idx+1) % 5 == 0:
        with open('/tmp/ocr_partial.json', 'w') as f:
            json.dump(results, f, ensure_ascii=False)

with open('/tmp/ocr_results.json', 'w') as f:
    json.dump(results, f, ensure_ascii=False)
```

### 4. 持久化到知识库

```python
lines = ['# 项目名称调研素材', '']
for i, (k, v) in enumerate(sorted(data.items())):
    lines.append(f'### 图片{i+1}')
    lines.append(v.strip())
    lines.append('')

path = f'/opt/data/Obsidian Vault/Obsidian Vault/concepts/项目名称-调研素材-YYYYMMDD.md'
with open(path, 'w') as f:
    f.write('\n'.join(lines))
```

### 5. 查看 OCR 结果

```bash
python3 -c "
import json
with open('/tmp/ocr_results.json') as f:
    data = json.load(f)
for i, (k, v) in enumerate(sorted(data.items())):
    print(f'===== 图片 {i+1} ({len(v)} chars) =====')
    print(v.strip()[:500])
    print()
"
```

If user sends more images after the initial batch (e.g. "对了还有几张"), append to the same reference file:
```python
with open('/tmp/ocr_new.json') as f:
    new_data = json.load(f)
with open(path, 'a') as f:
    for k, v in new_data.items():
        f.write(f'\\n### {desc}\\n{v.strip()}\\n')
```

## 结果（SiliconFlow VL 方案）

| 指标 | 数值 |
|------|------|
| 单张耗时 | 5-15s（首次 ~40s） |
| 30+ 张总耗时 | ~5min |
| 无请求限额 | ✅ |
| 准确率 | 高（正确识别"陕农经""三资"等专业术语） |

## 关键经验

1. **首选 SiliconFlow VL 模型** — 准确率高、无限额。OCR.space 仅做兜底（25次/天限制太紧）
2. **SILICONFLOW_API_KEY 读取** — .env 文件中 key 可能带引号，用 `strip("'").strip('"')` 清洗
3. **OCR 文本总有错别字** — VL 模型比 OCR.space 好得多，但仍需人工校对（如"阝夹农纟圣"→"陕农经"）
4. **第二批图追加** — 用户可能分批发图，先追加到已有素材文件再出报告
5. **保存中间结果** — 长时间批量处理时定期保存，避免中途失败丢数据

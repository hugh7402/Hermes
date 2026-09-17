"""意大利语字幕 → 中文翻译 → SRT 生成（段内按句切分，时间按字符比例分配）"""
import json, os, re, time
import concurrent.futures
import urllib.request

SRC = '/opt/data/.tmp_tests/milan_asr.json'
OUT_ZH = '/opt/data/.tmp_tests/milan_zh.json'
SRT_ZH = '/opt/data/.tmp_tests/milan_zh.srt'
SRT_BI = '/opt/data/.tmp_tests/milan_bi.srt'
BATCH = 20
CONC = 4

KEY = None
for line in open('/opt/data/.env'):
    if line.startswith('DEEPSEEK_API_KEY='):
        KEY = line.split('=', 1)[1].strip().strip('"').strip("'")
        break
assert KEY

data = json.load(open(SRC))
segs = [d for d in data if d.get('text')]
print(f'待翻译 {len(segs)} 段', flush=True)

SYS = ('你是专业的影视字幕翻译。用户给你 JSON，值是需要翻译的意大利语字幕，'
       '键是编号。请把每条翻译成简体中文，保持键不变，输出同样的 JSON。'
       '要求：口语自然、简洁（字幕风格）、人名保留通用译名（如 Maldini=马尔蒂尼、'
       'Inzaghi=因扎吉、Pirlo=皮尔洛、Nesta=内斯塔、Gattuso=加图索、'
       'Ambrosini=安布罗西尼、Ancelotti=安切洛蒂、Shevchenko=舍甫琴科、Kaká=卡卡）。'
       '若原文识别有误或无意义，就按上下文推测最可能的意思。只输出 JSON，不要任何解释。')

def call(payload):
    body = json.dumps({
        'model': 'deepseek-chat',
        'messages': [{'role': 'system', 'content': SYS},
                     {'role': 'user', 'content': json.dumps(payload, ensure_ascii=False)}],
        'temperature': 0.3,
        'max_tokens': 4000,
        'response_format': {'type': 'json_object'},
    }).encode()
    req = urllib.request.Request('https://api.deepseek.com/v1/chat/completions', data=body,
                                 headers={'Authorization': f'Bearer {KEY}',
                                          'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=300) as r:
        d = json.loads(r.read().decode())
    txt = d['choices'][0]['message']['content'].strip()
    txt = re.sub(r'^```json\s*|\s*```$', '', txt)
    return json.loads(txt)

# 分批并发
batches = []
for i in range(0, len(segs), BATCH):
    chunk = segs[i:i + BATCH]
    batches.append({str(s['idx']): s['text'] for s in chunk})

results = {}
if os.path.exists(OUT_ZH):
    results = {int(k): v for k, v in json.load(open(OUT_ZH)).items()}
    print(f'已缓存 {len(results)} 条', flush=True)

def work(item):
    bi, payload = item
    if all(int(k) in results for k in payload):
        return None
    for attempt in range(3):
        try:
            return call(payload)
        except Exception as e:
            if attempt == 2:
                print(f'  批 {bi} 失败: {str(e)[:100]}', flush=True)
                return None
            time.sleep(3)
    return None

t0 = time.time()
with concurrent.futures.ThreadPoolExecutor(max_workers=CONC) as ex:
    for res in ex.map(work, list(enumerate(batches))):
        if res:
            for k, v in res.items():
                try:
                    results[int(k)] = v
                except ValueError:
                    pass
print(f'翻译完成: {len(results)} 条, 用时 {time.time()-t0:.0f}s', flush=True)
json.dump(results, open(OUT_ZH, 'w'), ensure_ascii=False, indent=1)

# === 生成 SRT ===
def ts(x):
    total_ms = int(round(x * 1000))
    h = total_ms // 3600000
    m = (total_ms % 3600000) // 60000
    s = (total_ms % 60000) // 1000
    ms = total_ms % 1000
    return f'{h:02d}:{m:02d}:{s:02d},{ms:03d}'

def split_sentences(text):
    """先按句末标点切；若某段仍过长，再按逗号切分（字幕单行不宜过长）"""
    parts = re.split(r'(?<=[。！？；.!?])\s*', text.strip())
    out = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        if len(p) > 34:
            # 按逗号/顿号细分，保留标点
            sub = re.split(r'(?<=[，、,])\s*', p)
            buf = ''
            for sp in sub:
                if len(buf) + len(sp) <= 30:
                    buf += sp
                else:
                    if buf:
                        out.append(buf)
                    buf = sp
            if buf:
                out.append(buf)
        else:
            out.append(p)
    return out

subs_zh, subs_bi = [], []
n = 0
for s in segs:
    idx = s['idx']
    zh = results.get(idx, '')
    it = s['text']
    if not zh:
        continue
    start, end = s['start'], s['end']
    dur = end - start
    zh_parts = split_sentences(zh)
    it_parts = split_sentences(it)
    if not zh_parts:
        continue
    total_chars = sum(len(p) for p in zh_parts) or 1
    cur = start
    for i, zp in enumerate(zh_parts):
        seg_dur = dur * len(zp) / total_chars
        a, b = cur, cur + seg_dur
        cur = b
        n += 1
        subs_zh.append((n, a, b, zp))
        # 双语：意大利语按比例配对（简单对应）
        if i < len(it_parts):
            subs_bi.append((n, a, b, f'{zp}\n{it_parts[i]}'))
        else:
            subs_bi.append((n, a, b, zp))

def write_srt(subs, path):
    with open(path, 'w') as f:
        for i, a, b, t in subs:
            f.write(f'{i}\n{ts(a)} --> {ts(b)}\n{t}\n\n')

write_srt(subs_zh, SRT_ZH)
write_srt(subs_bi, SRT_BI)
print(f'=== SRT 生成: {len(subs_zh)} 条中文 / {len(subs_bi)} 条双语 ===', flush=True)
print(f'中文: {SRT_ZH}', flush=True)
print(f'双语: {SRT_BI}', flush=True)

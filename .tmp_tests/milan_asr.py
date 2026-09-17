"""米兰纪录片：音频切分 + Qwen3-ASR 并发转录（带断点续传）"""
import os, json, glob, subprocess, time, sys
import concurrent.futures
import urllib.request

SEG_DIR = '/tmp/milan_seg'
OUT = '/opt/data/.tmp_tests/milan_asr.json'
MODEL = 'Qwen/Qwen3-ASR-1.7B'
WIN = 20
API = 'https://api.siliconflow.cn/v1/audio/transcriptions'

KEY = None
for line in open('/opt/data/.env'):
    if line.startswith('SILICONFLOW_API_KEY='):
        KEY = line.split('=', 1)[1].strip().strip('"').strip("'")
        break
assert KEY, 'key 未找到'

# 1. 切分
os.makedirs(SEG_DIR, exist_ok=True)
if not glob.glob(f'{SEG_DIR}/seg_*.mp3'):
    print('切分音频...', flush=True)
    subprocess.run(['ffmpeg', '-i', '/tmp/milan_audio.mp3', '-f', 'segment',
                    '-segment_time', str(WIN), '-c', 'copy', f'{SEG_DIR}/seg_%04d.mp3', '-y'],
                   capture_output=True)
segs = sorted(glob.glob(f'{SEG_DIR}/seg_*.mp3'))
print(f'共 {len(segs)} 段', flush=True)

# 2. 断点续传
results = {}
if os.path.exists(OUT):
    for d in json.load(open(OUT)):
        if d.get('text'):
            results[d['idx']] = d
    print(f'已缓存 {len(results)} 段', flush=True)

def post_file(path):
    """multipart 上传（纯标准库，避免依赖 requests）"""
    boundary = '----WebKitFormBoundary' + str(int(time.time() * 1000))
    with open(path, 'rb') as f:
        data = f.read()
    body = b''
    body += f'--{boundary}\r\nContent-Disposition: form-data; name="model"\r\n\r\n{MODEL}\r\n'.encode()
    body += f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{os.path.basename(path)}"\r\nContent-Type: audio/mpeg\r\n\r\n'.encode()
    body += data + b'\r\n'
    body += f'--{boundary}--\r\n'.encode()
    req = urllib.request.Request(API, data=body, headers={
        'Authorization': f'Bearer {KEY}',
        'Content-Type': f'multipart/form-data; boundary={boundary}',
    })
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read().decode())

def transcribe(item):
    idx, path = item
    if idx in results:
        return None
    for attempt in range(3):
        try:
            d = post_file(path)
            t = (d.get('text') or '').strip()
            return {'idx': idx, 'start': idx * WIN, 'end': (idx + 1) * WIN, 'text': t}
        except Exception as e:
            if attempt == 2:
                return {'idx': idx, 'start': idx * WIN, 'end': (idx + 1) * WIN, 'text': '', 'error': str(e)[:100]}
            time.sleep(2 * (attempt + 1))
    return None

todo = [(i, p) for i, p in enumerate(segs) if i not in results]
print(f'待处理 {len(todo)} 段', flush=True)
t0 = time.time()
done_n = 0
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
    for res in ex.map(transcribe, todo):
        if not res:
            continue
        results[res['idx']] = res
        done_n += 1
        if done_n % 20 == 0:
            json.dump(sorted(results.values(), key=lambda x: x['idx']), open(OUT, 'w'), ensure_ascii=False, indent=1)
            el = time.time() - t0
            eta = el / done_n * (len(todo) - done_n)
            print(f'  {done_n}/{len(todo)} 已处理 | 用时 {el:.0f}s | ETA {eta:.0f}s', flush=True)

json.dump(sorted(results.values(), key=lambda x: x['idx']), open(OUT, 'w'), ensure_ascii=False, indent=1)
ok = sum(1 for r in results.values() if r.get('text'))
print(f'=== 完成: {ok}/{len(segs)} 段有文本, 总用时 {time.time()-t0:.0f}s ===', flush=True)

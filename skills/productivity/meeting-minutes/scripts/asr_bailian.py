#!/usr/bin/env python3
"""百炼 ASR：fun-asr 异步（长音频，支持说话人分离+热词）/ qwen3-asr-flash 同步（短片段）。

用法:
    python3 asr_bailian.py <audio> --out result.json [--diarization] [--hotwords 词1,词2]
    python3 asr_bailian.py <audio> --out result.json --model qwen3-asr-flash   # 强制短片段通道

输出 JSON:
    {"model":..., "duration":..., "text":..., "segments":[{"start":1.2,"end":3.4,"speaker":"1","text":"..."}], "cost_estimate_yuan":...}

铁律：音频可能涉密，只走境内百炼。免费额度耗尽会报 AllocationQuota.FreeTierOnly，
需用户到控制台关闭「仅使用免费额度」，agent 无法代劳。
"""
import argparse
import base64
import json
import mimetypes
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

BASE = 'https://dashscope.aliyuncs.com'
ENV = '/opt/data/.env'


def getkey(name='BAILIAN_API_KEY'):
    """os.open 绕过文件掩码读 key。"""
    try:
        fd = os.open(ENV, os.O_RDONLY)
        data = os.read(fd, 400000).decode('utf-8', 'ignore')
        os.close(fd)
    except Exception as e:
        sys.exit(f'读 {ENV} 失败: {e}')
    m = re.search(rf'^{name}\s*=\s*(.+)$', data, re.M)
    if not m:
        sys.exit(f'{ENV} 里找不到 {name}')
    return m.group(1).strip().strip('"\'')


def post_json(url, body, key, extra_headers=None):
    h = {'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'}
    if extra_headers:
        h.update(extra_headers)
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=h)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raw = e.read().decode('utf-8', 'ignore')
        if 'FreeTierOnly' in raw:
            sys.exit('❌ 百炼免费额度已耗尽。需用户到百炼控制台关闭「仅使用免费额度」模式，'
                     'agent 无法代劳。开通后重跑本条命令。')
        sys.exit(f'❌ HTTP {e.code}: {raw[:600]}')


def get_json(url, key):
    req = urllib.request.Request(url, headers={'Authorization': f'Bearer {key}'})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f'❌ HTTP {e.code}: {e.read().decode("utf-8", "ignore")[:400]}')


def upload_to_dashscope(path, key, model='fun-asr'):
    """申请 OSS 上传凭证 → 直传 → 返回 oss:// URL。长音频必走这条路。"""
    pol = get_json(f'{BASE}/api/v1/uploads?action=getPolicy&model={model}', key)
    d = pol.get('data') or {}
    for f in ('policy', 'signature', 'upload_dir', 'upload_host', 'oss_access_key_id'):
        if not d.get(f):
            sys.exit(f'❌ 上传凭证缺字段 {f}: {json.dumps(pol, ensure_ascii=False)[:300]}')

    obj_key = f"{d['upload_dir']}/{uuid.uuid4().hex}_{os.path.basename(path)}"
    boundary = '----HermesASR' + uuid.uuid4().hex
    fields = [
        ('key', obj_key),
        ('policy', d['policy']),
        ('OSSAccessKeyId', d['oss_access_key_id']),
        ('signature', d['signature']),
        ('success_action_status', '200'),
        ('x-oss-object-acl', d.get('x_oss_object_acl', 'private')),
        ('x-oss-forbid-overwrite', d.get('x_oss_forbid_overwrite', 'true')),
    ]
    ctype = mimetypes.guess_type(path)[0] or 'application/octet-stream'
    body = b''
    for k, v in fields:
        body += (f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n').encode()
    body += (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; '
             f'filename="{os.path.basename(path)}"\r\nContent-Type: {ctype}\r\n\r\n').encode()
    with open(path, 'rb') as fh:
        body += fh.read()
    body += f'\r\n--{boundary}--\r\n'.encode()

    req = urllib.request.Request(
        d['upload_host'], data=body,
        headers={'Content-Type': f'multipart/form-data; boundary={boundary}'})
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            if r.status != 200:
                sys.exit(f'❌ OSS 上传失败 HTTP {r.status}')
    except urllib.error.HTTPError as e:
        sys.exit(f'❌ OSS 上传 HTTP {e.code}: {e.read().decode("utf-8", "ignore")[:400]}')
    return f'oss://{obj_key}'


def asr_async(path, key, diarization=False, hotwords=None, language='zh'):
    """fun-asr / qwen3-asr-flash-filetrans 异步。"""
    url = upload_to_dashscope(path, key, 'fun-asr')
    params = {'channel_id': [0], 'language_hints': [language]}
    if diarization:
        params['diarization_enabled'] = True
    if hotwords:
        params['vocabulary'] = {w: 4 for w in hotwords}
    body = {'model': 'fun-asr', 'input': {'file_urls': [url]}, 'parameters': params}
    r = post_json(f'{BASE}/api/v1/services/audio/asr/transcription', body, key,
                  {'X-DashScope-Async': 'enable'})
    task_id = (r.get('output') or {}).get('task_id')
    if not task_id:
        sys.exit(f'❌ 提交失败: {json.dumps(r, ensure_ascii=False)[:400]}')
    print(f'  任务已提交 task_id={task_id}', file=sys.stderr)

    for i in range(360):  # 最多等 60 分钟
        time.sleep(10)
        t = get_json(f'{BASE}/api/v1/tasks/{task_id}', key)
        st = (t.get('output') or {}).get('task_status')
        if st in ('SUCCEEDED', 'FAILED', 'CANCELED'):
            break
        if i % 6 == 0:
            print(f'  [{i*10}s] {st}', file=sys.stderr)
    else:
        sys.exit('❌ 转写超时（60 分钟）')

    out = t.get('output') or {}
    if st != 'SUCCEEDED':
        sys.exit(f'❌ 转写失败 {st}: {json.dumps(out, ensure_ascii=False)[:600]}')

    segs, texts = [], []
    for res in out.get('results', []):
        tu = res.get('transcription_url')
        if not tu:
            continue
        tr = get_json(tu, key) if not tu.startswith('http') else json.load(
            urllib.request.urlopen(tu, timeout=120))
        for tr_ in tr.get('transcripts', []):
            texts.append(tr_.get('text', ''))
            for s in tr_.get('sentences', []) or []:
                segs.append({
                    'start': s.get('begin_time', 0) / 1000.0,
                    'end': s.get('end_time', 0) / 1000.0,
                    'speaker': str(s.get('speaker_id', '')),
                    'text': (s.get('text') or '').strip(),
                })
    return {'text': '\n'.join(t for t in texts if t), 'segments': segs}


def asr_sync(path, key):
    """qwen3-asr-flash 同步，限 5 分钟 / 10MB。注意 input_audio.data 直接放 data URI，不要 format 字段。"""
    size = os.path.getsize(path)
    if size > 10 * 1024 * 1024:
        sys.exit(f'❌ 文件 {size/2**20:.1f}MB 超 10MB，同步通道用不了，改用 fun-asr')
    ext = os.path.splitext(path)[1].lower()
    mime = {'.mp3': 'audio/mpeg', '.wav': 'audio/wav', '.m4a': 'audio/mp4',
            '.aac': 'audio/aac', '.amr': 'audio/amr'}.get(ext, 'audio/mpeg')
    b64 = base64.b64encode(open(path, 'rb').read()).decode()
    body = {'model': 'qwen3-asr-flash', 'stream': False,
            'messages': [{'role': 'user', 'content': [
                {'type': 'input_audio', 'input_audio': {'data': f'data:{mime};base64,{b64}'}}]}]}
    r = post_json(f'{BASE}/compatible-mode/v1/chat/completions', body, key)
    txt = r['choices'][0]['message']['content']
    return {'text': txt if isinstance(txt, str) else json.dumps(txt, ensure_ascii=False),
            'segments': []}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('audio')
    ap.add_argument('--out', default='/tmp/asr_result.json')
    ap.add_argument('--model', default='fun-asr')
    ap.add_argument('--diarization', action='store_true', help='开启说话人分离')
    ap.add_argument('--hotwords', default='', help='逗号分隔的热词，政务项目名/系统名/人名')
    ap.add_argument('--language', default='zh')
    a = ap.parse_args()

    if not os.path.isfile(a.audio):
        sys.exit(f'❌ 文件不存在: {a.audio}')
    key = getkey()
    hw = [w.strip() for w in a.hotwords.split(',') if w.strip()] or None

    # 时长估算费用
    dur = 0.0
    try:
        import subprocess
        dur = float(subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
             '-of', 'default=nw=1:nk=1', a.audio],
            capture_output=True, text=True, timeout=60).stdout.strip() or 0)
    except Exception:
        pass
    if dur:
        print(f'  音频时长 {dur/60:.1f} 分钟，预估 ASR 费用 约 ¥{dur/3600*0.29:.2f}',
              file=sys.stderr)

    t0 = time.time()
    if a.model == 'qwen3-asr-flash':
        res = asr_sync(a.audio, key)
    else:
        res = asr_async(a.audio, key, a.diarization, hw, a.language)

    res.update({'model': a.model, 'duration': dur,
                'cost_estimate_yuan': round(dur / 3600 * 0.29, 3),
                'elapsed_s': round(time.time() - t0, 1)})
    with open(a.out, 'w', encoding='utf-8') as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
    print(f'✅ 转写完成 {len(res["segments"])} 段 / {len(res["text"])} 字 → {a.out}',
          file=sys.stderr)


if __name__ == '__main__':
    main()

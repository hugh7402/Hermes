#!/usr/bin/env python3
"""长音频转写：切段 + qwen3.8-omni-flash（绕开被锁的 ASR 专用通道）。

背景：百炼的 fun-asr / qwen3-asr-flash 报 AllocationQuota.FreeTierOnly 时，
多模态 omni 通道仍然可用，转写质量实测 17/17 关键词全中。

用法:
    python3 transcribe_omni.py <audio> --out /tmp/transcript.json \
        --terms "秦务员,民政通,政数局" [--chunk 600] [--model qwen3.8-omni-flash]

输出: {"text": 全文, "segments":[{"idx","start","end","text"}], "cost": {...}}
"""
import argparse
import base64
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

BASE = 'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions'
ENV = '/opt/data/.env'


def getkey(name='BAILIAN_API_KEY'):
    fd = os.open(ENV, os.O_RDONLY)
    d = os.read(fd, 400000).decode('utf-8', 'ignore')
    os.close(fd)
    m = re.search(rf'^{name}\s*=\s*(.+)$', d, re.M)
    if not m:
        sys.exit(f'{ENV} 缺 {name}')
    return m.group(1).strip().strip('"\'')


def duration(path):
    r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                        '-of', 'default=nw=1:nk=1', path], capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except Exception:
        return 0.0


def split_audio(path, outdir, chunk_sec):
    """切成 16k 单声道 mp3，体积小、ASR 够用。丢掉不足 1 秒的碎片段。"""
    os.makedirs(outdir, exist_ok=True)
    subprocess.run([
        'ffmpeg', '-v', 'error', '-i', path,
        '-f', 'segment', '-segment_time', str(chunk_sec),
        '-ac', '1', '-ar', '16000', '-b:a', '48k',
        '-reset_timestamps', '1',
        os.path.join(outdir, 'part%03d.mp3')
    ], check=True, capture_output=True)
    out = []
    for f in sorted(os.listdir(outdir)):
        if not f.endswith('.mp3'):
            continue
        p = os.path.join(outdir, f)
        if duration(p) >= 1.0:          # 空/碎片段会让 API 报 InvalidParameter
            out.append(p)
        else:
            os.remove(p)
    return out


def transcribe_chunk(path, key, model, prompt, retries=3):
    b64 = base64.b64encode(open(path, 'rb').read()).decode()
    body = {
        'model': model,
        'modalities': ['text'],
        'stream': False,
        'messages': [{'role': 'user', 'content': [
            {'type': 'text', 'text': prompt},
            {'type': 'input_audio', 'input_audio': {'data': f'data:audio/mpeg;base64,{b64}',
                                                    'format': 'mp3'}},
        ]}],
    }
    last = None
    for i in range(retries):
        req = urllib.request.Request(
            BASE, data=json.dumps(body).encode(),
            headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                res = json.load(r)
            txt = res['choices'][0]['message']['content']
            if not isinstance(txt, str):
                txt = json.dumps(txt, ensure_ascii=False)
            return txt.strip(), res.get('usage') or {}
        except urllib.error.HTTPError as e:
            raw = e.read().decode('utf-8', 'ignore')
            last = f'HTTP {e.code}: {raw[:200]}'
            if 'FreeTierOnly' in raw:
                sys.exit('❌ 该模型也被免费额度锁住，换 --model qwen3.5-omni-flash 再试')
            time.sleep(2 * (i + 1))
        except Exception as e:
            last = f'{type(e).__name__}: {e}'
            time.sleep(2 * (i + 1))
    raise RuntimeError(f'转写失败 {os.path.basename(path)}: {last}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('audio')
    ap.add_argument('--out', default='/tmp/transcript.json')
    ap.add_argument('--terms', default='', help='专有名词，逗号分隔，会写进 prompt 纠正同音错字')
    ap.add_argument('--chunk', type=int, default=600, help='每段秒数，默认 600')
    ap.add_argument('--model', default='qwen3.8-omni-flash')
    ap.add_argument('--keep-chunks', action='store_true')
    a = ap.parse_args()

    if not os.path.isfile(a.audio):
        sys.exit(f'❌ 不存在: {a.audio}')
    key = getkey()
    total = duration(a.audio)
    if total:
        print(f'  音频 {total/60:.1f} 分钟，按 {a.chunk}s 切分', file=sys.stderr)

    tmp = tempfile.mkdtemp(prefix='omni_asr_')
    try:
        parts = split_audio(a.audio, tmp, a.chunk)
        print(f'  切成 {len(parts)} 段', file=sys.stderr)

        terms = [t.strip() for t in a.terms.split(',') if t.strip()]
        prompt = ('你是语音转写工具。把音频里的中文原样转写成文字。'
                  '只输出转写文本，不要解释、不要总结、不要加标题。')
        if terms:
            prompt += ('\n这些专有名词必须按原样写对，不要写错别字或同音字：'
                       + '、'.join(terms) + '。')

        segs, usages = [], []
        offset = 0.0
        for i, p in enumerate(parts):
            t0 = time.time()
            txt, usg = transcribe_chunk(p, key, a.model, prompt)
            usages.append(usg)
            d = duration(p)
            segs.append({'idx': i, 'start': round(offset, 1),
                         'end': round(offset + d, 1), 'text': txt})
            offset += d
            print(f'  [{i+1}/{len(parts)}] {time.time()-t0:.0f}s  {d:.0f}s音频  '
                  f'{len(txt)}字', file=sys.stderr)

        text = '\n'.join(s['text'] for s in segs)
        cost = {
            'prompt_tokens': sum(u.get('prompt_tokens', 0) for u in usages),
            'completion_tokens': sum(u.get('completion_tokens', 0) for u in usages),
            'audio_tokens': sum((u.get('prompt_tokens_details') or {}).get('audio_tokens', 0)
                                for u in usages),
            'total_tokens': sum(u.get('total_tokens', 0) for u in usages),
        }
        out = {'model': a.model, 'audio': os.path.basename(a.audio),
               'duration_s': total, 'text': text, 'segments': segs, 'usage': cost}
        with open(a.out, 'w', encoding='utf-8') as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
        print(f'✅ {len(text)} 字 → {a.out}', file=sys.stderr)
        print(f'   tokens: {cost}', file=sys.stderr)
    finally:
        if not a.keep_chunks:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    main()

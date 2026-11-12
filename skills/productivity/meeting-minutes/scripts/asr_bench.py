#!/usr/bin/env python3
"""百炼 ASR / 多模态转写模型横评：同一音频 + 同一标准答案，比准确率 / 专名命中 / 耗时 / 次数间的稳定性。

用途：用户问“哪个 ASR 模型最好用”、或百炼上线/下线模型、或账号额度开关变动后需要重新定选型时跑一次，
不要每次手写测试。

两种模式：
  1. 合成模式（默认）：用 edge-tts 把内置政务文本读成音频，天然有标准答案，最适合比模型。
  2. 真实音频模式：--audio <文件> --ref <标准答案.txt>，拿真会议片段比（噪声/抢话下更接近实战）。

用法:
    # 内置文本，跑 3 次看稳定性
    /opt/data/.venv/bin/python3 scripts/asr_bench.py

    # 只比指定模型，跑 5 次
    /opt/data/.venv/bin/python3 scripts/asr_bench.py --models qwen3.8-omni-flash qwen3-asr-flash --runs 5

    # 用真实会议片段 + 自己的标准答案
    /opt/data/.venv/bin/python3 scripts/asr_bench.py --audio /tmp/real3min.mp3 --ref /tmp/ref.txt

依赖: edge-tts（仅合成模式）、ffprobe。Key 从 /opt/data/.env 的 BAILIAN_API_KEY 读。
"""
import argparse
import asyncio
import base64
import difflib
import json
import os
import pathlib
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request

BASE = 'https://dashscope.aliyuncs.com'
ENV = '/opt/data/.env'

# 标准答案：故意塞满政务专有名词（同音易错字是拉开差距的关键）
DEFAULT_REF = (
    '好，今天这个会主要定三件事。第一，民政通在支付宝端的阵地建设，要等孙书记回来确认以后再启动，'
    '所有政务事项必须对接秦务员统一入口，这是竣工验收的硬性条件。第二，浪潮和腾讯过渡期的使用费问题，'
    '这周内要拿出方案。第三，养老助餐全省推广的设备成本，先按免费碰一碰那条路去谈，咸阳试点的六个助餐点、'
    '三百多名用户的资金链路要理清楚。数据这块，所有交易和核验数据统一收口到民政侧，不要散在第三方平台，'
    '省政数局明确要求核心系统部署在政务云。'
)
DEFAULT_KW = ['民政通', '支付宝', '孙书记', '秦务员', '竣工验收', '浪潮', '腾讯', '使用费',
              '养老助餐', '碰一碰', '咸阳', '助餐点', '三百', '资金链路', '民政侧', '政数局', '政务云']

# 三族请求形状，写错就是 format is empty / UNSUPPORTED_FORMAT
OMNI = ['qwen3.8-omni-flash', 'qwen3.5-omni-flash']
ASR_PLAIN = ['qwen3-asr-flash']            # data URI，绝对不带 format
FUN_FLASH = ['fun-asr-flash-2026-06-15']   # format + vocabulary 都在请求顶层
# 异步族只认公网 HTTPS，本地 oss:// 喂不进去，横评直接跳过
ASYNC_ONLY = ['fun-asr', 'qwen3-asr-flash-filetrans']


def getkey(name='BAILIAN_API_KEY'):
    fd = os.open(ENV, os.O_RDONLY)
    d = os.read(fd, 400000).decode('utf-8', 'ignore')
    os.close(fd)
    m = re.search(rf'^{name}\s*=\s*(.+)$', d, re.M)
    return m.group(1).strip().strip('"\'') if m else None


def norm(s):
    return re.sub(r'[^\u4e00-\u9fffA-Za-z0-9]', '', s or '')


def sim(ref, hyp):
    """字符级相似度（1 - CER 的近似），0~1 越高越好。"""
    r, h = norm(ref), norm(hyp)
    if not r:
        return 0.0
    return round(difflib.SequenceMatcher(None, r, h).ratio(), 4)


def make_audio(path, text):
    import edge_tts

    async def go():
        await edge_tts.Communicate(text, 'zh-CN-YunxiNeural').save(path)
    asyncio.run(go())
    r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                        '-of', 'default=nw=1:nk=1', path], capture_output=True, text=True)
    return float((r.stdout or '0').strip() or 0)


def build_body(model, uri, kw):
    if model in OMNI:
        return {'model': model, 'modalities': ['text'], 'stream': False,
                'messages': [{'role': 'user', 'content': [
                    {'type': 'text', 'text': PROMPT},
                    {'type': 'input_audio', 'input_audio': {'data': uri, 'format': 'mp3'}}]}]}
    if model in ASR_PLAIN:
        return {'model': model, 'stream': False,
                'messages': [{'role': 'user', 'content': [
                    {'type': 'input_audio', 'input_audio': {'data': uri}}]}]}
    if model in FUN_FLASH:
        return {'model': model, 'stream': False, 'format': 'mp3',
                'vocabulary': {w: 4 for w in kw},
                'messages': [{'role': 'user', 'content': [
                    {'type': 'input_audio', 'input_audio': {'data': uri}}]}]}
    raise ValueError(f'未知模型族: {model}（需要先在脚本里归类，否则请求形状会错）')


PROMPT = ''


def call(model, uri, key, kw):
    body = build_body(model, uri, kw)
    req = urllib.request.Request(f'{BASE}/compatible-mode/v1/chat/completions',
                                 data=json.dumps(body).encode(),
                                 headers={'Authorization': f'Bearer {key}',
                                          'Content-Type': 'application/json'})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=300) as r:
        res = json.load(r)
    txt = res['choices'][0]['message']['content']
    if isinstance(txt, list):
        txt = ''.join(c.get('text', '') for c in txt if isinstance(c, dict))
    return (txt or ''), round(time.time() - t0, 1), (res.get('usage') or {})


def main():
    global PROMPT
    ap = argparse.ArgumentParser()
    ap.add_argument('--audio', default='/tmp/asr_bench.mp3')
    ap.add_argument('--ref', default='')
    ap.add_argument('--models', nargs='*', default=OMNI + ASR_PLAIN + FUN_FLASH)
    ap.add_argument('--runs', type=int, default=3)
    a = ap.parse_args()

    key = getkey()
    if not key:
        raise SystemExit('BAILIAN_API_KEY 读取失败')

    ref = pathlib.Path(a.ref).read_text(encoding='utf-8') if a.ref else DEFAULT_REF
    kw = [w for w in DEFAULT_KW if w in ref] or DEFAULT_KW
    PROMPT = ('你是语音转写工具。把音频里的中文原样转写成文字。只输出转写文本，不要解释、不要总结。\n'
              '这些专有名词必须按原样写对：' + '、'.join(kw) + '。')

    dur = make_audio(a.audio, ref) if not a.ref else float(
        subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                        '-of', 'default=nw=1:nk=1', a.audio],
                       capture_output=True, text=True).stdout.strip() or 0)
    uri = f"data:audio/mpeg;base64,{base64.b64encode(open(a.audio, 'rb').read()).decode()}"
    print(f'音频 {dur:.1f} 秒，标准答案 {len(norm(ref))} 字，专名 {len(kw)} 个，每模型跑 {a.runs} 次\n')

    rows = []
    for m in a.models:
        if m in ASYNC_ONLY:
            print(f'  ⏭  {m:30s} 异步族只认公网 HTTPS，跳过')
            continue
        sims, hits, secs, miss = [], [], [], set()
        for i in range(a.runs):
            try:
                txt, sec, usg = call(m, uri, key, kw)
            except urllib.error.HTTPError as e:
                body = e.read().decode('utf-8', 'ignore')[:140]
                print(f'  ❌ {m:30s} HTTP {e.code}: {body}')
                break
            except Exception as e:
                print(f'  ❌ {m:30s} {type(e).__name__}: {str(e)[:120]}')
                break
            s = sim(ref, txt)
            h = sum(1 for w in kw if w in txt)
            sims.append(s)
            hits.append(h)
            secs.append(sec)
            for w in kw:
                if w not in txt:
                    miss.add(w)
            print(f'  {m:30s} 第{i+1}次  相似 {s:.4f}  命中 {h:2}/{len(kw)}  {sec:5.1f}s')
        if sims:
            rows.append({'model': m, 'sim_avg': round(sum(sims) / len(sims), 4),
                         'sim_min': min(sims), 'hit_min': min(hits),
                         'sec_avg': round(sum(secs) / len(secs), 1),
                         'stable': len(set(sims)) == 1 and len(set(hits)) == 1,
                         'miss': sorted(miss)})
        print()

    print('═══ 排名（先比最差一次，再看耗时）═══')
    print(f'{"模型":32s} {"平均":>7s} {"最差":>7s} {"命中最差":>8s} {"耗时":>7s}  稳定')
    for r in sorted(rows, key=lambda x: (-x['sim_min'], x['sec_avg'])):
        print(f"{r['model']:32s} {r['sim_avg']:7.4f} {r['sim_min']:7.4f} "
              f"{r['hit_min']:8d} {r['sec_avg']:6.1f}s  {'✅' if r['stable'] else '⚠️波动'}")
        if r['miss']:
            print(f"{'':32s} 漏/错: {r['miss']}")

    out = '/opt/data/.tmp_tests/asr_bench_result.json'
    pathlib.Path(out).write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'\n结果已存 {out}')
    print('判据：**先看“最差一次”再看平均**——生成式模型单次全对不代表可靠，')
    print('选型只认「多次全对且零波动」的那个（当前是 qwen3.8-omni-flash）。')


if __name__ == '__main__':
    sys.exit(main())

#!/usr/bin/env python3
"""加小鞋子中字磁链到 PikPak + 搜其他 3 部中字版"""
import asyncio, json, re, subprocess, sys, time
sys.path.insert(0, '/opt/data/.venv/lib/python3.13/site-packages')
from pikpakapi import PikPakApi
from urllib.parse import unquote

PROXY = 'http://127.0.0.1:10808'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'

MAGNETS = [
    ('小鞋子[国语音轨+简繁字幕].Children.of.Heaven.1997.BluRay.1080p.x265.10bit.2Audio-MiniHD',
     'magnet:?xt=urn:btih:0bf16177fb8ab707097c15d7fd31739e4133cd24'),
]

QUERIES = {
    '放牛班的春天': 'Les Choristes 国语音轨 OR 中文字幕',
    '心灵捕手': 'Good Will Hunting 国语音轨',
    '三傻大闹宝莱坞': '3 Idiots 中文字幕',
}

async def add_magnets():
    state = json.load(open('/opt/data/.pikpak_token.json'))
    api = PikPakApi.from_dict(state)
    ls = await api.file_list(parent_id='', size=100)
    movie_id = None
    for f in ls.get('files', []):
        if f.get('kind') == 'drive#folder' and f['name'] == 'Movie':
            movie_id = f['id']
            break
    for name, mag in MAGNETS:
        print(f'➕ {name}')
        task = await api.offline_download(mag, parent_id=movie_id)
        print(f'  task: {task.get("task", {}).get("id", "?")}')
    return api

def btdig_search(q):
    url = 'https://btdig.com/search?q=' + q.replace(' ', '+').replace(' OR ', '+')
    for attempt in range(3):
        r = subprocess.run(['curl', '-sL', '--max-time', '30', '-x', PROXY,
                            '-H', f'User-Agent: {UA}', url],
                           capture_output=True, text=True, timeout=40)
        html = r.stdout
        if len(html) > 3000:
            return html
        time.sleep(15)
    return ''

def parse_btdig(html):
    out = []
    mags = re.findall(r'href="(magnet:[^"]+)"', html)
    seen = set()
    for m in mags:
        m = m.replace('&amp;', '&')
        h = re.search(r'btih:([a-fA-F0-9]+)', m)
        if not h or h.group(1) in seen:
            continue
        seen.add(h.group(1))
        dn = re.search(r'dn=([^&]+)', m)
        name = unquote(dn.group(1)) if dn else '?'
        out.append((h.group(1), name))
    return out

async def main():
    api = await add_magnets()
    for title, q in QUERIES.items():
        print(f'\n===== {title} =====')
        html = btdig_search(q)
        if not html:
            print('  搜索失败（限流）')
            continue
        for btih, name in parse_btdig(html)[:12]:
            tag = '🎬' if any(k in name for k in ['中字', '字幕', '国', '简繁', 'CHS', 'MiniHD', 'BTBTT']) else ''
            print(f'  {tag} {name[:90]}')
            print(f'    {btih}')
        time.sleep(15)
    print('DONE')

asyncio.run(main())

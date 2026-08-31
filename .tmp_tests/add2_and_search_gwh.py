#!/usr/bin/env python3
"""加放牛班/三傻中字磁链 + 补搜心灵捕手中字版"""
import asyncio, json, re, subprocess, sys, time
sys.path.insert(0, '/opt/data/.venv/lib/python3.13/site-packages')
from pikpakapi import PikPakApi
from urllib.parse import unquote

PROXY = 'http://127.0.0.1:10808'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'

MAGNETS = [
    ('放牛班的春天[60帧率版本][国语配音+中文字幕].Les.choristes.2004.2160p.IQY.WEB-DL.H265',
     'magnet:?xt=urn:btih:88eccace35cf385ebc995a74e18541132823b117'),
    ('三傻大闹宝莱坞[国英多音轨+中文字幕].3.Idiots.2009.BluRay.REMUX.1080p.AVC.DTS-HD.MA',
     'magnet:?xt=urn:btih:d9ee5d71115f7042ddd9c51af6888a68ef46e33a'),
]

QUERIES = ['Good Will Hunting 中文字幕', 'Good Will Hunting 国语 1080p']

async def add_magnets(api):
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

def btdig_search(q):
    url = 'https://btdig.com/search?q=' + q.replace(' ', '+')
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
    state = json.load(open('/opt/data/.pikpak_token.json'))
    api = PikPakApi.from_dict(state)
    await add_magnets(api)
    for q in QUERIES:
        print(f'\n===== 心灵捕手搜索: {q} =====')
        html = btdig_search(q)
        if not html:
            print('  搜索失败（限流）')
            time.sleep(15)
            continue
        for btih, name in parse_btdig(html)[:12]:
            tag = '🎬' if any(k in name for k in ['中字', '字幕', '国', '简繁', 'CHS', 'MiniHD', '国语']) else ''
            print(f'  {tag} {name[:90]}')
            print(f'    {btih}')
        time.sleep(15)
    print('DONE')

asyncio.run(main())

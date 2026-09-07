#!/usr/bin/env python3
"""搜知无涯者中字版磁链"""
import re, subprocess
from urllib.parse import unquote

PROXY = 'http://127.0.0.1:10808'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
Q = 'The Man Who Knew Infinity 中文字幕'

def run(url):
    r = subprocess.run(['curl', '-sL', '--max-time', '30', '-x', PROXY,
                        '-H', f'User-Agent: {UA}', url],
                       capture_output=True, text=True, timeout=40)
    return r.stdout

html = run('https://btdig.com/search?q=' + Q.replace(' ', '+'))
if len(html) < 2000:
    print('页面获取失败', len(html))
    exit()
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
    tag = '🎬中字' if any(k in name for k in ['中字', '字幕', '国', 'CHS', 'MiniHD', '国语', '简繁']) else ''
    print(f'{tag} {name[:95]}')
    print(f'  btih: {h.group(1)}')

#!/usr/bin/env python3
"""BTDigg 手动版：抓取 + dn 提取（每部间隔 12s 防限流）"""
import re, subprocess, time
from urllib.parse import unquote

PROXY = 'http://127.0.0.1:10808'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'

QUERIES = {
    '小鞋子': 'Children of Heaven 1997',
    '放牛班的春天': 'Les Choristes 2004',
    '心灵捕手': 'Good Will Hunting 1997',
    '三傻大闹宝莱坞': '3 Idiots 2009',
}

for title, q in QUERIES.items():
    print(f'\n===== {title} =====')
    url = 'https://btdig.com/search?q=' + q.replace(' ', '+')
    html = ''
    for attempt in range(3):
        r = subprocess.run(['curl', '-sL', '--max-time', '25', '-x', PROXY,
                            '-H', f'User-Agent: {UA}', url],
                           capture_output=True, text=True, timeout=35)
        html = r.stdout
        if len(html) > 3000:
            break
        print(f'  (重试 {attempt+1}, {len(html)}B)')
        time.sleep(12)
    if len(html) < 3000:
        print('  获取失败')
        time.sleep(12)
        continue
    mags = re.findall(r'href="(magnet:[^"]+)"', html)
    seen = set()
    for m in mags:
        m = m.replace('&amp;', '&')
        h = re.search(r'btih:([a-fA-F0-9]+)', m)
        if not h:
            continue
        btih = h.group(1)
        if btih in seen:
            continue
        seen.add(btih)
        dn = re.search(r'dn=([^&]+)', m)
        name = unquote(dn.group(1)) if dn else '?'
        tag = '🎬中字' if any(k in name for k in ['中字', '中文', 'CHS', '简中', '国语', '字幕', 'CHINESE', 'Chinese', '简繁']) else ''
        ctx = html[html.find(m):html.find(m)+600]
        sz = re.search(r'([\d.]+\s*[GMK]i?B)', ctx)
        print(f'  {tag} [{sz.group(1) if sz else "?"}] {name[:90]}')
    time.sleep(12)
print('\nDONE')

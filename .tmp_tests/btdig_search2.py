#!/usr/bin/env python3
"""BTDigg 搜索（dn= 提取文件名，限速友好）"""
import re, subprocess, time

PROXY = 'http://127.0.0.1:10808'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'

QUERIES = {
    '小鞋子': 'Children of Heaven 1997',
    '放牛班的春天': 'Les Choristes 2004',
    '摔跤吧！爸爸': 'Dangal 2016',
    '心灵捕手': 'Good Will Hunting 1997',
    '三傻大闹宝莱坞': '3 Idiots 2009',
}

def curl(url):
    for attempt in range(3):
        r = subprocess.run(['curl', '-sL', '--max-time', '25', '-x', PROXY,
                            '-H', f'User-Agent: {UA}', url],
                           capture_output=True, text=True, timeout=35)
        if len(r.stdout) > 2000:
            return r.stdout
        time.sleep(8)
    return r.stdout

def parse(html):
    results = []
    for m in re.finditer(r'href="(magnet:\?xt=urn:btih:[a-zA-Z0-9]+)[^"]*"', html):
        mag = m.group(1)
        # dn= 文件名
        dn = re.search(r'dn=([^&"]+)', mag)
        title = __import__('urllib.parse', fromlist=['unquote']).unquote(dn.group(1)) if dn else '?'
        ctx = html[m.start():m.start()+800]
        sz = re.search(r'([\d.]+\s*[GMK]i?B)', ctx)
        results.append((mag, title, sz.group(1) if sz else '?'))
    seen, out = set(), []
    for r in results:
        if r[0] not in seen:
            seen.add(r[0])
            out.append(r)
    return out

for title, q in QUERIES.items():
    print(f'\n===== {title} ({q}) =====')
    url = 'https://btdig.com/search?q=' + q.replace(' ', '+')
    html = curl(url)
    if len(html) < 2000:
        print('  获取失败（限流）')
        time.sleep(10)
        continue
    res = parse(html)
    if not res:
        print('  无结果')
        time.sleep(10)
        continue
    for mag, t, sz in res[:15]:
        tag = '🎬中字' if any(k in t for k in ['中字', '中文', 'CHS', '简中', '国语', '字幕', 'CHINESE', 'Chinese']) else ''
        print(f'  {tag} [{sz}] {t[:85]}')
    time.sleep(10)
print('\nDONE')

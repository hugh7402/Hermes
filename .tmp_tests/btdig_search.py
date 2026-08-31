#!/usr/bin/env python3
"""BTDigg 搜索 5 部电影，提取磁链+标题+大小，标注中字版"""
import re, subprocess

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
    r = subprocess.run(['curl', '-sL', '--max-time', '25', '-x', PROXY, '-H', f'User-Agent: {UA}', url],
                       capture_output=True, text=True, timeout=35)
    return r.stdout

def parse(html):
    """BTDigg 结果：<a href="magnet:...">title</a> ... <span class="torrent-size">..</span>"""
    results = []
    for m in re.finditer(r'href="(magnet:\?xt=urn:btih:[a-zA-Z0-9]+)[^"]*"[^>]*>(.*?)</a>.*?</li>', html, re.S):
        mag = m.group(1)
        title = re.sub(r'<[^>]+>', '', m.group(2)).strip()
        ctx = m.group(0)
        sz = re.search(r'([\d.]+\s*[GMK]i?B)', ctx)
        results.append((mag, title, sz.group(1) if sz else '?'))
    # 去重
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
    if len(html) < 1000:
        print('  页面获取失败')
        continue
    res = parse(html)
    if not res:
        print('  无结果')
        continue
    for mag, t, sz in res[:12]:
        tag = ''
        if any(k in t for k in ['中字', '中文', 'CHS', '简中', '国语', '字幕', 'Sub', 'sub']):
            tag = '🎬中字'
        print(f'  {tag} [{sz}] {t[:80]}')
        print(f'    {mag}')

#!/usr/bin/env python3
"""磁力熊批量搜索 5 部电影，抓磁链列表（名+大小）"""
import re, subprocess

PROXY = 'http://127.0.0.1:10808'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
BASE = 'https://www.cilixiong.org'

MOVIES = ['小鞋子', '放牛班的春天', '摔跤吧', '心灵捕手', '三傻大闹宝莱坞']

def curl(url, data=None):
    cmd = ['curl', '-sL', '--max-time', '25', '-x', PROXY, '-H', f'User-Agent: {UA}']
    if data:
        cmd += ['-H', 'Referer: ' + BASE + '/', '--data', data]
    cmd.append(url)
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=35)
    return r.stdout

for title in MOVIES:
    print(f'\n===== {title} =====')
    html = curl(f'{BASE}/e/search/index.php', f'classid=1,2&show=title&tempid=1&keyboard={title}')
    # 结果链接
    links = re.findall(r'href="/(movie|drama)/(\d+)\.html"[^>]*>\s*([^<]{0,40})', html)
    seen = set()
    for kind, mid, name in links:
        key = (kind, mid)
        if key in seen:
            continue
        seen.add(key)
        print(f'  [{kind}] /{kind}/{mid}.html {name.strip()}')

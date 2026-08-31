#!/usr/bin/env python3
"""抓取磁力熊 5 个电影页的磁链（名+大小）"""
import re, subprocess

PROXY = 'http://127.0.0.1:10808'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
BASE = 'https://www.cilixiong.org'

PAGES = {
    '小鞋子': '/movie/64.html',
    '放牛班的春天': '/movie/14.html',
    '摔跤吧！爸爸': '/movie/297.html',
    '心灵捕手': '/movie/78.html',
    '三傻大闹宝莱坞': '/movie/12.html',
}

def curl(url):
    r = subprocess.run(['curl', '-sL', '--max-time', '25', '-x', PROXY, '-H', f'User-Agent: {UA}', url],
                       capture_output=True, text=True, timeout=35)
    return r.stdout

for title, path in PAGES.items():
    print(f'\n===== {title} =====')
    html = curl(f'{BASE}{path}')
    # 磁链 + 相邻文本
    magnets = re.findall(r'<a[^>]*href="(magnet:\?xt=urn:btih:[a-zA-Z0-9]+)"[^>]*>([^<]{0,120})', html)
    seen = set()
    for mag, name in magnets:
        if mag in seen:
            continue
        seen.add(mag)
        # 找大小标注（磁链附近）
        idx = html.find(mag)
        ctx = html[max(0, idx-50):idx+len(mag)+300]
        sz = re.findall(r'(\d+(?:\.\d+)?\s*[GM]B)', ctx)
        tag = '中字' if any(k in name for k in ['中字', '中文', 'CHS', '简中', '国语', '字幕']) else ''
        print(f'  {mag[-20:]}... {tag} {sz[:2]} {name[:90]}')
    if not seen:
        print('  无磁链')

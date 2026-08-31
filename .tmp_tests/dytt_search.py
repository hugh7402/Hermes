#!/usr/bin/env python3
"""电影天堂搜索 5 部电影（GBK 编码），提取磁链"""
import re, subprocess

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
SEARCH_URL = 'https://www.dytt8899.com/e/search/index.php'
MOVIES = ['小鞋子', '放牛班的春天', '摔跤吧', '心灵捕手', '三傻大闹宝莱坞']

def gbk(s):
    return s.encode('gbk')

def search(title):
    r = subprocess.run(['curl', '-sL', '--max-time', '20',
                        '-H', f'User-Agent: {UA}',
                        '-H', 'Referer: https://www.dytt8899.com/',
                        '--data-urlencode', f'keyboard={title}',
                        SEARCH_URL], capture_output=True, timeout=30)
    html = r.stdout.decode('gbk', errors='replace')
    return html

for t in MOVIES:
    print(f'\n===== {t} =====')
    html = search(t)
    # 结果链接（Discuz 风格 html/href）
    links = re.findall(r'<a[^>]*href="([^"]+)"[^>]*>([^<]{0,60})</a>', html)
    seen = set()
    cnt = 0
    for href, name in links:
        name = name.strip()
        if not name or '首页' in name or '搜索' in name:
            continue
        if href.startswith('http') or href.startswith('/html'):
            key = href
            if key in seen:
                continue
            seen.add(key)
            print(f'  {href} | {name[:50]}')
            cnt += 1
            if cnt >= 8:
                break
    if cnt == 0:
        # 找"没有搜索到"提示
        if '没有搜索' in html or '不存在' in html:
            print('  无结果')
        else:
            print(f'  页面 {len(html)}B，未解析到链接')

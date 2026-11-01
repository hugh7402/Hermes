#!/usr/bin/env python3
"""批量补中文字幕：subtitlecat 搜索 → 详情页找 zh-CN/zh-TW → 下载 → 验证 → 改名入库
用法: python3 fetch_subs.py  （改 TARGETS 字典为 {番号: 目标srt文件名}）
2026-08-27 实战验证：IPZZ-901 929条 / JUR-837 981条 / CAWB-025 676条 / MIDA-693 308条
"""
import os, re, shutil, subprocess, sys, time

INBOX = '/opt/data/PikPak/Inbox-JAV'
SUB_BASE = 'https://www.subtitlecat.com'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'

# 番号 -> 目标字幕文件名（改成你的实际需求）
TARGETS = {}

def curl(url):
    r = subprocess.run(['curl', '-sL', '--max-time', '15', '-H', f'User-Agent: {UA}', url],
                       capture_output=True, text=True, timeout=25)
    return r.stdout

def search(code):
    html = curl(f'{SUB_BASE}/index.php?search={code}')
    items = re.findall(r'href\s*=\s*"([^"]*(?:/subs/|subs/)[^"]*)"[^>]*>([^<]+)</a>', html)
    results = []
    for link, name in items:
        name_c = name.strip()
        if code.upper() in name_c.upper() or code.lower() in name_c.lower():
            if not link.startswith('/'):
                link = '/' + link
            results.append((link, name_c))
    seen = set()
    uniq = []
    for l, n in results:
        if l not in seen:
            seen.add(l)
            uniq.append((l, n))
    return uniq

def find_srt_links(page):
    html = curl(f'{SUB_BASE}{page}')
    links = []
    for m in re.finditer(r'href\s*=\s*"(/subs/\d+/[^"]*\.srt)"', html):
        path = m.group(1)
        # 🚨 rsplit('/')[-1] 取文件名；rsplit('/')[1] 取的是目录号(如1640)，会导致语言判断全失败
        fname = path.rsplit('/')[-1].lower()
        ctx = html[max(0, m.start()-300):m.end()+100]
        score = 0
        if 'zh-cn' in fname: score = 3
        elif 'zh-tw' in fname: score = 2
        elif '-zh.' in fname: score = 1
        elif 'chinese (simplified)' in ctx: score = 3
        elif 'chinese (traditional)' in ctx: score = 2
        if score:
            links.append((score, f'{SUB_BASE}{path}', fname))
    links.sort(key=lambda x: -x[0])
    return links

def download(url, dest):
    r = subprocess.run(['curl', '-sL', '--max-time', '60', '-H', f'User-Agent: {UA}', '-o', dest, url],
                       capture_output=True, text=True, timeout=80)
    return r.returncode == 0

def check_srt(path):
    try:
        with open(path, 'rb') as f:
            data = f.read()
    except Exception:
        return 0, 'read_fail'
    if not data:
        return 0, 'empty'
    if b'\x00' in data:
        return 0, 'binary'
    txt = None
    for enc in ('utf-8', 'gbk', 'latin-1'):
        try:
            txt = data.decode(enc)
            break
        except Exception:
            continue
    if txt is None:
        return 0, 'decode_fail'
    count = len(re.findall(r'^\d+\s*$', txt, re.M))
    bad = len(re.findall(r'锟斤拷|�', txt))
    return count, f'bad={bad}'

for code, target in TARGETS.items():
    dest = os.path.join(INBOX, target)
    if os.path.exists(dest) and os.path.getsize(dest) > 500:
        print(f'⏭️ {code}: 字幕已存在，跳过')
        continue
    print(f'\n=== {code} ===')
    items = search(code)
    if not items:
        print(f'  ❌ subtitlecat 无搜索结果')
        continue
    print(f'  搜索到 {len(items)} 个条目')
    got = False
    for page, name in items:
        print(f'  检查条目: {name[:60]}')
        links = find_srt_links(page)
        if not links:
            print(f'    无中文字幕链接')
            continue
        for score, url, fname in links[:3]:
            tmp = f'/tmp/{code}_sub.srt'
            ok = download(url, tmp)
            if not ok or not os.path.exists(tmp):
                continue
            count, note = check_srt(tmp)
            print(f'    下载 {fname}: {count} 条 ({note})')
            if count >= 100 and 'bad=0' in note:
                # 🚨 /tmp 与 /opt/data 跨设备，os.rename 报 Errno 18，必须 shutil.move
                shutil.move(tmp, dest)
                print(f'  ✅ {code} 字幕完成: {target[:50]}... ({count} 条)')
                got = True
                break
            else:
                os.remove(tmp)
        if got:
            break
    if not got:
        print(f'  ❌ {code}: 未能获取合格中文字幕')
    time.sleep(1)

print('\nALL_DONE')

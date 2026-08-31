#!/usr/bin/env python3
"""检查 4 个新字幕文件内容质量"""
import os, re

INBOX = '/opt/data/PikPak/Inbox-JAV'
names = ['IPZZ-901', 'JUR-837', 'CAWB-025', 'MIDA-693']
for n in names:
    for fn in os.listdir(INBOX):
        if fn.startswith(n) and fn.endswith('.srt'):
            fp = os.path.join(INBOX, fn)
            with open(fp, 'rb') as f:
                data = f.read()
            txt = data.decode('utf-8', errors='replace')
            count = len(re.findall(r'^\d+\s*$', txt, re.M))
            # 取前3条字幕文本
            blocks = re.findall(r'\d+\s*\n(\d\d:\d\d:\d\d[^\n]*)\n([^\n]+)', txt)
            sample = blocks[2][1][:50] if len(blocks) > 2 else 'N/A'
            print(f'{n}: {len(data)}B {count}条 样例: {sample}')
            break
    else:
        print(f'{n}: 未找到')

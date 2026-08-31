#!/usr/bin/env python3
"""核对今日 13 个番号的字幕状态"""
import os

INBOX = '/opt/data/PikPak/Inbox-JAV'
today = ['HMN-896', 'IPZZ-925', 'JUR-794', 'GARA-025', 'IPZZ-901', 'IPZZ-914',
         'JUR-837', 'DLDSS-525', 'JUFE-628', 'CAWB-025', 'DVMM-415', 'IPZZ-879', 'MIDA-693']

subs = {}
for fn in os.listdir(INBOX):
    if fn.endswith('.srt'):
        subs[fn] = os.path.getsize(os.path.join(INBOX, fn))

print('今日番号字幕状态:')
for code in today:
    found = [f'{n} ({s//1024}KB)' for n, s in subs.items() if n.startswith(code)]
    if found:
        print(f'  ✅ {code}: {found}')
    else:
        print(f'  ❌ {code}: 无外挂字幕')
print(f'\nInbox-JAV 共 {len(subs)} 个 srt')

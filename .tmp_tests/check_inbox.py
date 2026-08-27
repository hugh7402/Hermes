#!/usr/bin/env python3
"""检查 Inbox-JAV 文件状态，删除残留旧文件（IPZZ-901-中文字幕/JUR-837-中文字幕）"""
import asyncio, json, sys
sys.path.insert(0, '/opt/data/.venv/lib/python3.13/site-packages')
from pikpakapi import PikPakApi

async def main():
    state = json.load(open('/opt/data/.pikpak_token.json'))
    api = PikPakApi.from_dict(state)
    result = await api.path_to_id('/Inbox-JAV')
    inbox_id = result[0]['id'] if isinstance(result, list) else result

    ls = await api.file_list(parent_id=inbox_id, size=100)
    files = ls.get('files', [])
    print('Inbox-JAV 内容:')
    for f in files:
        kind = f.get('kind', '?')
        name = f.get('name', '?')
        size = int(f.get('size', 0))
        phase = f.get('phase', '')
        ftype = '📁' if kind == 'drive#folder' else '📄'
        print(f'  {ftype} {name}  {size/1024**3:.2f}GB  phase={phase}')

    # 删除残留旧字幕版
    to_del = []
    for f in files:
        n = f.get('name', '')
        if f.get('kind') == 'drive#folder':
            continue
        if 'IPZZ-901-中文字幕' in n or 'JUR-837-中文字幕' in n:
            to_del.append(f['id'])
            print(f'🗑️ 删除残留: {n}')
    if to_del:
        await api.delete_to_trash(to_del)
        print(f'已删除 {len(to_del)} 个残留文件')
    else:
        print('无残留')

    print('DONE')

asyncio.run(main())

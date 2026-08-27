#!/usr/bin/env python3
"""修正 3 个番号的磁链选择：删错误文件，加正确磁链"""
import asyncio, json, sys
sys.path.insert(0, '/opt/data/.venv/lib/python3.13/site-packages')
from pikpakapi import PikPakApi

MAGNETS = {
    'IPZZ-901-U.无码破解.torrent': 'magnet:?xt=urn:btih:43e8f4594ad00784ed9eaed98bc756e0bdf6010e&dn=[javdb.com]IPZZ-901-U.无码破解.torrent',
    'jufe-628': 'magnet:?xt=urn:btih:99a266ab33a2a83db2c7c959bbc40886325d880a&dn=[javdb.com]jufe-628',
    'jur-837': 'magnet:?xt=urn:btih:c63d8794834fd6c763be5ae7191ad528b9983210&dn=[javdb.com]jur-837',
}
DEL_PATTERNS = ['IPZZ-901-中文字幕', 'JUFE-628-U', 'JUR-837-中文字幕']

async def main():
    state = json.load(open('/opt/data/.pikpak_token.json'))
    api = PikPakApi.from_dict(state)
    result = await api.path_to_id('/Inbox-JAV')
    inbox_id = result[0]['id'] if isinstance(result, list) else result
    print(f'Inbox-JAV id: {inbox_id}')

    # 列出当前文件
    ls = await api.file_list(parent_id=inbox_id, size=100)
    files = [f for f in ls.get('files', []) if f.get('kind') == 'drive#file']
    print('当前 Inbox-JAV 文件:')
    for f in files:
        print(f"  {f['name']}  {int(f.get('size',0))/1024**3:.2f}GB")

    # 删除错误文件
    to_del = [f['id'] for f in files if any(p.upper() in f['name'].upper() for p in DEL_PATTERNS)]
    if to_del:
        for fid in to_del:
            name = next(f['name'] for f in files if f['id'] == fid)
            print(f'🗑️ 删除: {name}')
        await api.delete_to_trash(to_del)
        print(f'已删除 {len(to_del)} 个文件')

    # 添加正确磁链
    for name, mag in MAGNETS.items():
        print(f'➕ 添加: {name}')
        task = await api.offline_download(mag, parent_id=inbox_id)
        print(f'   task_id: {task.get("task_id", "?")}')

    print('DONE')

asyncio.run(main())

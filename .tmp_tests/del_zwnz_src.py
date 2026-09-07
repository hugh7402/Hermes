#!/usr/bin/env python3
"""删知无涯者 PikPak 云端源（本地已入库验证）"""
import asyncio, json, sys
sys.path.insert(0, '/opt/data/.venv/lib/python3.13/site-packages')
from pikpakapi import PikPakApi

async def main():
    state = json.load(open('/opt/data/.pikpak_token.json'))
    api = PikPakApi.from_dict(state)
    ls = await api.file_list(parent_id='', size=100)
    movie_id = None
    for f in ls.get('files', []):
        if f.get('kind') == 'drive#folder' and f['name'] == 'Movie':
            movie_id = f['id']
            break
    ls2 = await api.file_list(parent_id=movie_id, size=100)
    for f in ls2.get('files', []):
        if f.get('kind') == 'drive#file' and 'ParkHD' in f.get('name', ''):
            print(f'🗑️ 删云端: {f["name"][:50]} ({int(f.get("size",0))/2**30:.2f}G)')
            await api.delete_to_trash([f['id']])
            print('✅ 已删')
            break
    print('DONE')

asyncio.run(main())

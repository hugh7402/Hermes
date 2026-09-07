#!/usr/bin/env python3
"""处理知无涯者文件夹：移出视频→删广告→验证→删空文件夹"""
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
    folder = None
    for f in ls2.get('files', []):
        if f.get('kind') == 'drive#folder' and '知无涯者' in f.get('name', ''):
            folder = f
            break
    if not folder:
        print('❌ 未找到知无涯者文件夹')
        return

    flist = await api.file_list(parent_id=folder['id'], size=100)
    items = flist.get('files', [])
    vids = [f for f in items if f.get('kind') == 'drive#file'
            and f['name'].lower().endswith(('.mp4', '.mkv')) and int(f.get('size', 0)) > 100 * 1024 * 1024]
    ads = [f for f in items if f.get('kind') == 'drive#file' and f not in vids]

    for v in vids:
        print(f'📄 视频: {v["name"][:60]} {int(v["size"])/2**30:.2f}G')
    if ads:
        print(f'🗑️ 广告 {len(ads)} 个')
        await api.delete_to_trash([a['id'] for a in ads])
    for v in vids:
        print(f'📤 移出: {v["name"][:40]}')
        await api.file_batch_move([v['id']], movie_id)
    await asyncio.sleep(3)
    ls3 = await api.file_list(parent_id=movie_id, size=100)
    root_names = [f['name'] for f in ls3.get('files', [])]
    if all(v['name'] in root_names for v in vids):
        print('✅ 视频已在根目录，删文件夹')
        await api.delete_to_trash([folder['id']])
    else:
        print('⚠️ 移出未确认，暂不删文件夹')
    print('DONE')

asyncio.run(main())

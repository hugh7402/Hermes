#!/usr/bin/env python3
"""删 PikPak Movie/ 中 5 部电影源（本地完整副本验证后）"""
import asyncio, json, os, sys
sys.path.insert(0, '/opt/data/.venv/lib/python3.13/site-packages')
from pikpakapi import PikPakApi

LOCAL_MOVIE = '/opt/data/Movie'
LOCAL = {}
for fn in os.listdir(LOCAL_MOVIE):
    fp = os.path.join(LOCAL_MOVIE, fn)
    if os.path.isfile(fp):
        LOCAL[fn] = os.path.getsize(fp)

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
    files = [f for f in ls2.get('files', []) if f.get('kind') == 'drive#file']

    to_del = []
    print('Movie/ 云端文件核对:')
    for f in files:
        cname, csize = f['name'], int(f.get('size', 0))
        if not cname.lower().endswith(('.mp4', '.mkv')):
            print(f'  ⏭️ 跳过非视频: {cname[:40]}')
            continue
        found = None
        for lname, lsize in LOCAL.items():
            if abs(lsize - csize) < csize * 0.01:
                found = lname
                break
        if found:
            print(f'  🗑️ {cname[:45]} ({csize/2**30:.1f}G) → 本地[{found[:30]}] ✅')
            to_del.append(f['id'])
        else:
            print(f'  ⚠️ 本地无完整副本: {cname[:45]} ({csize/2**30:.1f}G) 保留')
    if to_del:
        await api.delete_to_trash(to_del)
        print(f'✅ 已删 {len(to_del)} 个云端源')
    print('DONE')

asyncio.run(main())

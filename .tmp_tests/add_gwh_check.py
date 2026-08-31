#!/usr/bin/env python3
"""加心灵捕手中字磁链 + 检查 5 部电影离线状态"""
import asyncio, json, sys
sys.path.insert(0, '/opt/data/.venv/lib/python3.13/site-packages')
from pikpakapi import PikPakApi

MAGNET = ('心灵捕手[国英多音轨+中文字幕].Good.Will.Hunting.1997.BluRay.1080p.HEVC.10bit',
          'magnet:?xt=urn:btih:c6aad011087997ee38af026350d2ae6fabdb26a1')

async def main():
    state = json.load(open('/opt/data/.pikpak_token.json'))
    api = PikPakApi.from_dict(state)
    ls = await api.file_list(parent_id='', size=100)
    movie_id = None
    for f in ls.get('files', []):
        if f.get('kind') == 'drive#folder' and f['name'] == 'Movie':
            movie_id = f['id']
            break
    name, mag = MAGNET
    print(f'➕ {name}')
    task = await api.offline_download(mag, parent_id=movie_id)
    print(f'  task: {task.get("task", {}).get("id", "?")}')

    # 等几秒后检查 Movie/ 内容
    await asyncio.sleep(8)
    ls2 = await api.file_list(parent_id=movie_id, size=100)
    print(f'\nMovie/ 当前内容:')
    for f in ls2.get('files', []):
        sz = int(f.get('size', 0))
        print(f'  {"📁" if f.get("kind")=="drive#folder" else "📄"} {f["name"][:60]} {sz/2**30:.2f}G phase={f.get("phase", "?")}')
    print('DONE')

asyncio.run(main())

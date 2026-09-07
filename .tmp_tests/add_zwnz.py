#!/usr/bin/env python3
"""添加知无涯者中字磁链到 PikPak Movie/"""
import asyncio, json, sys, time
sys.path.insert(0, '/opt/data/.venv/lib/python3.13/site-packages')
from pikpakapi import PikPakApi

MAGNET = ('知无涯者[中文字幕].The.Man.Who.Knew.Infinity.2015.1080p.WEB-DL.AAC.H264-ParkHD',
          'magnet:?xt=urn:btih:086600289bbbe1e3b5b5a9ead6eccefb6750bf77')

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
    # 轮询直到文件夹出现
    print('等待离线...')
    for i in range(20):
        await asyncio.sleep(15)
        ls2 = await api.file_list(parent_id=movie_id, size=100)
        for f in ls2.get('files', []):
            if f.get('kind') == 'drive#folder' and '知无涯者' in f.get('name', ''):
                print(f'  📁 文件夹出现: {f["name"][:40]} phase={f.get("phase")}')
                fl = await api.file_list(parent_id=f['id'], size=100)
                for sub in fl.get('files', []):
                    print(f'    📄 {sub["name"][:50]} {int(sub.get("size",0))/2**30:.2f}G phase={sub.get("phase")}')
                print('FOLDER_READY')
                return
    print('TIMEOUT_NO_FOLDER')
    print('DONE')

asyncio.run(main())

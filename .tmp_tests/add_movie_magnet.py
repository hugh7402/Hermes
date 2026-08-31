#!/usr/bin/env python3
"""添加电影磁链到 PikPak Movie/ 文件夹"""
import asyncio, json, sys
sys.path.insert(0, '/opt/data/.venv/lib/python3.13/site-packages')
from pikpakapi import PikPakApi

MAGNETS = [
    ('摔跤吧！爸爸.2016.1080p.简繁中字￡CMCT梦幻.12GB',
     'magnet:?xt=urn:btih:e2d8296830eae241be1488b24e3588a54315d150'),
]

async def main():
    state = json.load(open('/opt/data/.pikpak_token.json'))
    api = PikPakApi.from_dict(state)
    # 找 Movie/ 文件夹（根目录列出）
    ls = await api.file_list(parent_id='', size=100)
    movie_id = None
    for f in ls.get('files', []):
        if f.get('kind') == 'drive#folder' and f['name'] == 'Movie':
            movie_id = f['id']
            break
    if not movie_id:
        # 创建 Movie 文件夹
        movie_id = await api.create_folder('Movie', '')
        print(f'创建 Movie/: {movie_id}')
    else:
        print(f'Movie/ id: {movie_id}')

    for name, mag in MAGNETS:
        print(f'➕ {name}')
        task = await api.offline_download(mag, parent_id=movie_id)
        print(f'  task: {task.get("task", {}).get("id", "?")}')
    print('DONE')

asyncio.run(main())

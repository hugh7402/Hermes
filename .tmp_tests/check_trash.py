#!/usr/bin/env python3
"""查 PikPak 回收站，尝试恢复 JUR-837"""
import asyncio, json, sys
sys.path.insert(0, '/opt/data/.venv/lib/python3.13/site-packages')
import aiohttp
from pikpakapi import PikPakApi

async def main():
    state = json.load(open('/opt/data/.pikpak_token.json'))
    api = PikPakApi.from_dict(state)
    # 确保 token 有效
    try:
        await api.file_list(size=1)
    except Exception as e:
        print(f'token 刷新: {e}')
    token = api.access_token

    # 查回收站
    headers = {'Authorization': f'Bearer {token}'}
    proxy = 'http://127.0.0.1:10808'
    async with aiohttp.ClientSession() as s:
        # 回收站列表
        async with s.get('https://api-drive.mypikpak.com/drive/v1/files/trash?limit=100',
                         headers=headers, proxy=proxy, timeout=30) as r:
            print(f'回收站 HTTP {r.status}')
            if r.status == 200:
                data = await r.json()
                for f in data.get('files', []):
                    print(f"  {f['name']}  {int(f.get('size',0))/1024**3:.2f}GB  id={f['id']}")
            else:
                print(await r.text())
    print('DONE')

asyncio.run(main())

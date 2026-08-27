#!/usr/bin/env python3
"""查 Inbox-JAV 所有文件（pikpakapi 权威状态）"""
import asyncio, json, sys
sys.path.insert(0, '/opt/data/.venv/lib/python3.13/site-packages')
from pikpakapi import PikPakApi

async def main():
    state = json.load(open('/opt/data/.pikpak_token.json'))
    api = PikPakApi.from_dict(state)
    result = await api.path_to_id('/Inbox-JAV')
    inbox_id = result[0]['id'] if isinstance(result, list) else result
    ls = await api.file_list(parent_id=inbox_id, size=100)
    for f in ls.get('files', []):
        kind = '📁' if f.get('kind') == 'drive#folder' else '📄'
        print(f"{kind} {f['name']}  {int(f.get('size',0))/1024**3:.2f}GB  phase={f.get('phase','')}")
    print('DONE')

asyncio.run(main())

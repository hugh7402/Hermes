import json, asyncio
from pikpakapi import PikPakApi

async def run():
    token = json.load(open('/opt/data/.pikpak_token.json'))
    c = PikPakApi(encoded_token=token['encoded_token'])
    c.access_token = token['access_token']; c.refresh_token = token['refresh_token']
    c.user_id = token['user_id']; c.device_id = token['device_id']
    raw = await c.offline_list()
    print('返回类型:', type(raw).__name__)
    if isinstance(raw, dict):
        print('键:', list(raw.keys()))
        tasks = raw.get('tasks') or raw.get('data', {}).get('tasks') or []
    else:
        tasks = raw
    print('任务数:', len(tasks) if tasks else 0)
    for t in (tasks or []):
        n = t.get('name','')
        if any(k in n for k in ['碟中谍','Mission','MI8','Impossible']):
            sz = int(t.get('file_size') or 0)/1024**3
            print(f"  ★ {n[:75]} | {t.get('phase')} | {t.get('progress')}% | {sz:.2f}GB")
    print('--- 全部任务(前6) ---')
    for t in (tasks or [])[:6]:
        sz = int(t.get('file_size') or 0)/1024**3
        print(f"  {t.get('name','')[:65]} | {t.get('phase')} | {t.get('progress')}% | {sz:.2f}GB")

asyncio.run(run())

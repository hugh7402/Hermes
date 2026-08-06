"""心灵猎人第一季 10 集 → PikPak Inbox-JAV 离线 + 取 CDN 直链"""
import json, asyncio, sys
from pikpakapi import PikPakApi

async def run():
    token = json.load(open('/opt/data/.pikpak_token.json'))
    client = PikPakApi(encoded_token=token['encoded_token'])
    client.access_token = token['access_token']
    client.refresh_token = token['refresh_token']
    client.user_id = token['user_id']
    client.device_id = token['device_id']

    r = await client.path_to_id('/Inbox-JAV')
    inbox_id = r[0]['id']
    print(f'Inbox-JAV id: {inbox_id}')

    magnets = json.load(open('/tmp/xllr_magnets.json'))
    print(f'共 {len(magnets)} 集，添加到 PikPak...')

    ok, fail = 0, []
    for name, url in magnets.items():
        try:
            await client.offline_download(url, parent_id=inbox_id)
            print(f'  ✅ {name}')
            ok += 1
            await asyncio.sleep(1.5)
        except Exception as e:
            print(f'  ❌ {name}: {str(e)[:60]}')
            fail.append(name)

    print(f'\n添加完成: 成功 {ok}, 失败 {len(fail)}')
    if fail:
        print('失败:', fail)

asyncio.run(run())

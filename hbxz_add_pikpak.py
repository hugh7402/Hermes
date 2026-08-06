"""护宝寻踪 36 集 → PikPak Inbox-JAV 离线下载"""
import json, asyncio, sys
from pikpakapi import PikPakApi

async def run():
    token = json.load(open('/opt/data/.pikpak_token.json'))
    client = PikPakApi(encoded_token=token['encoded_token'])
    client.access_token = token['access_token']
    client.refresh_token = token['refresh_token']
    client.user_id = token['user_id']
    client.device_id = token['device_id']

    # 动态取 Inbox-JAV folder id
    r = await client.path_to_id('/Inbox-JAV')
    inbox_id = r[0]['id']
    print(f'Inbox-JAV id: {inbox_id}')

    magnets = json.load(open('/tmp/hbxz_magnets.json'))
    print(f'共 {len(magnets)} 集，开始添加到 PikPak...')

    ok, fail = 0, []
    for name, url in magnets.items():
        try:
            task = await client.offline_download(url, parent_id=inbox_id)
            print(f'  ✅ {name} 已添加 (task={task.get("task_id","?")[:12]}...)')
            ok += 1
            await asyncio.sleep(1.5)  # 避免限频
        except Exception as e:
            print(f'  ❌ {name} 失败: {str(e)[:80]}')
            fail.append(name)

    print(f'\n完成: 成功 {ok} 个, 失败 {len(fail)} 个')
    if fail:
        print('失败列表:', fail)

asyncio.run(run())

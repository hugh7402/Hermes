"""轮询 PikPak 离线状态 + 检查 Inbox-JAV 内部文件"""
import json, asyncio, sys
from pikpakapi import PikPakApi

async def run():
    token = json.load(open('/opt/data/.pikpak_token.json'))
    client = PikPakApi(encoded_token=token['encoded_token'])
    client.access_token = token['access_token']
    client.refresh_token = token['refresh_token']
    client.user_id = token['user_id']
    client.device_id = token['device_id']

    # 离线任务状态
    print('=== 离线任务 ===')
    try:
        tasks = await client.offline_list()
        for t in tasks.get('tasks', []):
            name = t.get('name', '?')
            if '黑钱' in name or 'Ozark' in name or '47BT' in name or '47bt' in name:
                size_mb = int(t.get('file_size') or 0) / 1024 / 1024
                print(f'  {name[:70]}')
                print(f'    状态={t.get("phase")} 进度={t.get("progress")}% 大小={size_mb:.0f}MB')
    except Exception as e:
        print('  查询失败:', str(e)[:100])

    # Inbox-JAV 文件
    print('=== Inbox-JAV 文件 ===')
    r = await client.path_to_id('/Inbox-JAV')
    inbox_id = r[0]['id']
    files = await client.file_list(parent_id=inbox_id)
    for f in files.get('files', []):
        n = f.get('name', '')
        if '黑' in n or 'Ozark' in n or '47BT' in n.upper():
            size_gb = int(f.get('size') or 0) / 1024**3
            print(f'  [{f.get("kind")}] {n[:70]} | {size_gb:.2f}GB | id={f.get("id")}')
            if f.get('kind') == 'drive#folder':
                sub = await client.file_list(parent_id=f['id'])
                for s in sub.get('files', []):
                    sz = int(s.get('size') or 0) / 1024**3
                    print(f'      └ {s.get("name")[:75]} | {sz:.2f}GB')

asyncio.run(run())

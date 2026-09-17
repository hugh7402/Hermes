"""删除繁体名 720p 备选版（保留 47BT 4K 版）"""
import json, asyncio
from pikpakapi import PikPakApi

TARGET_FOLDER_ID = 'VP1ZUpCEAQSO3Bf0LFwz1uVlo2'   # 黑錢勝地 第一季 (2017) 8.3

async def run():
    token = json.load(open('/opt/data/.pikpak_token.json'))
    client = PikPakApi(encoded_token=token['encoded_token'])
    client.access_token = token['access_token']
    client.refresh_token = token['refresh_token']
    client.user_id = token['user_id']
    client.device_id = token['device_id']

    # 删文件夹（含内部文件）
    try:
        await client.delete([TARGET_FOLDER_ID])
        print('✅ 已删文件夹: 黑錢勝地 第一季 (720p 备选)')
    except Exception as e:
        print('❌ 删文件夹失败:', str(e)[:100])

    # 删对应离线任务
    try:
        tasks = await client.offline_list()
        for t in tasks.get('tasks', []):
            if '黑錢勝地' in t.get('name', ''):
                await client.delete_tasks([t['id']])
                print(f'✅ 已删离线任务: {t.get("name")[:50]}')
    except Exception as e:
        print('删任务失败(可忽略):', str(e)[:80])

    # 确认 47BT 版文件列表
    print('=== 47BT 4K 版确认 ===')
    r = await client.path_to_id('/Inbox-JAV')
    files = await client.file_list(parent_id=r[0]['id'])
    for f in files.get('files', []):
        if '47BT' in f.get('name', '').upper():
            sub = await client.file_list(parent_id=f['id'])
            total = 0
            for s in sub.get('files', []):
                gb = int(s.get('size') or 0) / 1024**3
                if s.get('kind') == 'drive#file':
                    total += gb
            print(f'  文件夹: {f.get("name")}')
            print(f'  总大小: {total:.2f} GB, 文件数: {len(sub.get("files", []))}')

asyncio.run(run())

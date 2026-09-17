"""黑钱胜地 S02 → PikPak 离线（47BT 2160p 中字版，hash 来自上轮 BTDigg 搜索）"""
import json, asyncio
from pikpakapi import PikPakApi

MAGNETS = {
    "黑钱胜地_第二季_47BT_2160p": "magnet:?xt=urn:btih:92b56997f90d49e92abf854413e823be92959c1f&dn=%5B47BT%5D%5B%E9%BB%91%E9%92%B1%E8%83%9C%E5%9C%B0%20%E7%AC%AC%E4%BA%8C%E5%AD%A3%5DOzark.S02.2160p.10Bit.WEB-DL.HEVC.AAC&tr=udp%3A%2F%2Ftracker.openbittorrent.com%3A80&tr=udp%3A%2F%2Ftracker.opentrackr.org%3A1337%2Fannounce",
}

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

    for name, url in MAGNETS.items():
        try:
            await client.offline_download(url, parent_id=inbox_id)
            print(f'  ✅ {name} 已添加离线')
        except Exception as e:
            print(f'  ❌ {name} 失败: {str(e)[:120]}')
        await asyncio.sleep(2)

    await asyncio.sleep(10)
    print('=== 离线任务状态 ===')
    try:
        tasks = await client.offline_list()
        for t in tasks.get('tasks', []):
            n = t.get('name', '')
            if '黑钱' in n or 'Ozark' in n:
                sz = int(t.get('file_size') or 0) / 1024**3
                print(f'  {n[:60]} | {t.get("phase")} | {t.get("progress")}% | {sz:.2f}GB')
    except Exception as e:
        print('  查询失败:', str(e)[:80])

asyncio.run(run())

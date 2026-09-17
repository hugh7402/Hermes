"""黑钱胜地 S01 → PikPak 离线（47BT 2160p 中字版 + 繁体名版备选）"""
import json, asyncio
from pikpakapi import PikPakApi

MAGNETS = {
    "47BT_2160p_中字": "magnet:?xt=urn:btih:139240d4f30a1fcc8340dddc7a22ccf2bc910fab&dn=%5B47BT%5D%5B%E9%BB%91%E9%92%B1%E8%83%9C%E5%9C%B0%20%E7%AC%AC%E4%B8%80%E5%AD%A3%5DOzark.S01.2160p.WEB-DL.HEVC.AAC&tr=udp%3A%2F%2Ftracker.openbittorrent.com%3A80&tr=udp%3A%2F%2Ftracker.opentrackr.org%3A1337%2Fannounce",
    "繁中名_第一季": "magnet:?xt=urn:btih:2f403825de2d9a920078edb72d0e48c31dc11a98&dn=%E9%BB%91%E9%8C%A2%E5%8B%9D%E5%9C%B0%20%E7%AC%AC%E4%B8%80%E5%AD%A3%20Ozark%20Season%201%20(2017)%208.3&tr=udp%3A%2F%2Ftracker.openbittorrent.com%3A80&tr=udp%3A%2F%2Ftracker.opentrackr.org%3A1337%2Fannounce",
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
            task = await client.offline_download(url, parent_id=inbox_id)
            print(f'  ✅ {name} 已添加 (task={str(task.get("task_id","?"))[:14]})')
        except Exception as e:
            print(f'  ❌ {name} 失败: {str(e)[:100]}')
        await asyncio.sleep(2)

    # 立即查离线任务状态
    await asyncio.sleep(8)
    try:
        tasks = await client.offline_list()
        for t in tasks.get('tasks', []):
            print(f'  任务: {t.get("name","?")[:60]} | 状态={t.get("phase")} | 进度={t.get("progress")} | 大小={t.get("file_size")}')
    except Exception as e:
        print('  查询任务失败:', str(e)[:80])

asyncio.run(run())

#!/usr/bin/env python3
"""重新离线 JUR-837 并正确处理：添加磁链 → 等离线 → 移出(验证) → 重命名 → 删文件夹"""
import asyncio, json, sys, re, time
sys.path.insert(0, '/opt/data/.venv/lib/python3.13/site-packages')
from pikpakapi import PikPakApi

MAGNET = 'magnet:?xt=urn:btih:c63d8794834fd6c763be5ae7191ad528b9983210&dn=[javdb.com]jur-837'
VIDEO_EXT = ('.mp4', '.mkv', '.avi', '.wmv', '.mov', '.flv', '.ts', '.m4v', '.webm')

async def main():
    state = json.load(open('/opt/data/.pikpak_token.json'))
    api = PikPakApi.from_dict(state)
    result = await api.path_to_id('/Inbox-JAV')
    inbox_id = result[0]['id'] if isinstance(result, list) else result

    # 添加磁链
    print('➕ 添加磁链 jur-837')
    task = await api.offline_download(MAGNET, parent_id=inbox_id)
    print(f'  task: {task}')

    # 等待文件夹出现并完成
    folder_id = None
    for i in range(30):
        await asyncio.sleep(5)
        ls = await api.file_list(parent_id=inbox_id, size=100)
        for f in ls.get('files', []):
            if f.get('kind') == 'drive#folder' and 'jur-837' in f['name'].lower():
                folder_id = f['id']
                break
        if folder_id:
            print(f'  ✅ 文件夹出现 ({i*5}s): {folder_id}')
            break
    if not folder_id:
        print('❌ 30s 内未出现文件夹')
        return

    # 等子文件 COMPLETE
    video = None
    for i in range(36):  # 最多 3 分钟
        await asyncio.sleep(5)
        sub = await api.file_list(parent_id=folder_id, size=100)
        subs = sub.get('files', [])
        videos = [s for s in subs if s.get('name', '').lower().endswith(VIDEO_EXT)]
        if videos:
            all_complete = all(s.get('phase') == 'PHASE_TYPE_COMPLETE' for s in subs)
            if all_complete:
                video = max(videos, key=lambda s: int(s.get('size', 0)))
                print(f'  ✅ 视频就绪: {video["name"]} ({int(video["size"])/1024**3:.2f}GB)')
                break
        if i % 6 == 0:
            print(f'  等待离线... {i*5}s')

    if not video:
        print('❌ 3 分钟内视频未就绪')
        return

    # 删广告（非视频）
    ads = [s for s in subs if s['id'] != video['id']]
    if ads:
        for a in ads:
            print(f'  🗑️ 广告: {a["name"]}')
        await api.delete_to_trash([a['id'] for a in ads])

    # 移出（⚠️ batchMove 异步，必须验证）
    print(f'  📤 移出: {video["name"]}')
    await api.file_batch_move([video['id']], inbox_id)
    moved = False
    for i in range(10):  # 最多 30s 验证
        await asyncio.sleep(3)
        root = await api.file_list(parent_id=inbox_id, size=100)
        if any(f['id'] == video['id'] for f in root.get('files', [])):
            moved = True
            print(f'  ✅ 已确认在 Inbox-JAV 根目录 ({i*3}s)')
            break
        sub2 = await api.file_list(parent_id=folder_id, size=100)
        if not any(f['id'] == video['id'] for f in sub2.get('files', [])):
            print(f'  ⚠️ 文件夹里已没有视频，但根目录也没找到，再等')
    if not moved:
        print('❌ 移出未确认，中止（不删文件夹）')
        return

    # 重命名
    await api.file_rename(video['id'], 'JUR-837.mp4')
    print('  ✅ 重命名 → JUR-837.mp4')

    # 最后删空文件夹（此时视频已确认在根目录）
    sub3 = await api.file_list(parent_id=folder_id, size=100)
    remaining = sub3.get('files', [])
    if remaining:
        print(f'  ⚠️ 文件夹还有 {len(remaining)} 个文件，不删')
    else:
        await api.delete_to_trash([folder_id])
        print('  ✅ 空文件夹已删除')
    print('DONE')

asyncio.run(main())

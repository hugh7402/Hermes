#!/usr/bin/env python3
"""处理 5 个电影文件夹：移出视频→删广告→验证→删空文件夹"""
import asyncio, json, sys
sys.path.insert(0, '/opt/data/.venv/lib/python3.13/site-packages')
from pikpakapi import PikPakApi

async def main():
    state = json.load(open('/opt/data/.pikpak_token.json'))
    api = PikPakApi.from_dict(state)
    ls = await api.file_list(parent_id='', size=100)
    movie_id = None
    for f in ls.get('files', []):
        if f.get('kind') == 'drive#folder' and f['name'] == 'Movie':
            movie_id = f['id']
            break

    ls2 = await api.file_list(parent_id=movie_id, size=100)
    folders = [f for f in ls2.get('files', []) if f.get('kind') == 'drive#folder'
               and any(k in f['name'] for k in ['心灵捕手', '三傻', '放牛班', '小鞋子', '摔跤吧'])]
    print(f'找到 {len(folders)} 个电影文件夹')

    for folder in folders:
        fname = folder['name'][:50]
        print(f'\n=== {fname} ===')
        flist = await api.file_list(parent_id=folder['id'], size=100)
        items = flist.get('files', [])
        vids = [f for f in items if f.get('kind') == 'drive#file'
                and f['name'].lower().endswith(('.mp4', '.mkv')) and int(f.get('size', 0)) > 100 * 1024 * 1024]
        ads = [f for f in items if f.get('kind') == 'drive#file'
               and not (f['name'].lower().endswith(('.mp4', '.mkv')) and int(f.get('size', 0)) > 100 * 1024 * 1024)]
        if not vids:
            print(f'  ❌ 无视频文件（{len(items)} 个子项）')
            for f in items[:8]:
                print(f'    {f["name"][:50]} {int(f.get("size",0))/2**30:.2f}G')
            continue
        for v in vids:
            print(f'  📄 视频: {v["name"][:60]} {int(v["size"])/2**30:.2f}G')
        if ads:
            print(f'  🗑️ 广告 {len(ads)} 个: ' + '; '.join(a['name'][:20] for a in ads[:3]))
            await api.delete_to_trash([a['id'] for a in ads])
        # 移出视频（batchMove 异步！）
        for v in vids:
            print(f'  📤 移出: {v["name"][:40]}')
            await api.file_batch_move([v['id']], movie_id)
        # 验证：确认视频已到根目录
        await asyncio.sleep(3)
        ls3 = await api.file_list(parent_id=movie_id, size=100)
        root_names = [f['name'] for f in ls3.get('files', [])]
        all_moved = all(v['name'] in root_names for v in vids)
        if all_moved:
            print(f'  ✅ 视频已在根目录，删空文件夹')
            await api.delete_to_trash([folder['id']])
        else:
            print(f'  ⚠️ 移出未确认，暂不删文件夹')
    print('\nDONE')

asyncio.run(main())

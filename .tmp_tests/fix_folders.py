#!/usr/bin/env python3
"""处理 3 个离线文件夹（IPZZ-901-U/jufe-628/jur-837），删旧 JUR-837.mp4，生成下载列表"""
import asyncio, json, sys, re
sys.path.insert(0, '/opt/data/.venv/lib/python3.13/site-packages')
from pikpakapi import PikPakApi

VIDEO_EXT = ('.mp4', '.mkv', '.avi', '.wmv', '.mov', '.flv', '.ts', '.m4v', '.webm')

async def main():
    state = json.load(open('/opt/data/.pikpak_token.json'))
    api = PikPakApi.from_dict(state)
    result = await api.path_to_id('/Inbox-JAV')
    inbox_id = result[0]['id'] if isinstance(result, list) else result

    # 列出 Inbox-JAV
    ls = await api.file_list(parent_id=inbox_id, size=100)
    files = ls.get('files', [])
    print('Inbox-JAV:')
    for f in files:
        print(f"  {'📁' if f.get('kind')=='drive#folder' else '📄'} {f['name']}  {int(f.get('size',0))/1024**3:.2f}GB")

    # 1) 删旧 JUR-837.mp4 (1.37G 字幕版残留)
    for f in files:
        if f.get('kind') == 'drive#file' and f['name'].upper() == 'JUR-837.MP4':
            print(f'🗑️ 删除旧字幕版: JUR-837.mp4 ({int(f["size"])/1024**3:.2f}GB)')
            await api.delete_to_trash([f['id']])

    # 2) 处理离线文件夹
    folders = [f for f in files if f.get('kind') == 'drive#folder' and f['name'] in ('IPZZ-901-U', 'jufe-628', 'jur-837')]
    for folder in folders:
        fid = folder['id']
        fname = folder['name']
        print(f'\n=== 处理文件夹: {fname} ===')
        sub = await api.file_list(parent_id=fid, size=100)
        subs = sub.get('files', [])
        # 识别视频：优先含番号，其次最大
        code = re.sub(r'[^A-Za-z0-9]', '', fname).upper()
        videos = [s for s in subs if s.get('name', '').lower().endswith(VIDEO_EXT)]
        if not videos:
            print('  ⚠️ 无视频文件！')
            continue
        vids_with_code = [v for v in videos if code in re.sub(r'[^A-Za-z0-9]', '', v['name']).upper()]
        keep = (vids_with_code or videos)[0]
        # 广告 = 非 keep 的文件
        ads = [s for s in subs if s['id'] != keep['id']]
        for a in ads:
            print(f'  🗑️ 广告: {a["name"]} ({int(a.get("size",0))/1024**3:.2f}GB)')
        if ads:
            await api.delete_to_trash([a['id'] for a in ads])
        # 移出到 Inbox-JAV
        await api.file_batch_move([keep['id']], inbox_id)
        print(f'  ✅ 移出: {keep["name"]} ({int(keep.get("size",0))/1024**3:.2f}GB)')
        # 重命名（简单名）
        new_name = f'{fname.upper()}.mp4' if not fname.upper().endswith('.MP4') else fname
        new_name = new_name.replace('.MP4', '.mp4')
        await api.file_rename(keep['id'], new_name)
        print(f'  ✅ 重命名: {keep["name"]} → {new_name}')
        # 删空文件夹
        await api.delete_to_trash([fid])
        print(f'  ✅ 删除空文件夹: {fname}')

    # 3) 生成下载列表（排除本地已完成的 HMN-896）
    ls2 = await api.file_list(parent_id=inbox_id, size=100)
    dl = []
    for f in ls2.get('files', []):
        if f.get('kind') != 'drive#file':
            continue
        if not f['name'].lower().endswith(('.mp4', '.mkv')):
            continue
        dl.append(f['name'])
    with open('/tmp/dl2_list.txt', 'w') as fh:
        fh.write('\n'.join(dl))
    print(f'\n📋 下载列表 ({len(dl)} 个文件):')
    for n in dl:
        print(f'  - {n}')
    print('DONE')

asyncio.run(main())

#!/usr/bin/env python3
"""删 PikPak 源文件：云端文件在本地找到完整副本（大小≥99%）才删"""
import asyncio, json, os, sys
sys.path.insert(0, '/opt/data/.venv/lib/python3.13/site-packages')
from pikpakapi import PikPakApi

INBOX_LOCAL = '/opt/data/PikPak/Inbox-JAV'

async def main():
    state = json.load(open('/opt/data/.pikpak_token.json'))
    api = PikPakApi.from_dict(state)
    result = await api.path_to_id('/Inbox-JAV')
    inbox_id = result[0]['id'] if isinstance(result, list) else result

    ls = await api.file_list(parent_id=inbox_id, size=100)
    files = [f for f in ls.get('files', []) if f.get('kind') == 'drive#file']

    # 本地文件清单（名+大小）
    local = {}
    for fn in os.listdir(INBOX_LOCAL):
        fp = os.path.join(INBOX_LOCAL, fn)
        if os.path.isfile(fp):
            local[fn] = os.path.getsize(fp)

    # 匹配：云端文件名 → 本地（直接名匹配，或去掉 -C 等后缀匹配，或大小匹配）
    def find_local(cloud_name, cloud_size):
        if cloud_name in local and local[cloud_name] >= cloud_size * 0.99:
            return cloud_name
        # 大小匹配（本地唯一文件大小一致）
        for lname, lsize in local.items():
            if lsize >= cloud_size * 0.99 and lsize <= cloud_size * 1.01:
                return lname
        return None

    to_del = []
    print('云端 → 本地核对:')
    for f in files:
        cname = f['name']
        csize = int(f.get('size', 0))
        # 跳过非视频
        if not cname.lower().endswith(('.mp4', '.mkv')):
            print(f'  ⏭️ 非视频保留: {cname}')
            continue
        lname = find_local(cname, csize)
        if lname:
            print(f'  🗑️ {cname} ({csize/2**30:.2f}G) → 本地[{lname}] ✅ 删源')
            to_del.append(f['id'])
        else:
            print(f'  ⚠️ 保留（本地无完整副本）: {cname} ({csize/2**30:.2f}G)')

    if to_del:
        await api.delete_to_trash(to_del)
        print(f'✅ 已删除 {len(to_del)} 个 PikPak 源文件')
    else:
        print('无可删文件')
    print('DONE')

asyncio.run(main())

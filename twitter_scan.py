#!/usr/bin/env python3
"""扫描 PikPak 文件夹结构 → manifest JSON（用于去重和下载计划）"""
import json, asyncio, sys, os

sys.path.insert(0, '/opt/data/.venv/lib/python3.13/site-packages')
from pikpakapi import PikPakApi

ROOT_ID = 'VOkYjihe5LY5MUZEgjJNpsKqo2'  # My Twitter
OUT = '/opt/data/twitter_manifest.json'

async def list_all(api, folder_id, path, results, depth=0):
    """递归列出文件夹下所有文件和子文件夹"""
    page_token = None
    while True:
        try:
            result = await api.file_list(parent_id=folder_id, size=500, next_page_token=page_token)
        except Exception as e:
            print(f"  ⚠️ 列出失败 {path}: {e}")
            break
        files = result.get('files', [])
        for f in files:
            fname = f.get('name', '')
            fsize = int(f.get('size', 0))
            fkind = f.get('kind', '')
            fid = f.get('id', '')
            if fkind == 'drive#folder':
                print(f"{'  '*(depth+1)}📁 {fname} ({fid[:12]}...)")
                await list_all(api, fid, f"{path}/{fname}", results, depth+1)
            else:
                ext = os.path.splitext(fname)[1].lower()
                results.append({
                    'name': fname, 'id': fid, 'size': fsize, 'ext': ext,
                    'parent': path, 'src': f"{path}/{fname}"
                })
        page_token = result.get('next_page_token')
        if not page_token:
            break

async def main():
    state = json.load(open('/opt/data/.pikpak_token.json'))
    api = PikPakApi.from_dict(state)
    print(f"扫描 My Twitter (id={ROOT_ID})...")
    results = []
    await list_all(api, ROOT_ID, 'My Twitter', results)
    json.dump({'files': results}, open(OUT, 'w'), ensure_ascii=False, indent=1)
    
    from collections import Counter
    ext_counter = Counter(f['ext'] for f in results)
    total = sum(f['size'] for f in results)
    print(f"\n✅ 扫描完成: {len(results)} 个文件, {total/1024**3:.2f} GB")
    print(f"扩展名分布: {dict(ext_counter)}")

asyncio.run(main())

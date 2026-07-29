#!/usr/bin/env python3
"""检查 PikPak 离线下载状态，完成时保存直链到 /tmp/pikpak_urls.json"""
import json, os, asyncio
from pikpakapi import PikPakApi

TOKEN_FILE = '/opt/data/.pikpak_token.json'
URLS_OUT = '/tmp/pikpak_urls.json'

async def check():
    with open(TOKEN_FILE) as f:
        state = json.load(f)
    api = PikPakApi.from_dict(state)
    
    off = await api.offline_list(size=20)
    tasks = off.get('tasks', [])
    
    new_urls = {}
    for t in tasks:
        name = t.get('name', '')
        status = t.get('status', '?')
        prog = t.get('progress', 0)
        
        if status == 'completed' or prog == 100:
            fid = t.get('file_id', '') or t.get('reference_resource', {}).get('id', '')
            if fid:
                info = await api.get_download_url(fid)
                url = info.get('url', '')
                if url:
                    fn = f'{name}.mp4' if not name.endswith('.mp4') else name
                    new_urls[fn] = url
    
    if new_urls:
        existing = {}
        if os.path.exists(URLS_OUT):
            with open(URLS_OUT) as f:
                existing = json.load(f)
        existing.update(new_urls)
        with open(URLS_OUT, 'w') as f:
            json.dump(existing, f)
        print(f'✅ 新增 {len(new_urls)} 个直链')
        for n in new_urls:
            print(f'  {n}')
        return True
    
    for t in tasks:
        sz = int(t.get('file_size', 0))
        print(f'⏳ {t.get("name","?")[:40]} | {t.get("status","?")} | {t.get("progress",0)}% | {sz/1024**3:.2f}GB')
    return False

if __name__ == '__main__':
    ok = asyncio.run(check())
    exit(0 if ok else 1)

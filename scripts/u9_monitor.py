#!/usr/bin/env python3
"""U9 下载监控：10 分钟超时机制
- 监控 PikPak 离线任务
- 任务超过 10 分钟未完成：
  - 有重复磁链（同标题不同 btih）→ 取消旧任务，换新磁链重下
  - 无重复磁链 → 取消并删除任务
- 下载完成的 → 提取视频文件（移出文件夹、删广告）
"""
import json, asyncio, sys, os, time, re

sys.path.insert(0, '/opt/data/.venv/lib/python3.13/site-packages')
from pikpakapi import PikPakApi

TARGET_ID = 'VOzxmzGf1wHSumyuLKdRfvNgo2'
TIMEOUT = 600  # 10 分钟
VIDEO_EXTS = {'.mp4', '.mkv', '.avi', '.wmv', '.mov', '.flv', '.ts', '.m4v', '.webm'}
STATE_FILE = '/tmp/u9_monitor_state.json'

def load_state():
    if os.path.exists(STATE_FILE):
        return json.load(open(STATE_FILE))
    return {'started': {}, 'done': []}

def save_state(s):
    json.dump(s, open(STATE_FILE, 'w'), ensure_ascii=False, indent=1)

async def main():
    state = json.load(open('/opt/data/.pikpak_token.json'))
    api = PikPakApi(encoded_token=state['encoded_token'])
    api.access_token = state.get('access_token', '')
    api.refresh_token = state.get('refresh_token', '')
    api.user_id = state.get('user_id', '')
    api.device_id = state.get('device_id', '')

    mon = load_state()
    now = time.time()

    # 1. 目标目录当前内容
    r = await api.file_list(parent_id=TARGET_ID, size=100)
    files = r.get('files', [])

    # 2. 找下载中的文件夹（kind=folder，phase 非 complete）
    pending_folders = [f for f in files if f.get('kind') == 'drive#folder']

    for folder in pending_folders:
        fid = folder['id']
        name = folder['name']

        # 记录开始时间
        if fid not in mon['started']:
            mon['started'][fid] = now
            print(f"[{time.strftime('%H:%M:%S')}] ⏳ 开始监控: {name[:40]}")

        elapsed = now - mon['started'][fid]

        # 检查文件夹内容
        r2 = await api.file_list(parent_id=fid, size=50)
        subs = r2.get('files', [])
        videos = [f for f in subs if int(f.get('size',0)) > 100*1024*1024
                  and os.path.splitext(f.get('name',''))[1].lower() in VIDEO_EXTS]

        if videos:
            # 下载完成 → 移出视频，删广告，删文件夹
            vid = max(videos, key=lambda x: int(x.get('size',0)))
            del_ids = [f['id'] for f in subs if f['id'] != vid['id']]
            if del_ids:
                await api.delete_to_trash(del_ids)
            url = f"https://{api.PIKPAK_API_HOST}/drive/v1/files:batchMove"
            hdrs = api.get_headers()
            hdrs['Content-Type'] = 'application/json'
            resp = await api.httpx_client.post(url, json={"ids": [vid['id']], "to": {"parent_id": TARGET_ID}}, headers=hdrs)
            moved = resp.status_code in (200, 201, 204)
            await api.delete_to_trash([fid])
            mon['done'].append(name)
            mon['started'].pop(fid, None)
            print(f"[{time.strftime('%H:%M:%S')}] ✅ 完成: {name[:35]} → 视频 {vid['name'][:25]} ({int(vid['size'])/1024**2:.0f}MB) {'移出成功' if moved else '移出失败!'}")
        elif elapsed > TIMEOUT:
            # 超时未完成 → 按规则处理
            print(f"[{time.strftime('%H:%M:%S')}] ⚠️ 超时(>{TIMEOUT//60}min): {name[:40]}")
            # 有重复磁链吗？（从原始清单查同标题不同 btih）
            all_videos = json.load(open('/tmp/u9_all_videos.json'))
            same_title = [v for v in all_videos if v['title'][:15] == name[:15]]
            if len(same_title) > 1:
                alt = [v for v in same_title if v['btih'] != folder.get('name','')]
                # 简单处理：删任务，重新加（脚本外处理）
                print(f"    → 有 {len(same_title)} 个同标题磁链，建议换磁链")
            else:
                print(f"    → 无替代磁链，取消删除任务")
            await api.delete_to_trash([fid])
            mon['started'].pop(fid, None)
        # else: 等待

    save_state(mon)
    print(f"[{time.strftime('%H:%M:%S')}] 监控扫描完成. 待完成: {len(mon['started'])}")

if __name__ == '__main__':
    asyncio.run(main())

"""碟中谍8：轮询 PikPak 离线完成 → 自动 WebDAV 下载 4K 版 → 通知"""
import json, asyncio, subprocess, time, os
from pikpakapi import PikPakApi

RCLONE = '/opt/data/bin/rclone'
DEST = '/opt/data/.dl_tmp/mi8'
TARGET_GB = 30.18
KEY = '2160p'

async def main():
    t = json.load(open('/opt/data/.pikpak_token.json'))
    c = PikPakApi(encoded_token=t['encoded_token'])
    c.access_token = t['access_token']; c.refresh_token = t['refresh_token']
    c.user_id = t['user_id']; c.device_id = t['device_id']
    r = await c.path_to_id('/Inbox-JAV')
    inbox = r[0]['id']

    folder = None
    name = None
    # 等文件夹大小稳定（离线完成）
    prev = -1
    stable = 0
    t0 = time.time()
    while time.time() - t0 < 5400:  # 最多等 90 分钟
        try:
            fl = await c.file_list(parent_id=inbox)
            for f in fl.get('files', []):
                n = f.get('name', '')
                if '碟中谍8' in n and KEY in n:
                    folder, name = f['id'], n
                    break
            if not folder:
                print('等待文件夹出现...', flush=True)
                await asyncio.sleep(60); continue

            # 递归统计大小
            total = 0
            sub = await c.file_list(parent_id=folder)
            for s in sub.get('files', []):
                total += int(s.get('size') or 0)
            gb = total / 1024**3
            print(f'[{time.strftime("%H:%M:%S")}] 已离线 {gb:.2f} GB / {TARGET_GB} GB', flush=True)
            if abs(gb - prev) < 0.01 and gb > 1:
                stable += 1
            else:
                stable = 0
            prev = gb
            if gb >= TARGET_GB * 0.995 or (stable >= 3 and gb > TARGET_GB * 0.9):
                print('✅ 离线完成', flush=True)
                break
        except Exception as e:
            print('查询异常:', str(e)[:100], flush=True)
        await asyncio.sleep(60)

    if not folder:
        print('❌ 未找到目标文件夹，放弃', flush=True)
        return

    os.makedirs(DEST, exist_ok=True)
    print(f'开始 WebDAV 下载: {name[:80]}', flush=True)
    cmd = [RCLONE, 'copy', f'pikpak:/Inbox-JAV/{name}', DEST,
           '--transfers', '8', '--buffer-size', '32M', '--stats', '60s',
           '--log-file', '/tmp/mi8_dl.log', '--log-level', 'INFO']
    p = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    p.wait()
    print(f'rclone 退出码: {p.returncode}', flush=True)
    out = subprocess.run(['du', '-sh', DEST], capture_output=True, text=True).stdout.strip()
    print('下载结果:', out, flush=True)
    ls = subprocess.run(['ls', '-la', DEST], capture_output=True, text=True).stdout
    print(ls, flush=True)

asyncio.run(main())

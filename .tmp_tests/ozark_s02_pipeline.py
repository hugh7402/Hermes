"""黑钱胜地 S02：轮询 PikPak 离线完成 → 自动 WebDAV 下载 → 完成通知"""
import json, asyncio, subprocess, time, os
from pikpakapi import PikPakApi

DEST = '/opt/data/.dl_tmp/ozark_s02'
RCLONE = '/opt/data/bin/rclone'

async def wait_offline(client, max_wait=3600):
    """轮询直到第二季离线完成"""
    t0 = time.time()
    while time.time() - t0 < max_wait:
        try:
            tasks = await client.offline_list()
            for t in tasks.get('tasks', []):
                n = t.get('name', '')
                if '黑钱' in n and '第二季' in n or ('Ozark' in n and 'S02' in n):
                    phase = t.get('phase', '')
                    prog = t.get('progress', 0)
                    sz = int(t.get('file_size') or 0) / 1024**3
                    print(f'[{time.strftime("%H:%M:%S")}] {n[:50]} | {phase} | {prog}% | {sz:.2f}GB', flush=True)
                    if phase in ('PHASE_TYPE_COMPLETE', 'PHASE_TYPE_SUCCESS'):
                        print('✅ 离线完成', flush=True)
                        return True
        except Exception as e:
            print(f'查询异常: {str(e)[:80]}', flush=True)
        await asyncio.sleep(60)
    print('⚠️ 等待超时', flush=True)
    return False

async def main():
    token = json.load(open('/opt/data/.pikpak_token.json'))
    client = PikPakApi(encoded_token=token['encoded_token'])
    client.access_token = token['access_token']
    client.refresh_token = token['refresh_token']
    client.user_id = token['user_id']
    client.device_id = token['device_id']

    ok = await wait_offline(client)
    if not ok:
        return

    # 找 S02 文件夹
    r = await client.path_to_id('/Inbox-JAV')
    files = await client.file_list(parent_id=r[0]['id'])
    folder = None
    for f in files.get('files', []):
        n = f.get('name', '')
        if '第二季' in n or ('47BT' in n.upper() and 'S02' in n):
            folder = n
            break
    if not folder:
        print('❌ 未找到 S02 文件夹', flush=True)
        return
    print(f'文件夹: {folder}', flush=True)

    # WebDAV 下载
    os.makedirs(DEST, exist_ok=True)
    cmd = [RCLONE, 'copy', f'pikpak:/Inbox-JAV/{folder}', DEST,
           '--transfers', '15', '--buffer-size', '32M', '--stats', '60s',
           '--log-file', '/tmp/ozark_s02_dl.log', '--log-level', 'INFO']
    print('开始下载...', flush=True)
    p = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    p.wait()
    print(f'rclone 退出码: {p.returncode}', flush=True)
    out = subprocess.run(['du', '-sh', DEST], capture_output=True, text=True).stdout.strip()
    print(f'下载结果: {out}', flush=True)

asyncio.run(main())

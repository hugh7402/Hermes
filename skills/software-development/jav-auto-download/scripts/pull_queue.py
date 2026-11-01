#!/usr/bin/env python3
"""Inbox-JAV 串行拉取队列：等云端有文件 → 一次拉一个 → 校验收尾 → 删云端源 → 下一个。

设计要点：
  · 串行：同一时刻只跑一个 rclone copy，避免抢带宽（低内存机器铁律）
  · 等外部 rclone 跑完再接手：检测到其他 rclone 进程就等待，不并发
  · 收尾复用 finish_dl.py：字节比对 + ffprobe + 字幕按番号改名 + 删云端源
  · 校验不通过就保留云端源并跳过，不静默丢数据
  · 全部拉完（云端无文件）后退出

用法: python3 pull_queue.py [最大运行小时数，默认 4]
日志: /opt/data/.safe_media/pull_queue.log
"""
import json
import pathlib
import re
import subprocess
import sys
import time

RCLONE = '/opt/data/bin/rclone'
REMOTE = 'pikpak:/Inbox-JAV'
DEST = '/opt/data/PikPak/Inbox-JAV'
FINISH = '/opt/data/.tmp_tests/finish_dl.py'
PY = '/opt/data/.venv/bin/python3'
LOG = pathlib.Path('/opt/data/.safe_media/pull_queue.log')
VIDEO_EXT = ('.mp4', '.mkv', '.avi', '.wmv', '.mov', '.flv', '.ts', '.m4v', '.webm')


def log(msg):
    line = f'{time.strftime("%Y-%m-%d %H:%M:%S")} {msg}'
    print(line, flush=True)
    with LOG.open('a') as f:
        f.write(line + '\n')


def rclone_running():
    """是否有其他 rclone 进程在动 PikPak（排除自己）"""
    for pd in pathlib.Path('/proc').glob('[0-9]*'):
        try:
            argv = (pd / 'cmdline').read_bytes().replace(b'\0', b' ').decode(errors='ignore')
        except OSError:
            continue
        if 'rclone' in argv and 'pikpak' in argv.lower():
            return True
    return False


def cloud_files():
    r = subprocess.run([RCLONE, 'lsjson', REMOTE], capture_output=True, text=True, timeout=120)
    out = []
    for f in json.loads(r.stdout or '[]'):
        name = f['Name']
        if name.lower().endswith(VIDEO_EXT):
            out.append((f['Size'], name))
    return sorted(out, key=lambda x: x[1])


def code_of(name):
    """从文件名取番号：前两段，例如 DSOD-073"""
    parts = name.split('-')
    return '-'.join(parts[:2]) if len(parts) >= 2 else name


def main():
    hours = float(sys.argv[1]) if len(sys.argv) > 1 else 4
    deadline = time.time() + hours * 3600
    log(f'=== queue start (max {hours}h) ===')

    while time.time() < deadline:
        files = cloud_files()
        if not files:
            log('云端已空，队列结束')
            return 0
        size, name = files[0]
        code = code_of(name)
        gb = size / 1024 ** 3

        # 本地已有同番号完整文件：不用再拉，直接走收尾（校验收尾会删云端源）
        local = [p for p in pathlib.Path(DEST).glob('*.mp4')
                 if p.name.upper().replace('-', '').startswith(code.replace('-', '').upper())]
        if local and local[0].stat().st_size == size:
            log(f'{code} 本地已存在且大小一致 {gb:.2f}GB，跳过下载直接收尾')
            f = subprocess.run([PY, FINISH, code], capture_output=True, text=True, timeout=900)
            for line in (f.stdout or '').splitlines():
                log(f'    {line}')
            if f.returncode != 0:
                log(f'  ⚠️ 收尾未通过，改名 .unverified 跳过')
                subprocess.run([RCLONE, 'moveto', f'{REMOTE}/{name}',
                                f'{REMOTE}/{name}.unverified'], capture_output=True, timeout=120)
            continue

        log(f'下一个: {code}  {gb:.2f}GB  {name[:56]}')

        # 等外部 rclone 让路
        waited = 0
        while rclone_running():
            if waited % 60 == 0:
                log(f'  等待其他 rclone 结束（已等 {waited}s）')
            time.sleep(10)
            waited += 10
            if time.time() > deadline:
                log('超时退出')
                return 0

        log(f'  开始拉取 {gb:.2f}GB')
        t0 = time.time()
        r = subprocess.run([RCLONE, 'copy', f'{REMOTE}/{name}', DEST,
                            '--transfers', '15', '--checkers', '15',
                            '--buffer-size', '32M', '--timeout', '60s',
                            '--contimeout', '30s', '--retries', '3',
                            '--low-level-retries', '10', '--stats', '60s',
                            '--stats-one-line', '-v'],
                           capture_output=True, text=True, timeout=3600)
        dur = time.time() - t0
        if r.returncode != 0:
            log(f'  ❌ 拉取失败 rc={r.returncode}: {(r.stderr or r.stdout)[-300:]}')
            log('  暂停 60s 后重试同一条')
            time.sleep(60)
            continue
        log(f'  ✅ 拉取完成 {dur / 60:.1f} 分钟，均速 {size / 1024 ** 2 / max(dur, 1):.1f} MB/s')

        log(f'  收尾校验 {code}')
        f = subprocess.run([PY, FINISH, code], capture_output=True, text=True, timeout=900)
        for line in (f.stdout or '').splitlines():
            log(f'    {line}')

        if f.returncode != 0:
            log(f'  ⚠️ 收尾校验未通过（rc={f.returncode}），云端源保留，跳过该条')
            # 把这条标记跳过：改名加 .unverified 免得死循环重试
            subprocess.run([RCLONE, 'moveto', f'{REMOTE}/{name}',
                            f'{REMOTE}/{name}.unverified'], capture_output=True, timeout=120)
            continue

    log('=== 到达最大运行时间，退出 ===')
    return 0


if __name__ == '__main__':
    sys.exit(main())

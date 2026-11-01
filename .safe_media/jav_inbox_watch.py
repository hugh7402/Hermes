#!/usr/bin/env python3
"""Inbox-JAV 删除监视器：一旦有 mp4 消失，记录时间、文件、以及持有该目录 fd 的所有进程。

背景：2026-10 两度出现 mp4 静默消失（本次 DSOD-073 + SGKI-108 共 12.3GB；此前 74GB），
srt 都保留、无 cron / 无插件 / 无同步任务可对应，凶手未钉死。

用法：python3 jav_inbox_watch.py [监视秒数，默认 86400]
日志：/opt/data/.safe_media/jav_inbox_watch.log
"""
import glob
import os
import pathlib
import sys
import time

TARGET = pathlib.Path('/opt/data/PikPak/Inbox-JAV')
LOG = pathlib.Path('/opt/data/.safe_media/jav_inbox_watch.log')
POLL = 2.0


def log(msg):
    with LOG.open('a') as f:
        f.write(f'{time.strftime("%Y-%m-%d %H:%M:%S")} {msg}\n')


def snapshot():
    """name -> (size, mtime)"""
    out = {}
    try:
        with os.scandir(TARGET) as it:
            for e in it:
                try:
                    st = e.stat()
                    out[e.name] = (st.st_size, st.st_mtime)
                except OSError:
                    pass
    except OSError as exc:
        log(f'SCANDIR-FAIL {exc}')
    return out


def suspects():
    """所有 fd 指向该目录的进程（删除者如果还开着 fd 会被列出来）"""
    hits = []
    for pd in glob.glob('/proc/[0-9]*'):
        pid = pd.rsplit('/', 1)[-1]
        try:
            cmd = open(pd + '/cmdline', 'rb').read().replace(b'\0', b' ').decode(errors='ignore')[:150]
        except OSError:
            continue
        try:
            for fd in os.listdir(pd + '/fd'):
                try:
                    tgt = os.readlink(f'{pd}/fd/{fd}')
                except OSError:
                    continue
                if 'PikPak' in tgt:
                    hits.append(f'PID {pid} [{cmd.strip()}] -> {tgt[:70]}')
        except OSError:
            continue
    return hits


def main():
    seconds = int(sys.argv[1]) if len(sys.argv) > 1 else 86400
    LOG.parent.mkdir(parents=True, exist_ok=True)
    log(f'=== watcher start, pid={os.getpid()}, poll={POLL}s, dur={seconds}s, target={TARGET} ===')
    prev = snapshot()
    log(f'baseline: {len(prev)} items, mp4={sum(1 for k in prev if k.endswith(".mp4"))}')
    end = time.time() + seconds
    while time.time() < end:
        time.sleep(POLL)
        cur = snapshot()
        gone = [k for k in prev if k not in cur and not k.endswith('.partial')]
        new = [k for k in cur if k not in prev and not k.endswith('.partial')]
        changed = [k for k in cur if k in prev and cur[k] != prev[k]]
        if gone:
            for g in gone:
                sz = prev[g][0]
                log(f'DELETED {g}  size={sz:,}  ({sz / 1024 ** 3:.2f}GB)')
            for s in suspects() or ['(no process holds a fd on PikPak)']:
                log(f'  suspect {s}')
        if new:
            # .partial 是 rclone 下载中的临时文件，只在出现/消失时记，不记每次写入
            log(f'CREATED {new}')
        changed_real = [k for k in changed if not k.endswith('.partial')]
        if changed_real:
            log(f'MODIFIED {changed_real}')
        prev = cur
    log('=== watcher end ===')


if __name__ == '__main__':
    main()

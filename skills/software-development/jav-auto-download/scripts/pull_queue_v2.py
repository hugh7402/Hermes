#!/usr/bin/env python3
"""Inbox-JAV 满速串行拉取队列 + 本地完整性巡检（v2）。

背景（2026-10-31 实测）：/opt/data 是 FUSE 挂载（zfuse.zfsv3），15 线程 × 32M buffer
满速写入时，刚下完的多 GB mp4 会静默消失（.srt 这类小文件不受影响），无任何删除进程、
无 cron、无守护脚本，磁盘空间真实被释放 —— 判定为 FUSE 写回层丢 extents，非人为删除。

策略（用户明确要满速）：
  · 速度不降：--transfers 15 --buffer-size 32M
  · 每条下完立即 sync + 复核大小 + 观察 20 秒；消失就立刻重拉（最多 3 次）
  · 云端源「保管期」30 分钟：期间不删，本地丢了能秒补；过了保管期且本地仍在才删
  · 每 10 分钟巡检已登记文件；缺失时云端还在就重拉，云端已删就记入待重新离线

用法: python3 pull_queue_v2.py [最大运行小时数，默认 4]
状态: /opt/data/.safe_media/pull_state.json
日志: /opt/data/.safe_media/pull_queue.log
"""
import json
import os
import pathlib
import subprocess
import sys
import time

RCLONE = '/opt/data/bin/rclone'
REMOTE = 'pikpak:/Inbox-JAV'
DEST = pathlib.Path('/opt/data/PikPak/Inbox-JAV')
FINISH = '/opt/data/.tmp_tests/finish_dl.py'
PY = '/opt/data/.venv/bin/python3'
LOG = pathlib.Path('/opt/data/.safe_media/pull_queue.log')
STATE = pathlib.Path('/opt/data/.safe_media/pull_state.json')
VIDEO_EXT = ('.mp4', '.mkv', '.avi', '.wmv', '.mov', '.flv', '.ts', '.m4v', '.webm')
GRACE_SEC = 1800
SWEEP_EVERY = 600
RCLONE_ARGS = ['--transfers', '15', '--checkers', '15', '--buffer-size', '32M',
               '--timeout', '60s', '--contimeout', '30s', '--retries', '3',
               '--low-level-retries', '10', '--stats', '60s', '--stats-one-line', '-v']


def log(msg):
    line = f'{time.strftime("%Y-%m-%d %H:%M:%S")} {msg}'
    print(line, flush=True)
    with LOG.open('a') as f:
        f.write(line + '\n')


def load_state():
    if STATE.exists():
        try:
            return json.loads(STATE.read_text())
        except Exception:
            pass
    return {'verified': {}, 'pending_offline': []}


def save_state(st):
    STATE.write_text(json.dumps(st, ensure_ascii=False, indent=1))


def rclone_running():
    for pd in pathlib.Path('/proc').glob('[0-9]*'):
        try:
            argv = (pd / 'cmdline').read_bytes().replace(b'\0', b' ').decode(errors='ignore')
        except OSError:
            continue
        if argv and os.path.basename(argv.split(' ')[0]) == 'rclone' and 'pikpak' in argv.lower():
            return True
    return False


def cloud_list():
    r = subprocess.run([RCLONE, 'lsjson', REMOTE], capture_output=True, text=True, timeout=120)
    out = []
    for f in json.loads(r.stdout or '[]'):
        if f['Name'].lower().endswith(VIDEO_EXT):
            out.append((f['Size'], f['Name']))
    return sorted(out, key=lambda x: x[1])


def code_of(name):
    parts = name.split('-')
    return '-'.join(parts[:2]) if len(parts) >= 2 else name


def pull(name, size):
    for attempt in range(1, 4):
        log(f'  拉取第 {attempt} 次 {size / 1024 ** 3:.2f}GB')
        t0 = time.time()
        r = subprocess.run([RCLONE, 'copy', f'{REMOTE}/{name}', str(DEST)] + RCLONE_ARGS,
                           capture_output=True, text=True, timeout=7200)
        dur = max(time.time() - t0, 1)
        if r.returncode != 0:
            log(f'  ❌ rclone rc={r.returncode}: {(r.stderr or r.stdout)[-260:]}')
            continue
        log(f'  ✅ 传输完成 {dur / 60:.1f} 分钟，均速 {size / 1024 ** 2 / dur:.1f} MB/s')
        local = DEST / name
        if not local.exists():
            log('  ⚠️ 文件不在预期位置，重试')
            continue
        got = local.stat().st_size
        if got != size:
            log(f'  ⚠️ 大小不符 本地 {got:,} / 云端 {size:,}，重试')
            continue
        return size
    return 0


def sweep(st):
    """巡检并只做报告：用户在自行搬动文件，自动补拉会跟他抢，所以这里不重下。

    唯一例外是明确列在 skip_codes 之外、且云端仍在的条目 —— 也仍然只报告不下载，
    交给人判断（避免把用户挪走的文件又拉回来一份）。
    """
    skip = set(st.get('skip_codes') or [])
    clouds = None
    for name, rec in list(st['verified'].items()):
        local = DEST / name
        if local.exists() and local.stat().st_size == rec['size']:
            continue
        code = code_of(name)
        if code in skip:
            st['verified'].pop(name, None)   # 跳过名单里的不追踪，免得每轮刷日志
            continue
        if clouds is None:
            clouds = {n: s for s, n in cloud_list()}
        where = '云端仍有源，可随时重拉' if name in clouds else '云端已无源，需重新离线'
        log(f'  📋 本地缺失 {name[:56]}  → {where}')
    return []


def main():
    hours = float(sys.argv[1]) if len(sys.argv) > 1 else 4
    deadline = time.time() + hours * 3600
    st = load_state()
    log(f'=== queue v2 start (max {hours}h，满速 15x32M，保管期 {GRACE_SEC // 60}min) ===')
    if st['pending_offline']:
        log(f'  待重新离线: {st["pending_offline"]}')
    last_sweep = 0

    while time.time() < deadline:
        files = cloud_list()
        for size, name in files:
            rec = st['verified'].get(name)
            if not rec or time.time() - rec['ts'] < GRACE_SEC:
                continue
            local = DEST / name
            if local.exists() and local.stat().st_size == size:
                subprocess.run([RCLONE, 'delete', f'{REMOTE}/{name}'], capture_output=True, timeout=180)
                log(f'  保管期满且本地完好，删云端源 {name[:52]}')
                st['verified'].pop(name, None)
                save_state(st)
            else:
                log(f'  保管期满但本地异常，保留云端源 {name[:52]}')

        files = cloud_list()
        if not files:
            log('云端视频已全部处理完')
            save_state(st)
            return 0

        # 用户明确不要再补下的番号：永远不拉（云端源保留，改主意可随时恢复）
        skip = set(st.get('skip_codes') or [])
        pullable = [(s, n) for s, n in files if code_of(n) not in skip]
        if not pullable:
            skipped = sorted({code_of(n) for _, n in files})
            log(f'云端只剩跳过名单里的番号，不拉取: {skipped}')
            save_state(st)
            return 0
        files = pullable

        size, name = files[0]
        code = code_of(name)
        gb = size / 1024 ** 3

        # 已下载完成的条目：登记（过保管期就删云端源），然后挑下一条真正要下的，绝不死循环
        target = None
        for size, name in files:
            local = DEST / name
            if local.exists() and local.stat().st_size == size:
                rec = st['verified'].get(name)
                if not rec:
                    st['verified'][name] = {'size': size, 'ts': time.time()}
                    save_state(st)
                    log(f'{code_of(name)} 本地已存在，登记（云端源进入保管期）')
                elif time.time() - rec['ts'] >= GRACE_SEC:
                    subprocess.run([RCLONE, 'delete', f'{REMOTE}/{name}'], capture_output=True, timeout=180)
                    st['verified'].pop(name, None)
                    save_state(st)
                    log(f'{code_of(name)} 保管期满且本地完好，删云端源')
                continue
            target = (size, name)
            break

        if not target:
            # 云端没有需要下载的条目：清一轮保管期满的源，然后收工退出（不再 60s 刷日志）
            cleaned = 0
            for s2, n2 in cloud_list():
                rec2 = st['verified'].get(n2)
                if rec2 and time.time() - rec2['ts'] >= GRACE_SEC:
                    lp = DEST / n2
                    if lp.exists() and lp.stat().st_size == s2:
                        subprocess.run([RCLONE, 'delete', f'{REMOTE}/{n2}'], capture_output=True, timeout=180)
                        st['verified'].pop(n2, None)
                        cleaned += 1
                        log(f'  保管期满且本地完好，删云端源 {n2[:50]}')
            save_state(st)
            left = [n for _, n in cloud_list() if code_of(n) not in set(st.get('skip_codes') or [])]
            if not left:
                log(f'✅ 全部完成，队列退出（本轮清理云端源 {cleaned} 个）')
                return 0
            log(f'剩 {len(left)} 条待保管期满后清理，5 分钟后再看')
            time.sleep(300)
            continue

        size, name = target
        code = code_of(name)
        gb = size / 1024 ** 3
        local = DEST / name
        if local.exists() and local.stat().st_size == size:
            log(f'{code} 本地已存在且一致 {gb:.2f}GB，登记后跳过下载')
            prev = st['verified'].get(name, {})
            st['verified'][name] = {'size': size, 'ts': prev.get('ts', time.time())}
            save_state(st)
            continue

        log(f'下一个: {code}  {gb:.2f}GB  {name[:56]}')
        waited = 0
        while rclone_running():
            if waited % 120 == 0:
                log(f'  等外部 rclone 让路（已等 {waited}s）')
            time.sleep(10)
            waited += 10
            if time.time() > deadline:
                return 0

        got = pull(name, size)
        if not got:
            log('  ❌ 三次重试仍失败，60s 后跳过这条')
            time.sleep(60)
            continue

        st['verified'][name] = {'size': got, 'ts': time.time()}
        save_state(st)

        f = subprocess.run([PY, FINISH, code], capture_output=True, text=True, timeout=900)
        for line in (f.stdout or '').splitlines():
            log(f'    {line}')
        if f.returncode != 0:
            log('  ⚠️ 收尾校验未通过（云端源仍在保管期内，可重试）')

    log('=== 到达最大运行时间 ===')
    save_state(st)
    return 0


if __name__ == '__main__':
    sys.exit(main())

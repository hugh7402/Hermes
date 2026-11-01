import os, glob, time, pathlib
LOG = '/opt/data/.safe_media/watchdog.log'
TARGETS = ['/opt/data/PikPak', '/opt/data/.safe_media']
def logm(s):
    with open(LOG, 'a') as f: f.write(f'{time.strftime("%H:%M:%S")} {s}\n')
def count():
    n = 0
    for t in TARGETS:
        try: n += len(os.listdir(t))
        except OSError: pass
    return n
last = count(); logm(f'watchdog start, items={last}')
end = time.time() + 3600
while time.time() < end:
    time.sleep(0.1)
    cur = count()
    if cur != last:
        suspects = set()
        for pd in glob.glob('/proc/[0-9]*'):
            pid = pd.split('/')[-1]
            try:
                cmd = open(pd + '/cmdline','rb').read().replace(b'\0', b' ').decode()[:120]
                for fd in os.listdir(pd + '/fd'):
                    try: t = os.readlink(pd + '/fd/' + fd)
                    except OSError: continue
                    if any(x in t for x in TARGETS):
                        suspects.add(f'PID {pid} | {cmd} | {t[:60]}')
            except OSError:
                continue
        logm(f'CHANGE {last}->{cur}  suspects={list(suspects) or "none"}')
        last = cur
logm('watchdog end')

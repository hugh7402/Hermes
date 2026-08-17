#!/usr/bin/env python3
"""网络视频 → 本地 CDN 直连下载（无代理，aria2 3 并发）
源: PikPak /网络视频（含 烈@Retsu_dao 子文件夹）
目标: /opt/data/PikPak/网络视频/
规则: 只下视频、跳过已存在(≥99%)、失败重试3次、无代理
"""
import json, os, sys, time, asyncio, subprocess

sys.path.insert(0, '/opt/data/.venv/lib/python3.13/site-packages')
sys.path.insert(0, '/opt/data')
from pikpakapi import PikPakApi
import ai_drama_dl
from ai_drama_dl import get_url, verify_file, loop_run, VIDEO_EXT

CONCURRENCY = 3
ARIA2 = '/opt/data/aria2c'
ROOT_ID = 'VOzxnujyva9DSaR-AQ3rzD1lo2'   # /网络视频
DEST_ROOT = '/opt/data/PikPak/网络视频'
MANIFEST = '/opt/data/network_video_manifest.json'

def aria2_download_no_proxy(url, dest_file, total_size=0, use_proxy=False):
    """aria2 下载 — 默认无代理直连; use_proxy=True 时走代理"""
    os.makedirs(os.path.dirname(dest_file), exist_ok=True)
    env = dict(os.environ)
    env['LD_LIBRARY_PATH'] = '/opt/data' + (':' + env['LD_LIBRARY_PATH'] if env.get('LD_LIBRARY_PATH') else '')
    cmd = [
        ARIA2,
        '--max-connection-per-server=8', '--split=8', '--min-split-size=8M',
        '--continue=true', '--max-tries=3', '--retry-wait=3',
        '--timeout=60', '--connect-timeout=15',
        '--console-log-level=warn',
        '--dir', os.path.dirname(dest_file),
        '--out', os.path.basename(dest_file),
    ]
    if use_proxy:
        cmd.append('--all-proxy=http://127.0.0.1:10808')
    cmd.append(url)
    t0 = time.time()
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, env=env)
    proc.wait()
    dt = time.time() - t0
    rc = proc.returncode
    return rc == 0, dt, 'OK' if rc == 0 else 'FAIL'

async def aria2_download_async(url, dest_file, total_size=0, use_proxy=False):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, aria2_download_no_proxy, url, dest_file, total_size, use_proxy)

async def scan_network_video(api):
    """扫描 /网络视频 全部视频文件（递归子文件夹）"""
    tasks = []
    async def walk(parent_id, parent_dir):
        r = await api.file_list(parent_id=parent_id, size=100)
        files = r.get('files', [])
        for f in files:
            name = f.get('name', '')
            kind = f.get('kind', '')
            size = int(f.get('size', 0))
            ext = os.path.splitext(name)[1].lower()
            if kind == 'drive#folder':
                await walk(f['id'], os.path.join(parent_dir, name))
            elif ext in VIDEO_EXT and size > 0:
                tasks.append({
                    'id': f['id'],
                    'name': name,
                    'size': size,
                    'dest_dir': os.path.join(DEST_ROOT, parent_dir),
                })
    await walk(ROOT_ID, '')
    total = sum(t['size'] for t in tasks)
    print(f"扫描完成: {len(tasks)} 个视频, {total/1024**3:.2f} GB")
    json.dump(tasks, open(MANIFEST, 'w'), ensure_ascii=False, indent=1)
    return tasks

async def main():
    with open('/opt/data/.pikpak_token.json') as f:
        state = json.load(f)
    api = PikPakApi.from_dict(state)

    tasks = await scan_network_video(api)
    if not tasks:
        print("无任务")
        return

    stats = {
        'total': len(tasks), 'done': 0,
        'total_bytes': sum(t['size'] for t in tasks),
        'bytes_ok': 0, 't0': time.time(),
    }

    sem = asyncio.Semaphore(CONCURRENCY)
    results = []

    async def process_one(task):
        async with sem:
            fname = task['name']
            dest_file = os.path.join(task['dest_dir'], fname)
            stats['done'] += 1

            if os.path.exists(dest_file):
                sz = os.path.getsize(dest_file)
                if sz >= task['size'] * 0.99:
                    results.append({'task': task, 'status': 'SKIP'})
                    print(f"[{stats['done']}/{stats['total']}] ⏭️  {fname[:45]} ({sz/1024**2:.0f}MB)", flush=True)
                    return

            print(f"[{stats['done']}/{stats['total']}] ⬇️  {fname[:50]} ({task['size']/1024**2:.0f}MB)", flush=True)
            url = await get_url(api, task['id'])
            if not url:
                results.append({'task': task, 'status': 'URL_FAIL'})
                print(f"  ❌ URL失败")
                return

            total_size = task['size']
            # 默认走代理（SG-AWS02 稳定 9MB/s+）; 直连 CDN 当前不稳定
            use_proxy = True
            ok, elapsed, reason = await aria2_download_async(url, dest_file, total_size, use_proxy)

            # 直连重试（最多 2 次换 URL），失败后自动切代理
            attempt = 1
            while not ok and attempt < 3 and not use_proxy:
                print(f"  ⚠️ 直连失败({reason}), 换URL重试 {attempt}/2: {fname[:40]}", flush=True)
                url = await get_url(api, task['id'])
                if not url:
                    break
                ok, elapsed, reason = await aria2_download_async(url, dest_file, total_size, False)
                attempt += 1

            # 直连仍失败 → 切代理
            if not ok and not use_proxy:
                print(f"  🔄 直连失败, 切换代理下载: {fname[:40]}", flush=True)
                url = await get_url(api, task['id'])
                if url:
                    ok, elapsed, reason = await aria2_download_async(url, dest_file, total_size, True)
                    use_proxy = True

            # 代理也失败 → 再重试 1 次
            if not ok and use_proxy:
                url = await get_url(api, task['id'])
                if url:
                    ok, elapsed, reason = await aria2_download_async(url, dest_file, total_size, True)

            if not ok:
                results.append({'task': task, 'status': 'DL_FAIL', 'reason': reason})
                print(f"  ❌ 失败3次: {fname} ({reason})")
                return

            good, dur = await loop_run(verify_file, dest_file)
            speed = task['size'] / elapsed / 1024 / 1024 if elapsed > 0 else 0
            if good:
                results.append({'task': task, 'status': 'OK', 'duration': dur})
                stats['bytes_ok'] += task['size']
                elapsed_total = time.time() - stats['t0']
                avg_speed = stats['bytes_ok'] / elapsed_total / 1024 / 1024 if elapsed_total > 0 else 0
                remaining = (stats['total_bytes'] - stats['bytes_ok']) / 1024**3
                eta = remaining / avg_speed / 3600 if avg_speed > 0.001 else 0
                print(f"  ✅ {speed:.1f}MB/s ({elapsed:.0f}s) 累计{avg_speed:.1f}MB/s 剩余{remaining:.0f}GB ETA~{eta:.1f}h", flush=True)
            else:
                results.append({'task': task, 'status': 'VERIFY_FAIL'})
                print(f"  ❌ 校验失败: {fname} ({dur})")

    queue = asyncio.Queue()
    for t in tasks:
        await queue.put(t)

    async def worker():
        while True:
            try:
                task = await asyncio.wait_for(queue.get(), timeout=5)
            except asyncio.TimeoutError:
                break
            try:
                await process_one(task)
            except Exception as e:
                results.append({'task': task, 'status': 'ERROR', 'msg': str(e)})
                print(f"  ❌ {task['name'][:40]}: {e}")
            queue.task_done()

    t0 = time.time()
    print(f"\n开始下载: {len(tasks)} 个文件, {CONCURRENCY} 并发, CDN 直连(无代理)")
    workers = [asyncio.create_task(worker()) for _ in range(CONCURRENCY)]
    await asyncio.gather(*workers)

    dt = time.time() - t0
    ok = sum(1 for r in results if r['status'] == 'OK')
    fail = len(results) - ok
    print(f"\n=== 完成: {ok}/{len(results)} 成功, {fail} 失败, 用时 {dt/60:.1f}min ===")
    json.dump(results, open('/opt/data/network_video_dl_result.json', 'w'), ensure_ascii=False, indent=1)

if __name__ == '__main__':
    asyncio.run(main())

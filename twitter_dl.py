#!/usr/bin/env python3
"""My Twitter 全量下载 — 复用 ai_drama_dl 的下载核心"""
import json, os, sys, time, asyncio

sys.path.insert(0, '/opt/data/.venv/lib/python3.13/site-packages')
sys.path.insert(0, '/opt/data')
import ai_drama_dl
from ai_drama_dl import get_url, aria2_download_async, verify_file, loop_run, CONCURRENCY

MANIFEST = '/opt/data/twitter_manifest.json'
DEST_ROOT = '/opt/data/PikPak/My Twitter'

def build_plan():
    """My Twitter: 374 个文件, 按 size 去重(同名/同字节数视为重复), 只下保留的"""
    data = json.load(open(MANIFEST))
    files = [f for f in data['files'] if f['ext'].lower() in ai_drama_dl.VIDEO_EXT]

    # 按 size 去重: 字节数完全相同 → 视为重复文件, 只保留第一个
    seen_sizes = set()
    kept = []
    skipped = []
    for f in files:
        if f['size'] in seen_sizes:
            skipped.append(f)
        else:
            seen_sizes.add(f['size'])
            kept.append(f)

    tasks = [{
        'src': f['src'],
        'dest_dir': DEST_ROOT,
        'name': f['name'],
        'id': f['id'],
        'size': f['size'],
    } for f in kept]
    total = sum(t['size'] for t in tasks)
    dup_bytes = sum(f['size'] for f in skipped)
    print(f"总文件: {len(files)}, 按size去重后: {len(tasks)} 个, 跳过重复 {len(skipped)} 个 ({dup_bytes/1024**3:.2f} GB)")
    print(f"计划: {len(tasks)} 个文件, {total/1024**3:.2f} GB")
    return tasks

async def main():
    tasks = build_plan()
    if not tasks:
        print("无任务")
        return

    with open('/opt/data/.pikpak_token.json') as f:
        state = json.load(f)
    api = ai_drama_dl.PikPakApi.from_dict(state)

    stats = {
        'total': len(tasks),
        'done': 0,
        'total_bytes': sum(t['size'] for t in tasks),
        'bytes_ok': 0,
        't0': time.time(),
    }

    sem = asyncio.Semaphore(CONCURRENCY)
    results = []

    async def process_one(task):
        async with sem:
            fname = task['name']
            dest_file = os.path.join(task['dest_dir'], fname)
            stats['done'] += 1

            # 跳过已存在
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
            ok, elapsed, reason = await aria2_download_async(url, dest_file, total_size)
            attempt = 1
            while not ok and reason == 'SLOW' and attempt < 3 and total_size <= 500 * 1024 * 1024:
                print(f"  ⚠️ 慢节点({attempt}/3), 换URL: {fname[:40]}", flush=True)
                url = await get_url(api, task['id'])
                if not url:
                    break
                ok, elapsed, reason = await aria2_download_async(url, dest_file, total_size)
                attempt += 1

            if not ok:
                attempts = task.get('attempts', 1)
                if attempts < 3:
                    task['attempts'] = attempts + 1
                    results.append({'task': task, 'status': 'RETRY'})
                    print(f"  🔄 失败({reason}), 重排队({attempts}/3)", flush=True)
                    await stats['queue'].put(task)
                else:
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

    # 队列 + worker（支持重排队）
    queue = asyncio.Queue()
    stats['queue'] = queue
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
    print(f"\n开始下载: {len(tasks)} 个文件, {CONCURRENCY} 并发")
    workers = [asyncio.create_task(worker()) for _ in range(CONCURRENCY)]
    await asyncio.gather(*workers)

    dt = time.time() - t0
    ok = sum(1 for r in results if r['status'] == 'OK')
    fail = len(results) - ok
    print(f"\n=== 完成: {ok}/{len(results)} 成功, {fail} 失败, 用时 {dt/60:.1f}min ===")
    json.dump(results, open('/opt/data/twitter_dl_result.json', 'w'), ensure_ascii=False, indent=1)

if __name__ == '__main__':
    asyncio.run(main())

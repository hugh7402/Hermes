#!/usr/bin/env python3
"""补下缺失的 57 个文件 — 复用 ai_drama_dl 的下载逻辑"""
import json, os, sys, time, asyncio

sys.path.insert(0, '/opt/data/.venv/lib/python3.13/site-packages')
sys.path.insert(0, '/opt/data')
import ai_drama_dl
from ai_drama_dl import get_url, aria2_download_async, verify_file, loop_run, CONCURRENCY

async def main():
    # 从上次结果里取缺失任务
    results = json.load(open('/opt/data/ai_drama_dl_result.json'))
    todo = [r for r in results if r['status'] in ('REQUEUE', 'RETRY', 'VERIFY_FAIL')]

    # 过滤掉已存在的
    tasks = []
    for r in todo:
        t = r['task']
        dest = os.path.join(t['dest_dir'], t['name'])
        if os.path.exists(dest) and os.path.getsize(dest) >= t['size'] * 0.99:
            continue
        tasks.append(t)

    print(f"补下 {len(tasks)} 个文件, {sum(t['size'] for t in tasks)/1024**3:.2f} GB, {CONCURRENCY} 并发")

    with open('/opt/data/.pikpak_token.json') as f:
        state = json.load(f)
    api = ai_drama_dl.PikPakApi.from_dict(state)

    # 信号量控制并发
    sem = asyncio.Semaphore(CONCURRENCY)
    results_out = []

    async def process(t):
        async with sem:
            dest = os.path.join(t['dest_dir'], t['name'])
            print(f"⬇️  {t['name'][:45]} ({t['size']/1024**2:.0f}MB)", flush=True)
            url = await get_url(api, t['id'])
            if not url:
                print(f"  ❌ URL失败"); return
            ok, elapsed, reason = await aria2_download_async(url, dest, t['size'])
            if not ok:
                # 重试一次
                print(f"  ⚠️ {reason}, 重试...")
                url = await get_url(api, t['id'])
                if url:
                    ok, elapsed, reason = await aria2_download_async(url, dest, t['size'])
            if ok:
                good, dur = await loop_run(verify_file, dest)
                speed = t['size']/elapsed/1024/1024 if elapsed > 0 else 0
                print(f"  ✅ {speed:.1f}MB/s ({elapsed:.0f}s)")
                results_out.append({'task': t, 'status': 'OK' if good else 'VERIFY_FAIL'})
            else:
                print(f"  ❌ 失败 ({reason})")
                results_out.append({'task': t, 'status': 'FAIL'})

    await asyncio.gather(*[process(t) for t in tasks])

    ok = sum(1 for r in results_out if r['status'] == 'OK')
    print(f"\n=== 补下完成: {ok}/{len(tasks)} ===")
    json.dump(results_out, open('/opt/data/ai_drama_dl_result2.json', 'w'), ensure_ascii=False, indent=1)

asyncio.run(main())

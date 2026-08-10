#!/usr/bin/env python3
"""AI短剧 全量下载器 v2 — aria2 4并发排队 + 文件级剧集识别 + 去重

规则:
1. 只下载视频文件 (mp4/mkv/mov/avi/wmv/flv/ts/m4v/webm)
2. 文件名含《标题》→ 用标题作为剧集归属（混入其他剧集的摘出来单独建文件夹）
3. 无书名号的 → 按所在文件夹归属
4. 名字相近的剧集合并 (古寺艳鬼录/G-古寺艳鬼录/古寺艳鬼录 1-10)
5. aria2 下载, 同时 4 个, 其余排队
6. 去重: 完全同名的文件 (去噪后) 只保留最大
"""
import json, os, re, sys, time, shutil, asyncio, subprocess
from collections import defaultdict

sys.path.insert(0, '/opt/data/.venv/lib/python3.13/site-packages')
from pikpakapi import PikPakApi

VIDEO_EXT = {'.mp4', '.mkv', '.mov', '.avi', '.wmv', '.flv', '.ts', '.m4v', '.webm'}
MANIFEST = '/opt/data/ai_drama_manifest.json'
DEST_ROOT = '/opt/data/PikPak/AI短剧'
ARIA2 = '/opt/data/aria2c'
CONCURRENCY = 4
SLOW_THRESHOLD = 200 * 1024  # 0.2 MB/s 以下视为慢节点（走代理时速度上限低）
SLOW_CHECKS = 2              # 连续 2 次(30s)低于阈值 → 立即换节点

# ============ 名称规范化 ============
def norm_name(name):
    """规范化文件名: 去扩展名、去序号、去噪"""
    n = os.path.splitext(name)[0]
    n = re.sub(r'[（(]\d+[)）]', '', n)
    n = re.sub(r'_\d{8}_\d{6}_\w+', '', n)
    n = re.sub(r'[_\- ]*wm[_\- ]*', '', n, flags=re.I)
    n = re.sub(r'[_\- ]+', ' ', n)
    return n.strip().lower()

def norm_drama(name):
    """规范化剧集名: 去前缀字母、去集数、去符号 → 用于合并判断"""
    n = name.strip()
    n = re.sub(r'^[GXMD]\s*[-_－]\s*', '', n)
    n = re.sub(r'^【(I_?No\.?\s*\d+)】', '', n)
    n = re.sub(r'^《|》$', '', n)
    n = re.sub(r'[\d\-]+集?$', '', n)
    n = re.sub(r'[\s\d\-\+]+$', '', n)
    n = re.sub(r'[《》\[\]【】()（）,.，。]', '', n)
    n = re.sub(r'\s+[A-Za-z].*$', '', n)
    return n.strip()

def title_from_name(name):
    """从文件名提取《标题》中的剧集名, 无则 None"""
    base = os.path.splitext(name)[0]
    m = re.search(r'《([^》]+)》', base)
    if m:
        return m.group(1).strip()
    return None

def edit_distance(a, b):
    if len(a) > len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j-1] + 1, prev[j-1] + (ca != cb)))
        prev = cur
    return prev[-1]

def similar(a, b):
    """两剧集名是否相近（可合并）"""
    if not a or not b:
        return False
    if a == b:
        return True
    if len(a) >= 3 and len(b) >= 3:
        shorter, longer = (a, b) if len(a) <= len(b) else (b, a)
        if shorter in longer and len(shorter) / len(longer) >= 0.6:
            return True
    if len(a) >= 4 and len(b) >= 4 and abs(len(a) - len(b)) <= 1 and edit_distance(a, b) == 1:
        return True
    return False

# ============ 加载与过滤 ============
def load_manifest():
    data = json.load(open(MANIFEST))
    return data['files'], data['folders']

def filter_videos(files):
    return [f for f in files if f['ext'] in VIDEO_EXT]

def get_src_drama(f):
    parts = f['path'].split('/')
    return parts[1] if len(parts) > 1 else '(根目录)'

# ============ 文件级剧集识别 ============
def assign_file_drama(f, all_src_names):
    """决定文件属于哪个剧集
    1. 文件名有《标题》→ 标题即剧集名
    2. 无标题 → 所在文件夹名
    3. 若标题与所在文件夹相似 → 用文件夹名(合并)
    """
    src = get_src_drama(f)
    title = title_from_name(f['name'])
    if title:
        # 标题与所在文件夹相似 → 归属文件夹；否则独立成新剧集
        if similar(norm_drama(title), norm_drama(src)):
            return src
        return title
    return src

def build_plan():
    files, folders = load_manifest()
    videos = filter_videos(files)
    print(f"视频总数: {len(videos)}, {sum(f['size'] for f in videos)/1024**3:.2f} GB")

    # 先按文件级剧集识别分组（不合并，纯归属）
    drama_files = defaultdict(list)
    for v in videos:
        drama_files[assign_file_drama(v, None)].append(v)
    print(f"文件级归属后剧集数: {len(drama_files)}")

    # 合并相近剧集
    names = sorted(drama_files.keys())
    parent = {n: n for n in names}
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for i in range(len(names)):
        for j in range(i+1, len(names)):
            if similar(norm_drama(names[i]), norm_drama(names[j])):
                union(names[i], names[j])

    groups = defaultdict(list)
    for n in names:
        groups[find(n)].append(n)

    plan = defaultdict(list)
    for root, members in groups.items():
        best = max(members, key=len)
        for m in members:
            for v in drama_files[m]:
                plan[best].append(v)

    # 去重（组内同名文件只留最大）
    result = []
    removed = 0
    seen = defaultdict(list)
    for dest, flist in plan.items():
        for f in flist:
            seen[(dest, norm_name(f['name']))].append(f)
    dedup_plan = defaultdict(list)
    for (dest, _), items in seen.items():
        items.sort(key=lambda x: x['size'], reverse=True)
        dedup_plan[dest].append(items[0])
        removed += len(items) - 1

    tasks = []
    for dest, flist in sorted(dedup_plan.items()):
        for f in flist:
            tasks.append({
                'src': f['path'],
                'dest_dir': os.path.join(DEST_ROOT, dest),
                'name': f['name'],
                'id': f['id'],
                'size': f['size'],
            })
    total = sum(t['size'] for t in tasks)
    print(f"去重: 去掉 {removed} 个")
    print(f"最终: {len(tasks)} 个文件, {len(dedup_plan)} 个剧集, {total/1024**3:.2f} GB")
    return tasks

# ============ 下载执行 ============
async def get_url(api, fid, retries=3):
    for i in range(retries):
        try:
            info = await api.get_download_url(fid)
            url = info.get('web_content_link', '')
            if url:
                return url
        except Exception as e:
            print(f"  ⚠️ get_url 失败 {i+1}/{retries}: {e}")
            await asyncio.sleep(2)
    return None

def aria2_download(url, dest_file):
    os.makedirs(os.path.dirname(dest_file), exist_ok=True)
    env = dict(os.environ)
    env['LD_LIBRARY_PATH'] = '/opt/data' + (':' + env['LD_LIBRARY_PATH'] if env.get('LD_LIBRARY_PATH') else '')
    cmd = [
        ARIA2,
        '--max-connection-per-server=8', '--split=8', '--min-split-size=8M',
        '--continue=true', '--max-tries=3', '--retry-wait=3',
        '--timeout=120', '--connect-timeout=30',
        '--all-proxy=http://127.0.0.1:10808',
        '--console-log-level=warn',
        '--dir', os.path.dirname(dest_file),
        '--out', os.path.basename(dest_file),
        url,
    ]
    t0 = time.time()
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, env=env)

    # 慢速监测: 每 15s 检查文件大小增长, 连续 SLOW_CHECKS 次(30s) < SLOW_THRESHOLD → kill 返回 SLOW
    slow_count = 0
    prev_size = -1
    last_size_check = 0
    while proc.poll() is None:
        time.sleep(3)
        if time.time() - last_size_check >= 15:
            last_size_check = time.time()
            cur = os.path.getsize(dest_file) if os.path.exists(dest_file) else 0
            if prev_size >= 0:
                delta = cur - prev_size
                if delta < SLOW_THRESHOLD * 15:
                    slow_count += 1
                else:
                    slow_count = 0
            prev_size = cur
            if slow_count >= SLOW_CHECKS:
                proc.kill()
                proc.wait()
                for p in [dest_file, dest_file + '.aria2']:
                    if os.path.exists(p):
                        os.remove(p)
                return False, time.time() - t0, 'SLOW'

    dt = time.time() - t0
    rc = proc.returncode
    return rc == 0, dt, 'OK' if rc == 0 else 'FAIL'

def verify_file(path):
    r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                        '-of', 'default=noprint_wrappers=1:nokey=1', path],
                       capture_output=True, text=True, timeout=60)
    out = r.stdout.strip()
    if not out:
        return False, "ffprobe 无输出"
    try:
        float(out)
        return True, out
    except ValueError:
        return False, out

async def worker(api, queue, results, sem, stats):
    while True:
        task = await queue.get()
        if task is None:
            break
        async with sem:
            try:
                await process_one(api, task, results, stats)
            except Exception as e:
                results.append({'task': task, 'status': 'ERROR', 'msg': str(e)})
                print(f"  ❌ {task['name']}: {e}")
        queue.task_done()
async def aria2_download_async(url, dest_file):
    """async 包装: aria2 是阻塞 subprocess, 用 to_thread 避免阻塞事件循环"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, aria2_download, url, dest_file)

async def process_one(api, task, results, stats):
    fname = task['name']
    dest_file = os.path.join(task['dest_dir'], fname)
    stats['done'] += 1

    # 跳过已完整下载的文件（断点续传）
    if os.path.exists(dest_file):
        sz = os.path.getsize(dest_file)
        if sz >= task['size'] * 0.99:  # 大小匹配(容差1%)
            results.append({'task': task, 'status': 'SKIP'})
            print(f"[{stats['done']}/{stats['total']}] ⏭️  已存在跳过: {fname[:45]} ({sz/1024**2:.0f}MB)", flush=True)
            return

    print(f"[{stats['done']}/{stats['total']}] ⬇️  {fname[:50]} ({task['size']/1024**2:.0f}MB)", flush=True)

    url = await get_url(api, task['id'])
    if not url:
        results.append({'task': task, 'status': 'URL_FAIL'})
        print(f"  ❌ 获取直链失败: {fname}")
        return

    # 下载, SLOW 时立即换 URL 重试(最多3次)
    ok, elapsed, reason = await aria2_download_async(url, dest_file)
    attempt = 1
    while not ok and reason == 'SLOW' and attempt < 3:
        print(f"  ⚠️ 慢节点({attempt}/3), 立即换 URL: {fname[:40]}", flush=True)
        url = await get_url(api, task['id'])
        if not url:
            break
        ok, elapsed, reason = await aria2_download_async(url, dest_file)
        attempt += 1

    if not ok:
        # 重试计数（SLOW 或 FAIL 都累计）
        attempts = task.get('attempts', 1)
        if reason == 'SLOW':
            # 3 次都慢节点: 放回队列尾部, 稍后重试(可能分到快节点)
            if attempts < 3:
                stats['slow_requeue'] += 1
                task['attempts'] = attempts + 1
                results.append({'task': task, 'status': 'REQUEUE'})
                print(f"  🔄 慢节点×{attempts}, 重新排队: {fname[:40]} (第{stats['slow_requeue']}个)", flush=True)
                await stats['queue'].put(task)
            else:
                results.append({'task': task, 'status': 'DL_FAIL', 'reason': reason})
                print(f"  ❌ 下载失败(重试3次仍慢): {fname} ({reason})")
        else:
            # FAIL: 非慢速错误(超时/断连等), 重排队最多2次
            if attempts < 3:
                task['attempts'] = attempts + 1
                results.append({'task': task, 'status': 'RETRY'})
                print(f"  🔄 下载失败({reason}), 重新排队({attempts}/3): {fname[:40]}", flush=True)
                await stats['queue'].put(task)
            else:
                results.append({'task': task, 'status': 'DL_FAIL', 'reason': reason})
                print(f"  ❌ 下载失败(重试3次): {fname} ({reason})")
        return

    good, dur = await loop_run(verify_file, dest_file)
    speed = task['size'] / elapsed / 1024 / 1024 if elapsed > 0 else 0
    if good:
        results.append({'task': task, 'status': 'OK', 'duration': dur})
        stats['bytes_ok'] += task['size']
        # 累计速度估算: 用总已完成字节/总耗时
        elapsed_total = time.time() - stats['t0']
        avg_speed = stats['bytes_ok'] / elapsed_total / 1024 / 1024 if elapsed_total > 0 else 0
        remaining = (stats['total_bytes'] - stats['bytes_ok']) / 1024**3
        eta = remaining / avg_speed / 3600 if avg_speed > 0.001 else 0
        print(f"  ✅ {speed:.1f}MB/s ({elapsed:.0f}s) 累计{avg_speed:.1f}MB/s 剩余{remaining:.0f}GB ETA~{eta:.1f}h", flush=True)
    else:
        results.append({'task': task, 'status': 'VERIFY_FAIL'})
        print(f"  ❌ 校验失败: {fname} ({dur})")

async def loop_run(fn, *args):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, fn, *args)

async def main():
    tasks = build_plan()
    if not tasks:
        print("无任务")
        return

    stats = {
        'total': len(tasks),
        'done': 0,
        'total_bytes': sum(t['size'] for t in tasks),
        'bytes_ok': 0,
        'speed_avg': 0,
        't0': time.time(),
        'slow_requeue': 0,
    }
    print(f"\n开始下载: {len(tasks)} 个文件, {CONCURRENCY} 并发")
    t0 = time.time()

    with open('/opt/data/.pikpak_token.json') as f:
        state = json.load(f)
    api = PikPakApi.from_dict(state)

    queue = asyncio.Queue()
    stats['queue'] = queue
    for t in tasks:
        await queue.put(t)
    for _ in range(CONCURRENCY):
        await queue.put(None)

    sem = asyncio.Semaphore(CONCURRENCY)
    results = []
    workers = [asyncio.create_task(worker(api, queue, results, sem, stats)) for _ in range(CONCURRENCY)]
    await asyncio.gather(*workers)

    dt = time.time() - t0
    ok = sum(1 for r in results if r['status'] == 'OK')
    fail = len(results) - ok
    print(f"\n=== 完成: {ok}/{len(results)} 成功, {fail} 失败, 用时 {dt/60:.1f}min ===")
    json.dump(results, open('/opt/data/ai_drama_dl_result.json', 'w'), ensure_ascii=False, indent=1)

if __name__ == '__main__':
    asyncio.run(main())

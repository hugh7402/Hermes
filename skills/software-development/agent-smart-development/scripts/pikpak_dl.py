#!/usr/bin/env python3
"""
PikPak WebDAV 多线程分段下载器 (类似 Neat Download Manager)
原理：用 rclone cat --offset --count 并发下载多个分片，最后合并

用法：
  python3 pikpak_dl.py <文件名>
  python3 pikpak_dl.py NSFS-484.mp4

注意：
  - 本脚本通过 rclone 读取文件，不走代理
  - PikPak WebDAV 对多线程有 503 限流，实际速度取决于服务器IP
  - 如果是本地 PC，用 Neat Download Manager 更快（~5 MB/s）
"""
import json, os, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

RCLONE = "/tmp/rclone"
REMOTE = "pikpak:/Inbox-JAV"
LOCAL = "/opt/data/PikPak/Inbox-JAV/"
THREADS = 8
CHUNK_MB = 512
MAX_RETRIES = 3
RETRY_DELAY = 5

def log(msg):
    print(msg, flush=True)

def get_size(filename):
    for _ in range(3):
        r = subprocess.run([RCLONE, "size", f"{REMOTE}/{filename}", "--json"],
                           capture_output=True, text=True, timeout=30)
        if r.returncode == 0:
            return json.loads(r.stdout)["bytes"]
        log(f"  ⚠️ 获取大小失败，重试...")
        time.sleep(10)
    raise RuntimeError(f"获取文件大小失败: {r.stderr[:200]}")

def dl_chunk(filename, start, end, idx, total_chunks):
    part = f"{LOCAL}{filename}.part{idx}"
    need = end - start
    if os.path.exists(part) and os.path.getsize(part) == need:
        return idx, need, 0, True
    offset = start
    if os.path.exists(part):
        got = os.path.getsize(part)
        if got > 0 and got < need:
            offset = start + got
            need = end - offset
    for attempt in range(MAX_RETRIES):
        t0 = time.time()
        cmd = [RCLONE, "cat", f"{REMOTE}/{filename}",
               "--offset", str(offset), "--count", str(need)]
        mode = "ab" if offset > start else "wb"
        try:
            with open(part, mode) as f:
                subprocess.run(cmd, stdout=f, stderr=subprocess.DEVNULL,
                               timeout=600, check=True)
            sz = os.path.getsize(part)
            el = time.time() - t0
            sp = (sz - max(0, offset - start)) / el / 1024 / 1024 if el > 0 else 0
            return idx, sz, sp, True
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                log(f"  [{idx+1}/{total_chunks}] ⚠️ 重试 {attempt+1}: {str(e)[:60]}")
                time.sleep(RETRY_DELAY)
            else:
                log(f"  [{idx+1}/{total_chunks}] ❌ 失败: {str(e)[:80]}")
                return idx, 0, 0, False

def merge(filename, n_chunks):
    final = f"{LOCAL}{filename}"
    log(f"\n  🔗 合并 {n_chunks} 个分片...")
    with open(final, "wb") as out:
        for i in range(n_chunks):
            part = f"{LOCAL}{filename}.part{i}"
            if os.path.exists(part):
                with open(part, "rb") as f:
                    out.write(f.read())
                os.remove(part)
    sz = os.path.getsize(final)
    log(f"  ✅ {filename} ({sz/1024**3:.2f} GB)")
    return sz

def download(filename):
    for f in Path(LOCAL).glob(f"{filename}.*.partial"):
        f.unlink(missing_ok=True)
    log(f"📥 获取文件大小...")
    total = get_size(filename)
    cs = CHUNK_MB * 1024 * 1024
    n_chunks = (total + cs - 1) // cs
    n_workers = min(THREADS, n_chunks)
    log(f"📥 {filename} ({total/1024**3:.2f} GB) {n_workers}线程")
    chunks = [(filename, i*cs, min((i+1)*cs, total), i, n_chunks) for i in range(n_chunks)]
    done, speeds = 0, []
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=n_workers) as ex:
        fut = {ex.submit(dl_chunk, *c): c[3] for c in chunks}
        for f in as_completed(fut):
            idx, sz, sp, ok = f.result()
            if ok: done += sz
            if sp > 0: speeds.append(sp)
            avg = sum(speeds)/len(speeds) if speeds else 0
            tag = "✅" if ok else "❌"
            log(f"  [{idx+1}/{n_chunks}] {tag} {sz/1024**2:.0f}MB @ {sp:.1f}MB/s — {done*100/total:.0f}% ({avg:.1f}MB/s avg)")
    merge(filename, n_chunks)
    t = time.time() - t0
    avg = total / t / 1024 / 1024 if t > 0 else 0
    log(f"  ⏱ {t:.0f}s ({t/60:.1f}min) | 📊 平均 {avg:.1f} MB/s")

if __name__ == "__main__":
    files = sys.argv[1:] if len(sys.argv) > 1 else []
    if not files:
        log("用法: python3 pikpak_dl.py <文件名1> [文件名2 ...]")
        sys.exit(1)
    for f in files:
        download(f)
        log("")

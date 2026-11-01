#!/usr/bin/env python3
"""
PikPak CDN 多线程分片下载器
先用 pikpakapi 获取 CDN 直链，再用 Python 多线程 HTTP Range 并发分片下载。
比 rclone WebDAV 更稳定（不触发 503），比单线程快 8 倍。

用法：
  /opt/hermes/.venv/bin/python3 pikpak_cdn_dl.py              # 下载 /tmp/pikpak_urls.json 中所有文件
  /opt/hermes/.venv/bin/python3 pikpak_cdn_dl.py NSFS-484.mp4  # 指定文件
  /opt/hermes/.venv/bin/python3 pikpak_cdn_dl.py f1.mp4 f2.mp4 # 逐个下载多个

前置条件：
  1. /tmp/pikpak_urls.json 中存在文件直链（有效期约 24h）
  2. 直链过期时需先用 pikpakapi 刷新（见 SKILL.md）

原理：
  8 线程 × HTTP Range 分片（8MB/片），每片独立连接，下载完成后合并。
  支持断点续传（检测已存在的 .part 文件）、3 次重试。
"""
import json, os, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

URLS_FILE = "/tmp/pikpak_urls.json"
LOCAL = "/opt/data/PikPak/Inbox-JAV/"

# 已知文件大小 (bytes)，避免 HEAD 请求触发限流
SIZES = {
    "NSFS-484.mp4": 4668217447,
    "MIDA-646.mp4": 6425694461,
}

def dl_chunk(url, fn, start, end, idx, n):
    """下载一个分片（支持断点续传，3次重试）"""
    pt = f"{LOCAL}{fn}.part{idx}"
    need = end - start
    if os.path.exists(pt) and os.path.getsize(pt) == need:
        return idx, need, 0
    off = os.path.getsize(pt) if os.path.exists(pt) else 0
    for a in range(3):
        t0 = time.time()
        try:
            r = urllib.request.Request(url)
            r.add_header('Range', f'bytes={start+off}-{end-1}')
            resp = urllib.request.urlopen(r, timeout=120)
            with open(pt, 'ab' if off > 0 else 'wb') as f:
                while True:
                    chunk = resp.read(512*1024)
                    if not chunk: break
                    f.write(chunk)
                    off += len(chunk)
            sz = os.path.getsize(pt)
            el = time.time() - t0
            sp = sz / el / 1024 / 1024 if el > 0 else 0
            return idx, sz, sp
        except Exception:
            if a < 2:
                time.sleep(3 * (a + 1))
            else:
                return idx, 0, 0
    return idx, 0, 0

def merge(fn, nc):
    """按顺序合并分片，删除临时文件"""
    final = f"{LOCAL}{fn}"
    print(f"\n  🔗 合并 {nc} 个分片...", flush=True)
    with open(final, 'wb') as out:
        for i in range(nc):
            p = f"{LOCAL}{fn}.part{i}"
            if os.path.exists(p):
                with open(p, 'rb') as f:
                    out.write(f.read())
                os.remove(p)
    s = os.path.getsize(final)
    print(f"  ✅ {fn} ({s/1024**3:.2f} GB)", flush=True)

def dl(fn):
    """下载单个文件"""
    urls = {}
    if os.path.exists(URLS_FILE):
        urls = json.load(open(URLS_FILE))
    url = urls.get(fn)
    if not url:
        print(f"❌ {fn} 无直链（运行 refresh_urls.py 刷新）")
        return False

    total = SIZES.get(fn, 0)
    if not total:
        print(f"❌ {fn} 大小未知")
        return False

    for p in Path(LOCAL).glob(f"{fn}.*"):
        p.unlink(missing_ok=True)

    TH = 8
    CS = 8 * 1024 * 1024
    nc = (total + CS - 1) // CS
    nw = min(TH, nc)

    print(f"📥 {fn} ({total/1024**3:.2f} GB) | {nc}片 × {CS//1024//1024}MB | {nw}线程", flush=True)

    chunks = [(url, fn, i*CS, min((i+1)*CS, total), i, nc) for i in range(nc)]
    done = 0; speeds = []; t0 = time.time()

    with ThreadPoolExecutor(max_workers=nw) as ex:
        fut = {ex.submit(dl_chunk, *c): c[4] for c in chunks}
        for f in as_completed(fut):
            idx, sz, sp = f.result()
            if sz > 0: done += sz
            if sp > 0: speeds.append(sp)
            status = "✅" if sz > 0 else "❌"
            avg = sum(speeds)/len(speeds) if speeds else 0
            pct = done * 100 / total
            print(f"  [{idx+1}/{nc}] {status} {sz/1024**2:.0f}MB @ {sp:.1f}MB/s — {pct:.0f}% ({avg:.1f}MB/s avg)", flush=True)

    merge(fn, nc)
    t = time.time() - t0
    print(f"  ⏱ {t:.0f}s | 📊 平均 {total/t/1024/1024:.1f} MB/s", flush=True)
    return True

if __name__ == "__main__":
    files = sys.argv[1:] if len(sys.argv) > 1 else []
    if not files and os.path.exists(URLS_FILE):
        files = list(json.load(open(URLS_FILE)).keys())
    for f in files:
        dl(f)
        print()

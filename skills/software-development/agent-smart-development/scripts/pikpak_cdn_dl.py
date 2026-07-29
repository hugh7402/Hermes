#!/usr/bin/env python3
"""
PikPak CDN 多线程分片下载器
用法: python3 pikpak_cdn_dl.py [文件名1 文件名2 ...]
     不传参数则下载 /tmp/pikpak_urls.json 中所有文件

流程:
  1. 读取 /tmp/pikpak_urls.json 中的 CDN 直链
  2. 8 线程并发 HTTP Range 分片下载（8MB/片）
  3. 完成后自动合并

前置:
  先获取直链: python3 get_pikpak_urls.py
  或手动执行:
    PikPakApi.get_download_url(file_id) → links[].url
    存到 /tmp/pikpak_urls.json
"""
import json, os, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

URL_FILE = "/tmp/pikpak_urls.json"
LOCAL = "/opt/data/PikPak/Inbox-JAV/"

# 已知文件大小 (bytes) — HEAD 可能不返回 Content-Length
SIZES = {
    "NSFS-484.mp4": 4668217447,
    "MIDA-646.mp4": 6425694461,
}

def dl_chunk(url, fn, start, end, idx, n):
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
        except Exception as e:
            if a < 2:
                time.sleep(3 * (a + 1))
            else:
                return idx, 0, 0
    return idx, 0, 0

def merge(fn, nc):
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
    with open(URL_FILE) as f:
        urls = json.load(f)
    url = urls.get(fn)
    if not url:
        print(f"❌ {fn} 无直链 (检查 {URL_FILE})", flush=True)
        return False
    total = SIZES.get(fn, 0)
    if not total:
        print(f"❌ {fn} 大小未知 (补充 SIZES 字典)", flush=True)
        return False
    for p in Path(LOCAL).glob(f"{fn}.*"):
        p.unlink(missing_ok=True)
    CS = 8 * 1024 * 1024
    nc = (total + CS - 1) // CS
    nw = min(8, nc)
    print(f"📥 {fn} ({total/1024**3:.2f} GB) | {nc}片 × {CS//1024//1024}MB | {nw}线程", flush=True)
    chunks = [(url, fn, i*CS, min((i+1)*CS, total), i, nc) for i in range(nc)]
    done, speeds, t0 = 0, [], time.time()
    with ThreadPoolExecutor(max_workers=nw) as ex:
        fut = {ex.submit(dl_chunk, *c): c[4] for c in chunks}
        for f in as_completed(fut):
            idx, sz, sp = f.result()
            if sz > 0: done += sz
            if sp > 0: speeds.append(sp)
            avg = sum(speeds)/len(speeds) if speeds else 0
            pct = done * 100 / total
            print(f"  [{idx+1}/{nc}] {'✅' if sz>0 else '❌'} {sz/1024**2:.0f}MB @ {sp:.1f}MB/s — {pct:.0f}% ({avg:.1f}MB/s avg)", flush=True)
    merge(fn, nc)
    t = time.time() - t0
    print(f"  ⏱ {t:.0f}s | 📊 平均 {total/t/1024/1024:.1f} MB/s", flush=True)
    return True

if __name__ == "__main__":
    files = sys.argv[1:] if len(sys.argv) > 1 else []
    if not files and os.path.exists(URL_FILE):
        with open(URL_FILE) as f:
            files = list(json.load(f).keys())
    for f in files:
        dl(f)
        print()

#!/usr/bin/env python3
"""SeedHub 抓取器 —— 内嵌中字影视资源的头号来源

2026-09-27 变形金刚全系列实战验证（7/8 部一次拿到 4K 国英多音轨+简繁中字磁链）。

用法:
    python3 seedhub_fetch.py search "变形金刚"            # 搜片 → 列 movie_id
    python3 seedhub_fetch.py versions <movie_id>          # 列全部版本（中字版排在前面）
    python3 seedhub_fetch.py magnet <movie_id> <seed_id>  # 解析 base64 磁链
    python3 seedhub_fetch.py best <movie_id>              # 自动挑 4K 国英多音轨+简繁中字最优版
    python3 seedhub_fetch.py best <movie_id> --all        # 列出全部中字候选+磁链

关键点:
  * 域名用 www.seedhub.cc（seedhub.icu 已死）
  * 搜索接口是 /s/<kw>，不是 /search?keyword=（后者 403）
  * 磁链是 **base64 编码**在 /link_start/ 页面里的，页面无 'magnet:' 明文
  * href 里 seed_id= 才是有 BT 种子；redirect_to=pan_id_ 只是网盘链接

⚠️ 输出量大时不要 `| head`（会 SIGPIPE 杀掉本进程，末尾写文件失效）——重定向到文件再读。
"""
import base64
import html
import json
import re
import subprocess
import sys
import urllib.parse

BASE = "https://www.seedhub.cc"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")
ZH = re.compile(r'中字|简繁|中英|国语|国英|中文')

# 各片页面的版本行结构
VER_RE = re.compile(
    r'title="([^"]{10,400})"[^>]*href="/link_start/\?seed_id=(\d+)[^"]*"'
    r'[^>]*>.*?</a>\s*/\s*<code class="size">([^<]*)</code>(.*?)</li>', re.S)
FEAT_RE = re.compile(r'<code class="seed-feature">([^<]*)</code>')


def get(url, ref=BASE + "/"):
    r = subprocess.run(["curl", "-s", "--noproxy", "*", "-m", "35", "-A", UA,
                        "-L", "-e", ref, url], capture_output=True, text=True)
    return r.stdout


def sizesz(s):
    """'36.86G' / '253.81MB' → 浮点 GB"""
    m = re.match(r'([\d.]+)\s*([KMGkmg]?)[Bb]?', s.strip())
    if not m:
        return 0.0
    v = float(m.group(1))
    u = m.group(2).upper()
    return v / 1024 if u == 'M' else (v / 1024 / 1024 if u == 'K' else v)


def search(kw):
    s = get(f"{BASE}/s/{urllib.parse.quote(kw)}")
    out, seen = [], set()
    for m in re.finditer(r'href="(/movies/(\d+)/?)"[^>]*>(.*?)</a>', s, re.S):
        if m.group(2) in seen:
            continue
        seen.add(m.group(2))
        t = html.unescape(re.sub(r'<[^>]+>', ' ', m.group(3)))
        out.append((m.group(2), re.sub(r'\s+', ' ', t).strip()))
    return out


def versions(mid):
    p = get(f"{BASE}/movies/{mid}/")
    vs, n_seed, n_pan = [], p.count('seed_id='), p.count('redirect_to=pan_id_')
    for m in VER_RE.finditer(p):
        name, sid, size, rest = m.group(1), m.group(2), m.group(3), m.group(4)
        vs.append({"title": html.unescape(name), "seed_id": sid, "size": size,
                   "gb": sizesz(size), "feats": FEAT_RE.findall(rest),
                   "zh": bool(ZH.search(name))})
    return vs, n_seed, n_pan


def magnet(mid, sid):
    p = get(f"{BASE}/link_start/?seed_id={sid}&movie_title=x", ref=f"{BASE}/movies/{mid}/")
    for b in re.findall(r'\b[A-Za-z0-9+/]{40,200}={0,2}\b', p):
        try:
            dec = base64.b64decode(b + "=" * (-len(b) % 4)).decode('utf-8', 'ignore')
            if dec.startswith('magnet:'):
                return dec
        except Exception:
            pass
    return None


def pick_best(vs):
    """按『规格匹配』而非『体积最大』挑：4K + 国英多音轨 + 简繁中字；
    同规格内挑体积大的。避免误选 60-77G 的 REMUX。"""
    cand = [v for v in vs if v['zh'] and ('2160p' in v['title'] or 'UHD' in v['title'])
            and ('国英多音轨' in v['title'] or '国英双' in v['title'] or '国英双语' in v['title'])]
    if not cand:
        cand = [v for v in vs if v['zh'] and ('2160p' in v['title'] or 'UHD' in v['title'])]
    if not cand:
        cand = [v for v in vs if v['zh']]
    # 规格标签归一：REMUX/原盘 视为更高一档体积，但用户偏好是"高清大版本"里的压制版
    non_remux = [v for v in cand if 'REMUX' not in v['title'].upper() and '原盘' not in v['title']]
    pool = non_remux or cand
    return max(pool, key=lambda z: z['gb'])


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    cmd = sys.argv[1]
    if cmd == 'search':
        for mid, t in search(sys.argv[2]):
            print(f"  id={mid:>7s}  {t[:100]}")
    elif cmd == 'versions':
        mid = sys.argv[2]
        vs, ns, npan = versions(mid)
        zh = sorted([v for v in vs if v['zh']], key=lambda z: -z['gb'])
        print(f"  版本 {len(vs)} 个 / 含中文字样 {len(zh)} 个 / seed_id={ns} pan_id={npan}")
        if ns == 0 and npan:
            print("  🚫 本页全是网盘链接（redirect_to=pan_id_），**拿不到 BT 磁链**，别在这里耗时间")
        for v in zh:
            print(f"  {v['size']:>10s}  {'/'.join(v['feats'])[:20]:22s} {v['title'][:110]}")
    elif cmd == 'magnet':
        print(magnet(sys.argv[2], sys.argv[3]) or "❌ 解析失败")
    elif cmd == 'best':
        mid = sys.argv[2]
        vs, ns, npan = versions(mid)
        if ns == 0:
            print(f"  🚫 无 BT 种子（seed_id=0，pan_id={npan}）→ 只能走网盘。如实告知用户。")
            return
        zh = sorted([v for v in vs if v['zh']], key=lambda z: -z['gb'])
        if '--all' in sys.argv:
            for v in zh[:12]:
                mg = magnet(mid, v['seed_id'])
                print(f"  {v['size']:>10s}  {v['title'][:100]}\n      {mg}")
            return
        b = pick_best(vs)
        if not b:
            print("  ✗ 无候选"); return
        print(f"  选中: {b['title']}\n  体积: {b['size']}  seed_id={b['seed_id']}")
        print(f"  磁链: {magnet(mid, b['seed_id'])}")
    else:
        print(__doc__)


if __name__ == '__main__':
    main()

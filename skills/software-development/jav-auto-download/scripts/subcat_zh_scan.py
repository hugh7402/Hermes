#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""扫 subtitlecat 某番号的全部详情页，挑出最好的中文 srt。

用法:
    subcat_zh_scan.py <番号> <输出目录> [视频时长秒数]

传片长是可选的，但**强烈建议传**：时间轴比对是唯一能拓下“别的番号的字幕”的判据。
退出码: 0 = 找到合格中文; 3 = 有字幕但全部不合格; 2 = 该番号无字幕; 1 = 网络失败。

本脚本内置的硬规则（全部是踩过的坑）:
  1. 缓存与中间文件**必须带番号**，否则下一个番号会拿到上一个番号的搜索页 → 假结论“无字幕”。
  2. 详情页输出文件**还要带页码**，否则某页 000 时会把上一页的旧内容当本页解析。
  3. subtitlecat 的 HTTP 000 是**常态**：搜索页、详情页、.srt 本体各重试 3 次（间隔 4s）再判死。
  4. 搜索是**模糊**的，必须按番号精确过滤页面（横杠/下划线/空格视为等价）。
  5. 质量三判据：汉字 > 1000、文本重复率 < 55%、时间轴尾点 ≥ 片长 90%。
     只看汉字数会被 aisubs.app 之类的 AI 自动翻译版骗过。
  6. `/subs/<页码>/` 必须从详情页原样照抄，不许自己拼。
"""
import re, sys, subprocess, pathlib, collections

CODE = sys.argv[1]
OUT = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else pathlib.Path('/tmp')
DUR = int(sys.argv[3]) if len(sys.argv) > 3 else 0

UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/120.0 Safari/537.36')
KEY = re.sub(r'[^A-Za-z0-9]', '', CODE).upper()


def norm(s):
    return re.sub(r'[^A-Za-z0-9]', '', s).upper()


def curl(url, outfile, ref=None, mtime=50, tries=3):
    """返回 (size, http_code)。res 非 200 时 size 不可信。"""
    for i in range(tries):
        cmd = ['curl', '-s', '--noproxy', '*', '--compressed',
               '--max-time', str(mtime), '-A', UA, '-o', outfile, '-w', '%{http_code}']
        if ref:
            cmd += ['-e', ref]
        cmd.append(url)
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=mtime + 25)
            code = (r.stdout or '').strip()
        except Exception:
            code = '000'
        size = pathlib.Path(outfile).stat().st_size if pathlib.Path(outfile).exists() else 0
        if code == '200' and size > 800:
            return size, code
        if i < tries - 1:
            import time; time.sleep(4)
    return size, code


def score(txt):
    han = len(re.findall(r'[\u4e00-\u9fff]', txt))
    kana = len(re.findall(r'[\u3040-\u309f\u30a0-\u30ff]', txt))
    arab = len(re.findall(r'[\u0600-\u06ff]', txt))
    lines = [l.strip() for l in txt.splitlines()
             if l.strip() and '-->' not in l and not l.strip().isdigit()]
    uniq = len(set(lines))
    dup = (1 - uniq / len(lines)) * 100 if lines else 100
    ts = re.findall(r'(\d{2}):(\d{2}):(\d{2})[.,]\d{3}\s*-->\s*(\d{2}):(\d{2}):(\d{2})[.,]\d{3}', txt)
    end = int(ts[-1][3]) * 3600 + int(ts[-1][4]) * 60 + int(ts[-1][5]) if ts else 0
    cov = (1 - abs(DUR - end) / DUR) * 100 if (DUR and ts) else (100 if not DUR else 0)
    ok = han > 1000 and dup < 55 and (not DUR or cov >= 90) and kana < 200
    return dict(han=han, kana=kana, arab=arab, n=len(lines), uniq=uniq, dup=dup,
                end=end, cov=cov, ok=ok, top=collections.Counter(lines).most_common(2))


print(f'=== {CODE} 中文字幕全扫 ===', flush=True)
CACHE = pathlib.Path(f'/tmp/_s_{KEY}.html')
sz, cd = curl(f'https://www.subtitlecat.com/index.php?search={CODE}&show=1000', str(CACHE))
if cd != '200' or sz < 10000:
    if CACHE.exists() and CACHE.stat().st_size > 10000:
        print(f'  ⚠️ 搜索页连抓 3 次失败，复用**本番号自己的**缓存 {CACHE.stat().st_size:,}B')
    else:
        sys.exit(f'  ❌ 搜索页取不到且无本番号缓存 → 无法判定有无字幕（不是“没有”）')
sp = CACHE.read_text('utf-8', 'ignore')

allpages = sorted(set(re.findall(r'(?:/)?(subs/\d+/[^"\'<>\s]+)', sp)))
pages = [p for p in allpages if KEY in norm(p)]
print(f'  详情页：搜索页 {len(allpages)} 个 → 精确匹配 {len(pages)} 个')
for p in pages:
    print(f'    {p}')
if not pages:
    print('  ℹ️ 精确匹配 0 个 = 该番号确实没字幕（注意：番号若只出现在页面 title/表单里不算条目）')
    sys.exit(2)

found = []
for pi, p in enumerate(pages, 1):
    url = 'https://www.subtitlecat.com/' + p
    DPF = f'/tmp/_sd_{KEY}_{pi}.html'
    sz, cd = curl(url, DPF, ref='https://www.subtitlecat.com/index.php')
    if cd != '200' or sz < 2000:
        print(f'  [{pi}] {p[-52:]} → 连抓 3 次仍失败（最后 {cd}），跳过')
        continue
    dp = pathlib.Path(DPF).read_text('utf-8', 'ignore')
    links = set(re.findall(r'href\s*=\s*["\']([^"\']*\.srt[^"\']*)["\']', dp))
    links |= set(re.findall(r'[^\'"<>\s]*\.srt[^\'"<>\s]*', dp))
    # 🚨 过滤必须锚定「语言后缀」，不能对整条路径做 zh 匹配：
    #    路径本身都带 "xxx.zh-cn(by transub)" 字样，`re.search(r'zh', x)` 会把
    #    .en.srt / .ar.srt / .th.srt 等 20 多种语种全部放行，逐一去抓纯属白耗时间
    #    （ABF-394 实测 26 个链接里只该试 3 个）。
    zh = sorted({x for x in links
                 if re.search(r'-(zh-CN|zh-TW|zh|orig)\.srt$', x, re.I) and len(x) > 8})
    print(f'  [{pi}] {p[-52:]} → {sz:,}B，中文/原版 {len(zh)} 个')
    for x in zh:
        if x.startswith('http'):
            tgt = x
        elif '%' in x:
            tgt = 'https://www.subtitlecat.com/' + x.lstrip('/')
        else:
            from urllib.parse import quote
            tgt = 'https://www.subtitlecat.com' + quote(x if x.startswith('/') else '/' + x)
        s2, c2 = curl(tgt, '/tmp/_ss.srt', ref=url, mtime=60)
        if c2 != '200' or s2 < 800:
            print(f'        ❌ {c2}  {x[-44:]}')
            continue
        txt = pathlib.Path('/tmp/_ss.srt').read_text('utf-8', 'ignore')
        s = score(txt)
        print(f"        {'✅' if s['ok'] else '❌'} 汉字{s['han']:5d} 重复{s['dup']:5.1f}% "
              f"尾点{s['end']//60:3d}分 覆盖{s['cov']:5.1f}%  {x[-44:]}")
        found.append((s['ok'], s, tgt, pathlib.Path('/tmp/_ss.srt').read_bytes()))

if not found:
    sys.exit('  ❌ 所有链接都抓不下来（网络问题，不是没字幕）')

found.sort(key=lambda r: (not r[0], -r[1]['han'], r[1]['dup'], -r[1]['cov']))
good, s, tgt, data = found[0]
out = OUT / f'{KEY.lower()}.srt'
out.write_bytes(data)
print(f"\n  落盘 → {out}  ({len(data):,}B 汉字 {s['han']} 重复 {s['dup']:.1f}% "
      f"时间轴尾点 {s['end']//60} 分)")
print(f'  来源: {tgt}')
if not good:
    print('  ⚠️ 最佳候选也不达标 —— 不要直接配上，先报给用户看是否接受')
    sys.exit(3)
sys.exit(0)

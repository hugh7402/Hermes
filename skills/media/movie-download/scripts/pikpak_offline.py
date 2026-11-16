#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PikPak 离线下载 + 递归完成判定 + 单个条目的文件清单

用法:
    python3 pikpak_offline.py <magnet|http://...> --expect 25.84
    python3 pikpak_offline.py --peek 八仙              # 只看已有条目，不下载

为什么需要它（手工写易错的两处）:
  * 递归统计必须返回 (GB, 视频数, 原始字节, 文件数) —— 只返 3 个值会在
    `s, v, n = await stat(...)` 处抛 `ValueError: too many values to unpack`。
  * 累加时**不要先转 GB 再累加又除一次**，否则总量恒显示 0.00 GB。
  * 离线结果常是文件夹，顶层 file_list 看到 kind=drive#folder / size=0，
    只看顶层会恒判「已完成」（顶层体积永远是 0）。必须递归两层。

完成判据: 累计字节 >= 预期 × 0.995 且视频数（>100MB）> 0；
         或连续 3 轮不增长且已有视频。广告文件（0 字节 .DOC/.MP4）不计入。
"""
import asyncio, json, os, sys
from pikpakapi import PikPakApi

TOKEN = '/opt/data/.pikpak_token.json'
VIDEO_MIN = 100 * 1024 * 1024


def arg(flag, default=None):
    return sys.argv[sys.argv.index(flag) + 1] if flag in sys.argv else default


async def login():
    old = json.load(open(TOKEN))
    c = PikPakApi(username=old['username'], password=old['password'],
                  device_id=old['device_id'])   # device_id 必须沿用旧的，换新会触发风控
    try:
        await c.login()
    except Exception as e:
        print('  login 异常:', e)
        c.access_token = old.get('access_token')
        c.refresh_token = old.get('refresh_token')
    d = c.to_dict() if hasattr(c, 'to_dict') else {}
    if d:
        old.update({k: v for k, v in d.items() if v})
        json.dump(old, open(TOKEN, 'w'), indent=2)
        os.chmod(TOKEN, 0o600)
    print('  ✅ 登录')
    return c


async def folder_id(c, name='Movie'):
    r = await c.file_list(size=100, parent_id='')
    for f in r.get('files', []):
        if f.get('name') == name and f.get('kind', '').endswith('folder'):
            return f['id']
    return None


async def stat_tree(c, fid, depth=0):
    """返回 (GB, 视频数, 原始字节, 文件数)；fid 可以是文件也可以是文件夹"""
    total = nvid = nfile = 0
    r = await c.file_list(size=200, parent_id=fid)
    for f in r.get('files', []):
        if f.get('kind', '').endswith('folder'):
            if depth < 2:
                g, v, b, n = await stat_tree(c, f['id'], depth + 1)
                nvid += v; total += b; nfile += n
            continue
        sz = int(f.get('size') or 0)
        total += sz; nfile += 1
        if sz > VIDEO_MIN:
            nvid += 1
    return total / 1024 ** 3, nvid, total, nfile


async def wait_done(c, fid, expect_gb, rounds=40):
    last, stable = -1, 0
    for i in range(rounds):
        await asyncio.sleep(15)
        gb, nvid, _b, nfile = await stat_tree(c, fid)
        print('    [%2d] %.2f GB / 预期 %.2f GB  视频 %d / 文件 %d'
              % (i + 1, gb, expect_gb, nvid, nfile))
        if gb >= expect_gb * 0.995 and nvid > 0:
            print('    ✅ 离线完成')
            return True
        if abs(gb - last) < 0.01:
            stable += 1
            if stable >= 3 and nvid > 0:
                print('    ⚠️ 连续 3 轮不增长，按完成处理')
                return True
        else:
            stable = 0
        last = gb
    print('    ⏳ 超时未完成，稍后重跑本脚本复查')
    return False


async def show(c, mid, kw):
    r = await c.file_list(size=200, parent_id=mid)
    for f in r.get('files', []):
        if kw and kw not in f.get('name', ''):
            continue
        print('\n  ■ %s  kind=%s' % (f.get('name'), f.get('kind')))
        if f.get('kind', '').endswith('folder'):
            gb, nvid, _b, nfile = await stat_tree(c, f['id'])
            rr = await c.file_list(size=200, parent_id=f['id'])
            for g in rr.get('files', []):
                sz = int(g.get('size') or 0)
                mark = '  ' if sz > VIDEO_MIN else '  (广告/跳过) '
                print('    %8.2f GB %s%s' % (sz / 1024 ** 3, mark, g.get('name')))
            print('    ── 合计 %.2f GB / 视频 %d / 文件 %d ──' % (gb, nvid, nfile))
        else:
            print('    %.2f GB' % (int(f.get('size') or 0) / 1024 ** 3))


async def main():
    c = await login()
    mid = await folder_id(c, 'Movie')
    if not mid:
        print('  ❌ 找不到 /Movie')
        return
    print('  /Movie =', mid)

    if '--peek' in sys.argv:
        await show(c, mid, arg('--peek', ''))
        return

    link = sys.argv[1]
    try:
        await c.offline_download(link, parent_id=mid)
        print('  ✅ 已提交离线')
    except Exception as e:
        print('  ⚠️ offline_download 异常（可能已存在）:', e)
    await wait_done(c, mid, float(arg('--expect', '0')))
    await show(c, mid, arg('--include', ''))


asyncio.run(main())

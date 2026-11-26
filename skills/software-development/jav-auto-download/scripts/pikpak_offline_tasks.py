#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""列出 PikPak 离线任务，并找出「死磁链」任务。

为什么需要这个脚本：
  死磁链的表现是 phase=PHASE_TYPE_RUNNING + progress=0 + msg=Saving，
  **看上去和「大文件还在离线中」一模一样**，但等多久都不会动。
  只看云端文件列表是看不出来的（文件夹根本没建出来），只有 offline_list() 能看到。
  而且重试会在列表里堆出一堆重复任务（实测同一番号堆 8 个、另一个堆 5 个）。

用法:
    python3 pikpak_offline_tasks.py            # 只列出（默认）
    python3 pikpak_offline_tasks.py --clean    # 列出后删掉 progress=0 的死任务
    python3 pikpak_offline_tasks.py --clean --min-age 600
                                               # 只删创建超过 600 秒的（给正常任务留机会）

注意:
  · delete_to_trash 后 file_list/offline_list 会短暂仍返回旧数据，属正常，别重复删。
  · 不要传空列表给 delete_tasks，会报 Request parameter error。
"""
import argparse
import asyncio
import datetime
import json
import pathlib
import sys

TOKEN = pathlib.Path('/opt/data/.pikpak_token.json')


def load_client():
    from pikpakapi import PikPakApi
    st = json.loads(TOKEN.read_text())
    c = PikPakApi(encoded_token=st.get('encoded_token', ''))
    c.access_token = st.get('access_token', '')
    c.refresh_token = st.get('refresh_token', '')
    c.user_id = st.get('user_id', '')
    c.device_id = st.get('device_id', '')
    return c


def age_seconds(task):
    """任务创建至今的秒数；时间解析不了就返回一个很大的数（视为老任务）。"""
    ct = str(task.get('created_time') or '')
    for fmt, cut in (('%Y-%m-%dT%H:%M:%S', 19), ('%Y-%m-%d %H:%M:%S', 19)):
        try:
            dt = datetime.datetime.strptime(ct[:cut], fmt)
            return max(0, (datetime.datetime.utcnow() - dt).total_seconds())
        except ValueError:
            continue
    return 10 ** 9


def is_dead(task, min_age):
    """死磁链：RUNNING 但 progress 恰为 0，且已过了观察期。"""
    if task.get('phase') != 'PHASE_TYPE_RUNNING':
        return False
    if task.get('progress') != 0:
        return False
    return age_seconds(task) >= min_age


async def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('--clean', action='store_true', help='删除判定为死磁链的任务')
    ap.add_argument('--min-age', type=int, default=300,
                    help='progress=0 且创建超过这么多秒才算死（默认 300）')
    args = ap.parse_args(argv)

    c = load_client()
    tasks = (await c.offline_list()).get('tasks', [])
    if not tasks:
        print('  离线任务列表为空')
        return 0

    print(f'  离线任务 {len(tasks)} 条（新的在前）：')
    dead = []
    for t in tasks:
        dead_flag = is_dead(t, args.min_age)
        if dead_flag:
            dead.append(t)
        mark = '💀' if dead_flag else '  '
        prog = t.get('progress')
        name = str(t.get('name', ''))[:56]
        msg = str(t.get('message') or '')[:28]
        print(f'    {mark} {str(t.get("phase", "")):22s} prog={prog!s:>4}  {name}  {msg}')

    print()
    if not dead:
        print(f'  ✅ 没有 progress=0 的死任务（判定阈值 {args.min_age}s）')
        return 0

    print(f'  💀 判定为死磁链 {len(dead)} 条')
    if not args.clean:
        print('     只列出，未删除。加 --clean 才删。')
        print('     处置：这些磁链重试也不会好，应换源（换 btih）或改用详情页两段式。')
        return 0

    ids = [t['id'] for t in dead if t.get('id')]
    if not ids:                       # 🚨 空列表会报 Request parameter error
        print('     ⚠️ 拿不到任务 id，跳过删除')
        return 1
    await c.delete_tasks(ids)
    print(f'  🗑  已提交删除 {len(ids)} 条')

    await asyncio.sleep(3)
    left = (await c.offline_list()).get('tasks', [])
    still = [t for t in left if is_dead(t, args.min_age)]
    # 列表是最终一致的，删完立刻查可能还在；隔几秒再看才是真结论
    print(f'  复核：剩 {len(left)} 条任务，其中判死的 {len(still)} 条')
    if still:
        print('     （若几秒后仍然存在再重跑一次 --clean；不要因为第一次还读到就重复删）')
    return 0


if __name__ == '__main__':
    sys.exit(asyncio.run(main(sys.argv[1:])))

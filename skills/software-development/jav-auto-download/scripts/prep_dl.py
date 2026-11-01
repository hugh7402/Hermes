#!/usr/bin/env python3
"""一条龙的云端准备：搜 javdb → 选版 → PikPak 离线 → 清广告 → 重命名 → 删空文件夹。

用法: python3 prep_dl.py <番号> "<完整新文件名.mp4>"

选版规则（用户口径）：
  · 只认 ≥2GB 的版本；体积最大者优先（清晰度优先）
  · 排除 -U（无码破解）；-UC 默认不选（标称中字实测多为日文，且体积偏小）
  · 若无 ≥2GB 版本，打印全部候选并退出码 2，交由用户决定

不碰本地文件，字幕另行补抓（fetch_sub_srt.sh）。
"""
import asyncio
import json
import pathlib
import re
import sys

sys.path.insert(0, '/opt/data')
import importlib.util

spec = importlib.util.spec_from_file_location('jm', '/opt/data/jav_manager.py')
jm = importlib.util.module_from_spec(spec)
sys.modules['jm'] = jm
spec.loader.exec_module(jm)

from pikpakapi import PikPakApi

VIDEO = {'.mp4', '.mkv', '.avi', '.wmv', '.mov', '.flv', '.ts', '.m4v', '.webm'}
SUB = {'.srt', '.ass', '.ssa'}


async def client():
    st = json.loads(pathlib.Path('/opt/data/.pikpak_token.json').read_text())
    c = PikPakApi(encoded_token=st.get('encoded_token', ''))
    c.access_token = st.get('access_token', '')
    c.refresh_token = st.get('refresh_token', '')
    c.user_id = st.get('user_id', '')
    c.device_id = st.get('device_id', '')
    return c


async def main():
    if len(sys.argv) < 3:
        raise SystemExit('用法: python3 prep_dl.py <番号> "<新文件名.mp4>"')
    code = sys.argv[1]
    new_name = sys.argv[2]
    if not new_name.lower().endswith('.mp4'):
        new_name += '.mp4'
    code_nh = code.replace('-', '').upper()

    def ensure_version_tag(nm, magnet_name):
        """把磁链里的版本标签（-C / -UC）补到番号后面。用户硬要求 -C 紧跟番号保留。"""
        m = re.search(r'-(UC|C)(?=[\s._\-]|$)', magnet_name, re.I)
        if not m:
            return nm
        tag = '-' + m.group(1).upper()
        parts = nm.split('-')
        if len(parts) < 2:
            return nm
        head = '-'.join(parts[:2])          # 番号 = 前缀-数字，例如 MIDA-783
        rest = nm[len(head):]
        if rest.upper().startswith(tag):
            return nm                        # 已有，不重复插
        rest = re.sub(r'^-(UC|C)(?=-|\.| )', '', rest, flags=re.I)
        return head + tag + rest

    href = jm.search_javdb(code)
    print(f'  详情页: {href}')
    if not href:
        raise SystemExit('javdb 未搜到该番号')

    mags = jm.get_magnets(href)
    print(f'\n=== {code} 磁链 {len(mags)} 条（-U 已过滤）===')
    for m in sorted(mags, key=lambda x: -x['size_bytes']):
        print(f"  {m['size_bytes'] / 1024 ** 3:6.2f}GB  {m['file_count']}个文件  "
              f"字幕={int(m['has_subtitle'])}  {m['name'][:48]}")

    cand = [m for m in mags if m['size_bytes'] >= 2 * 1024 ** 3
            and '-UC' not in m['name'].upper()]
    if not cand:
        print('\n  没有 >=2GB 的候选版本，需要用户决定（未提交离线）')
        return 2

    # 选版：体积最大者为基准；若存在 -C（内嵌中文字幕）版且体积不低于最大者的 90%，优先选 -C。
    # 理由：-C 是用户明确要保留的内嵌字幕版，体积差 10% 以内不值得为画质放弃字幕。
    biggest = max(cand, key=lambda x: x['size_bytes'])
    c_versions = [m for m in cand
                  if re.search(r'-[Cc](?=[\s._\-]|$)', m['name'])
                  and m['size_bytes'] >= biggest['size_bytes'] * 0.90]
    if c_versions:
        pick = max(c_versions, key=lambda x: x['size_bytes'])
        print(f"\n  优先选内嵌字幕 -C 版（体积 ≥ 最大版的 90%）")
    else:
        pick = biggest
    print(f"  选定: {pick['name']} / {pick['size_bytes'] / 1024 ** 3:.2f}GB / {pick['file_count']}个文件")

    # 版本标签跟随番号：磁链是 -C/-UC 版时，文件名里必须保留
    final_name = ensure_version_tag(new_name, pick['name'])
    if final_name != new_name:
        print(f'  已按磁链补版本标签: {final_name}')
    new_name = final_name

    c = await client()
    inbox = (await c.path_to_id('/Inbox-JAV'))[0]['id']
    task = await c.offline_download(pick['url'], parent_id=inbox)
    print(f"  离线已提交 task={task.get('task', {}).get('id')}")

    folder = None
    kids = []
    for i in range(15):
        await asyncio.sleep(6)
        files = (await c.file_list(parent_id=inbox))['files']
        hit = [f for f in files if f['kind'] == 'drive#folder'
               and code_nh in f['name'].upper().replace('-', '')]
        if hit:
            folder = hit[0]
            kids = (await c.file_list(parent_id=folder['id']))['files']
            done = sum(1 for k in kids if str(k.get('phase', '')).startswith('PHASE_TYPE_COMPLETE'))
            print(f"  第 {(i + 1) * 6}s: {folder['name'][:34]} {done}/{len(kids)}")
            if kids and done == len(kids):
                break
    if not folder:
        raise SystemExit('未见离线文件夹，可能仍在离线中，稍后重跑本脚本可续')

    keep, dele, subs = [], [], []
    print('\n=== 决策表 ===')
    for k in kids:
        nm = k['name']
        ext = pathlib.Path(nm).suffix.lower()
        gb = int(k.get('size') or 0) / 1024 ** 3
        is_v = ext in VIDEO and code_nh in nm.upper().replace('-', '') and gb > 0.5
        is_s = ext in SUB
        print(f"  {'KEEP' if (is_v or is_s) else 'DEL ':4s} {gb:7.2f}GB  {nm[:58]}")
        if is_v:
            keep.append(k)
        elif is_s:
            keep.append(k)
            subs.append(k)
        else:
            dele.append(k)

    vids = [k for k in keep if k not in subs]
    if not vids:
        raise SystemExit('文件夹里没有含番号的主视频，请人工检查')
    main_vid = max(vids, key=lambda k: int(k.get('size') or 0))

    if dele:
        await c.delete_to_trash([k['id'] for k in dele])
        print(f'  已删 {len(dele)} 个无用文件')
    await c.file_batch_move(ids=[main_vid['id']] + [x['id'] for x in subs], to_parent_id=inbox)
    print(f'  已移出主视频 + {len(subs)} 个字幕文件')
    await asyncio.sleep(2)
    await c.file_rename(id=main_vid['id'], new_file_name=new_name)
    print(f'  已重命名 -> {new_name}')
    for s in subs:
        ext = pathlib.Path(s['name']).suffix
        await c.file_rename(id=s['id'], new_file_name=new_name[:-4] + ext)
    await asyncio.sleep(1)
    left = (await c.file_list(parent_id=folder['id']))['files']
    if not left:
        await c.delete_to_trash([folder['id']])
        print('  空文件夹已删')

    print('\n=== 云端 Inbox-JAV ===')
    for f in (await c.file_list(parent_id=inbox))['files']:
        print(f"  {int(f.get('size') or 0) / 1024 ** 3:6.2f}GB  {f['name'][:52]}")
    return 0


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))

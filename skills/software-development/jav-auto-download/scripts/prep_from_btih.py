#!/usr/bin/env python3
"""云端准备（直接用 btih，完全不碰 javdb）：PikPak 离线 → 清广告 → 移出 → 改名 → 删空文件夹。

为什么需要它：javdb 对机房 IP 限流极严（每 IP 1-3 个请求就 403），批量选版时
prep_dl.py 会重跑一遍 javdb 搜索，必然卡在读流上。选版一旦完成（拿到 btih），
PikPak 阶段就不要再访问 javdb。

用法:
    python3 prep_from_btih.py <番号>
    读 /opt/data/.tmp_tests/batch9_result.json，每条需要：
      code   番号，如 ATID-711
      target 用户给的目标文件名（含后缀描述，不含 .mp4 也行）
      pick   {btih, gb, files, name, why}

起法（venv 里才有 pikpakapi，不要用系统 python）:
    export PATH=/opt/data/.venv/bin:$PATH && python3 prep_from_btih.py ATID-711
"""
import asyncio
import json
import pathlib
import re
import sys

sys.path.insert(0, '/opt/data')
from pikpakapi import PikPakApi

RESULT = pathlib.Path('/opt/data/.tmp_tests/batch9_result.json')
VIDEO = {'.mp4', '.mkv', '.avi', '.wmv', '.mov', '.flv', '.ts', '.m4v', '.webm'}
SUB = {'.srt', '.ass', '.ssa'}
TRACKERS = ('&tr=udp://tracker.opentrackr.org:1337/announce'
            '&tr=udp://open.tracker.cl:1337/announce'
            '&tr=udp://tracker.openbittorrent.com:6969/announce'
            '&tr=http://tracker.openbittorrent.com:80/announce')


def ensure_version_tag(nm, magnet_name):
    """把磁链里的版本标签（-C / -UC）补到番号后面，紧跟番号。

    ⚠️ 番号是「PREFIX-数字」两段，不能 split('-', 1)[0]，否则 MIDA-783 会拼成 MIDA-C-783。
    """
    m = re.search(r'-(UC|C)(?=[\s._\-]|$)', magnet_name, re.I)
    if not m:
        return nm
    tag = '-' + m.group(1).upper()
    parts = nm.split('-')
    if len(parts) < 2:
        return nm
    head = '-'.join(parts[:2])
    rest = nm[len(head):]
    if rest.upper().startswith(tag):
        return nm
    rest = re.sub(r'^-(UC|C)(?=-|\.| )', '', rest, flags=re.I)
    return head + tag + rest


async def client():
    st = json.loads(pathlib.Path('/opt/data/.pikpak_token.json').read_text())
    c = PikPakApi(encoded_token=st.get('encoded_token', ''))
    c.access_token = st.get('access_token', '')
    c.refresh_token = st.get('refresh_token', '')
    c.user_id = st.get('user_id', '')
    c.device_id = st.get('device_id', '')
    return c


async def main():
    if len(sys.argv) < 2:
        raise SystemExit('用法: python3 prep_from_btih.py <番号>')
    code = sys.argv[1].upper()
    rows = json.loads(RESULT.read_text(encoding='utf-8'))
    rec = next((r for r in rows if r['code'].upper() == code), None)
    if not rec or not rec.get('pick'):
        raise SystemExit(f'{code} 在 {RESULT.name} 里没有选中的磁链')

    pick = rec['pick']
    new_name = rec['target']
    if not new_name.lower().endswith('.mp4'):
        new_name += '.mp4'
    new_name = ensure_version_tag(new_name, pick['name'])
    code_nh = code.replace('-', '').upper()

    magnet = f"magnet:?xt=urn:btih:{pick['btih']}&dn={pick['name']}{TRACKERS}"
    print(f'▶ {code}  {pick["gb"]:.2f}GB / {pick["files"]}文件 / {pick["why"]}')
    print(f'  目标名: {new_name}')

    c = await client()
    inbox = (await c.path_to_id('/Inbox-JAV'))[0]['id']

    # 幂等：云端已有同名就直接进收尾，不重复提交
    files = (await c.file_list(parent_id=inbox, size=200))['files']
    folder, kids = None, []
    if [f for f in files if f['name'] == new_name]:
        print('  云端已存在同名文件，跳过离线')
    else:
        task = await c.offline_download(magnet, parent_id=inbox)
        print(f"  离线已提交 task={task.get('task', {}).get('id')}")
        for i in range(20):
            await asyncio.sleep(6)
            fl = (await c.file_list(parent_id=inbox, size=200))['files']
            hit = [f for f in fl if code_nh in f['name'].upper().replace('-', '')]
            fdir = [f for f in hit if f['kind'] == 'drive#folder']
            ffile = [f for f in hit if f['kind'] != 'drive#folder']
            if fdir:
                folder = fdir[0]
                kids = (await c.file_list(parent_id=folder['id'], size=200))['files']
                done = sum(1 for k in kids
                           if str(k.get('phase', '')).startswith('PHASE_TYPE_COMPLETE'))
                print(f'  第{(i+1)*6}s: [夹]{folder["name"][:30]} {done}/{len(kids)}')
                if kids and done == len(kids):
                    break
            elif ffile:
                # 单文件磁链：没有文件夹，直接改名收工
                done = sum(1 for k in ffile
                           if str(k.get('phase', '')).startswith('PHASE_TYPE_COMPLETE'))
                print(f'  第{(i+1)*6}s: [文件]{len(ffile)}个 {done}完成')
                if done == len(ffile):
                    await c.file_rename(id=ffile[0]['id'], new_file_name=new_name)
                    print(f'  ✅ 单文件已重命名 -> {new_name}')
                    kidless = True
                    break

    if kids:
        keep, dele, subs = [], [], []
        print('\n  === 决策表 ===')
        for k in kids:
            nm = k['name']
            ext = pathlib.Path(nm).suffix.lower()
            gb = int(k.get('size') or 0) / 1024 ** 3
            is_v = ext in VIDEO and code_nh in nm.upper().replace('-', '') and gb > 0.5
            is_s = ext in SUB
            print(f"  {'KEEP' if (is_v or is_s) else 'DEL ':4s} {gb:7.2f}GB  {nm[:56]}")
            if is_v:
                keep.append(k)
            elif is_s:
                keep.append(k)
                subs.append(k)
            else:
                dele.append(k)

        vids = [k for k in keep if k not in subs]
        if not vids:
            # 磁链文件名没带番号时退化：取最大的 >1GB 视频，并打印告警
            alt = [k for k in kids
                   if pathlib.Path(k['name']).suffix.lower() in VIDEO
                   and int(k.get('size') or 0) / 1024 ** 3 > 1.0]
            if not alt:
                raise SystemExit('  文件夹里找不到主视频，人工检查')
            vids = [max(alt, key=lambda k: int(k.get('size') or 0))]
            print(f'  ⚠️ 无文件名含番号，退化为最大视频: {vids[0]["name"][:50]}')
        main_vid = max(vids, key=lambda k: int(k.get('size') or 0))

        if dele:
            await c.delete_to_trash([k['id'] for k in dele])
            print(f'  已删 {len(dele)} 个无用文件')
        await c.file_batch_move(ids=[main_vid['id']] + [x['id'] for x in subs],
                                to_parent_id=inbox)
        print(f'  已移出主视频 + {len(subs)} 个字幕')
        await asyncio.sleep(2)
        await c.file_rename(id=main_vid['id'], new_file_name=new_name)
        print(f'  ✅ 已重命名 -> {new_name}')
        for s in subs:
            ext = pathlib.Path(s['name']).suffix
            await c.file_rename(id=s['id'], new_file_name=new_name[:-4] + ext)
        # 顺序必须是 move → rename → delete_folder，反过来会报 file_rename_in_recycle_bin
        await asyncio.sleep(1)
        if folder:
            left = (await c.file_list(parent_id=folder['id'], size=50))['files']
            if not left:
                await c.delete_to_trash([folder['id']])
                print('  空文件夹已删')

    print('\n  === 云端 Inbox-JAV ===')
    tot = 0
    for f in (await c.file_list(parent_id=inbox, size=200))['files']:
        sz = int(f.get('size') or 0) / 1024 ** 3
        tot += sz
        print(f'    {sz:6.2f}GB  {f["name"][:54]}')
    print(f'    合计 {tot:.2f} GB')
    return 0


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))

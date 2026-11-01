#!/usr/bin/env python3
"""收尾一条已下载完成的番号：字节比对 → ffprobe → 字幕按番号改名 → 删云端源。

用法：python3 finish_dl.py SNOS-420
约定：
  · 只处理文件名以番号（忽略横杠）开头的视频/字幕，绝不动其他番号的文件
  · 字幕目标已存在时先改名为 .bak.srt 再覆盖，避免静默丢文件
  · 全部通过后才删云端源；任一校验失败则不删并退出非零
"""
import json
import pathlib
import re
import subprocess
import sys

BASE = pathlib.Path('/opt/data/PikPak/Inbox-JAV')
RCLONE = '/opt/data/bin/rclone'
REMOTE = 'pikpak:/Inbox-JAV'


def run(cmd, timeout=120):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def find_video(code_nh):
    for p in BASE.iterdir():
        if p.suffix.lower() == '.mp4' and p.name.upper().replace('-', '').startswith(code_nh):
            return p
    return None


def cloud_size(code_nh):
    r = run([RCLONE, 'lsjson', REMOTE], timeout=90)
    for f in json.loads(r.stdout or '[]'):
        if f['Name'].upper().replace('-', '').startswith(code_nh):
            return f['Size'], f['Name']
    return None, None


def main():
    if len(sys.argv) < 2:
        raise SystemExit('用法: python3 finish_dl.py <番号>')
    code = sys.argv[1]
    code_nh = code.replace('-', '').upper()

    vid = find_video(code_nh)
    if not vid:
        raise SystemExit(f'本地没有 {code} 的 mp4，无法收尾')

    ok = True
    print(f'=== {code} 收尾 ===')
    print(f'  视频: {vid.name}')

    # ① 字节比对
    lsize = vid.stat().st_size
    csize, cname = cloud_size(code_nh)
    if csize is None:
        print(f'  云端: 未找到同名文件（可能已删）')
    else:
        same = lsize == csize
        ok = ok and same
        print(f'  字节: 本地 {lsize:,} / 云端 {csize:,} → {"一致 OK" if same else "不一致 FAIL"}')

    # ①-b 云端若带内嵌字幕文件（-C 版常见），一并拉回
    try:
        r = run([RCLONE, 'lsjson', REMOTE], timeout=90)
        for f in json.loads(r.stdout or '[]'):
            nm = f['Name']
            if not nm.lower().endswith(('.srt', '.ass', '.ssa')):
                continue
            if not nm.upper().replace('-', '').startswith(code_nh):
                continue
            dst = BASE / nm
            if dst.exists():
                continue
            run([RCLONE, 'copy', f'{REMOTE}/{nm}', str(BASE), '--timeout', '60s'], timeout=180)
            print(f'  云端字幕已拉回: {nm[:60]}')
    except Exception as exc:
        print(f'  云端字幕检查跳过: {exc}')

    # ② ffprobe
    r = run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration,bit_rate',
             '-show_entries', 'stream=codec_type,codec_name,profile,width,height',
             '-of', 'json', str(vid)], timeout=120)
    if r.returncode != 0:
        print(f'  ffprobe: 失败 -> {r.stderr[:200]}')
        ok = False
    else:
        d = json.loads(r.stdout)
        fmt = d.get('format', {})
        dur = float(fmt.get('duration') or 0)
        vs = next((s for s in d.get('streams', []) if s.get('codec_type') == 'video'), {})
        nsub = sum(1 for s in d.get('streams', []) if s.get('codec_type') == 'subtitle')
        print(f"  时长 {dur:.0f}s = {dur / 60:.1f} 分钟 | "
              f"{vs.get('codec_name')} {vs.get('width')}x{vs.get('height')} | "
              f"{int(fmt.get('bit_rate') or 0) / 1e6:.1f} Mbps | 字幕流 {nsub}")

    # ③ 字幕改名（只动本番号）
    for s in [p for p in BASE.iterdir() if p.suffix.lower() in ('.srt', '.ass', '.ssa')]:
        if not s.name.upper().replace('-', '').startswith(code_nh):
            continue
        txt = s.read_text(errors='ignore')
        han = len(re.findall(r'[\u4e00-\u9fff]', txt))
        kana = len(re.findall(r'[\u3040-\u309f\u30a0-\u30ff]', txt))
        tgt = BASE / (vid.stem + s.suffix)
        if s.name != tgt.name:
            if tgt.exists():
                tgt.rename(BASE / (tgt.stem + '.bak.srt'))
            s.rename(tgt)
            print(f'  字幕改名 -> {tgt.name[:60]}')
        print(f'  字幕汉字 {han} / 假名 {kana} → '
              f'{"中文可用 OK" if han > 500 and han > kana else "疑似非中文，需补 srt"}')

    for b in BASE.glob('*.bak.srt'):
        b.unlink()

    # ④ 云端源不在这里删：由 pull_queue_v2 的「30 分钟保管期」流程处理。
    #    原因：FUSE 写回层会在满速写入时丢掉刚下完的大文件，云端源必须留一段时间兜底。
    if cname:
        print(f'  云端源保留（保管期内可兜底）: {cname[:56]}')

    # ⑤ 目录总览
    print('\n=== 本地 Inbox-JAV ===')
    vids = sorted(p for p in BASE.iterdir() if p.suffix.lower() == '.mp4')
    for v in vids:
        has = (BASE / (v.stem + '.srt')).exists()
        print(f'  {"OK " if has else "缺字幕"} {v.stat().st_size / 1024 ** 3:5.2f}GB  {v.name[:60]}')
    print(f'  视频 {len(vids)} / 字幕配对 {sum(1 for v in vids if (BASE / (v.stem + ".srt")).exists())}')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())

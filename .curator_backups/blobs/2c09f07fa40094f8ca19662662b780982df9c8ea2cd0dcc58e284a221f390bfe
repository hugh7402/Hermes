#!/usr/bin/env python3
"""从 .torrent 提取 btih → magnet，并输出文件清单（含外挂字幕/视频文件检测）。

用法: python3 torrent_to_magnet.py <file.torrent> [more.torrent ...]
在 movie-download 流程里替代手工拼磁链。纯标准库。
"""
import hashlib
import os
import sys


def bdecode(data, idx=0):
    if data[idx:idx + 1] == b'i':
        end = data.index(b'e', idx)
        return int(data[idx + 1:end]), end + 1
    if data[idx:idx + 1] == b'l':
        idx += 1
        out = []
        while data[idx:idx + 1] != b'e':
            v, idx = bdecode(data, idx)
            out.append(v)
        return out, idx + 1
    if data[idx:idx + 1] == b'd':
        idx += 1
        out = {}
        while data[idx:idx + 1] != b'e':
            k, idx = bdecode(data, idx)
            v, idx = bdecode(data, idx)
            out[k] = v
        return out, idx + 1
    if data[idx:idx + 1].isdigit():
        end = data.index(b':', idx)
        n = int(data[idx:end])
        return data[end + 1:end + 1 + n], end + 1 + n
    raise ValueError(f'bad bencode at {idx}')


def bencode(obj):
    if isinstance(obj, int):
        return b'i' + str(obj).encode() + b'e'
    if isinstance(obj, bytes):
        return str(len(obj)).encode() + b':' + obj
    if isinstance(obj, str):
        b = obj.encode()
        return str(len(b)).encode() + b':' + b
    if isinstance(obj, list):
        return b'l' + b''.join(bencode(x) for x in obj) + b'e'
    if isinstance(obj, dict):
        items = sorted(obj.items(), key=lambda kv: kv[0] if isinstance(kv[0], bytes) else kv[0].encode())
        return b'd' + b''.join(bencode(k) + bencode(v) for k, v in items) + b'e'
    raise TypeError(type(obj))


VIDEO_EXT = ('.mkv', '.mp4', '.ts', '.m2ts', '.avi', '.rmvb')
SUB_EXT = ('.srt', '.ass', '.ssa', '.sup', '.sub', '.idx')


def inspect(path):
    meta, _ = bdecode(open(path, 'rb').read())
    info = meta[b'info']
    ih = hashlib.sha1(bencode(info)).hexdigest()
    name = info[b'name'].decode('utf-8', 'replace')

    files = []
    if b'files' in info:
        for f in info[b'files']:
            p = '/'.join(x.decode('utf-8', 'replace') for x in f[b'path'])
            files.append((p, f[b'length']))
    else:
        files = [(name, info[b'length'])]
    total = sum(s for _, s in files)

    trackers = []
    if meta.get(b'announce'):
        trackers.append(meta[b'announce'].decode('utf-8', 'replace'))
    for tier in meta.get(b'announce-list', []) or []:
        for x in tier:
            trackers.append(x.decode('utf-8', 'replace'))
    # 常见公共 tracker 兜底（PikPak 离线成功率更稳）
    trackers += ['udp://tracker.openbittorrent.com:80',
                 'udp://tracker.opentrackr.org:1337/announce',
                 'udp://open.tracker.cl:1337/announce']

    print(f'### {os.path.basename(path)}')
    print(f'  名称: {name[:110]}')
    print(f'  Hash: {ih}')
    print(f'  体积: {total / 1024 ** 3:.2f} GB | 文件数: {len(files)}')

    vids = [(p, s) for p, s in files if os.path.splitext(p)[1].lower() in VIDEO_EXT]
    subs = [(p, s) for p, s in files if os.path.splitext(p)[1].lower() in SUB_EXT]
    for p, s in sorted(vids, key=lambda x: -x[1])[:3]:
        print(f'  视频: {p[:72]} ({s / 1024 ** 3:.2f} GB)')
    print(f'  外挂字幕文件: {len(subs)} 个' + (f' 例: {[p for p, _ in subs[:3]]}' if subs else '  （→ 字幕应内封在 mkv 里，属合格）'))

    mag = f'magnet:?xt=urn:btih:{ih}&dn={name}'
    for t in dict.fromkeys(trackers):
        mag += f'&tr={t}'
    print(f'  MAGNET={mag}')
    print()
    return mag


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    for p in sys.argv[1:]:
        inspect(p)

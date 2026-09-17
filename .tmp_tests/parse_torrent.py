"""解析 .torrent → info hash → magnet 链接 + 文件清单"""
import hashlib, sys, os, glob

def bdecode(data, idx=0):
    if data[idx:idx+1] == b'i':
        end = data.index(b'e', idx)
        return int(data[idx+1:end]), end+1
    if data[idx:idx+1] == b'l':
        idx += 1; out = []
        while data[idx:idx+1] != b'e':
            v, idx = bdecode(data, idx)
            out.append(v)
        return out, idx+1
    if data[idx:idx+1] == b'd':
        idx += 1; out = {}
        while data[idx:idx+1] != b'e':
            k, idx = bdecode(data, idx)
            v, idx = bdecode(data, idx)
            out[k] = v
        return out, idx+1
    if data[idx:idx+1].isdigit():
        end = data.index(b':', idx)
        n = int(data[idx:end])
        return data[end+1:end+1+n], end+1+n
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

for path in sorted(glob.glob('/opt/data/.tmp_tests/torrents/*.torrent')):
    raw = open(path, 'rb').read()
    meta, _ = bdecode(raw)
    info = meta[b'info']
    ih = hashlib.sha1(bencode(info)).hexdigest()
    name = info[b'name'].decode('utf-8', 'replace')
    # 文件清单
    files = []
    if b'files' in info:
        for f in info[b'files']:
            p = '/'.join(x.decode('utf-8', 'replace') for x in f[b'path'])
            files.append((p, f[b'length']))
    else:
        files = [(name, info[b'length'])]
    total = sum(s for _, s in files)
    trackers = []
    if b'announce' in meta:
        trackers.append(meta[b'announce'].decode('utf-8', 'replace'))
    if b'announce-list' in meta:
        for t in meta[b'announce-list']:
            for x in t:
                trackers.append(x.decode('utf-8', 'replace'))

    print(f'### {os.path.basename(path)}')
    print(f'  名称: {name[:100]}')
    print(f'  Hash: {ih}')
    print(f'  大小: {total/1024**3:.2f} GB | 文件数: {len(files)}')
    # 字幕文件
    subs = [p for p, _ in files if os.path.splitext(p)[1].lower() in ('.srt', '.ass', '.sup', '.ssa')]
    print(f'  外挂字幕文件: {len(subs)} 个 {subs[:3] if subs else ""}')
    vid = [(p, s) for p, s in files if os.path.splitext(p)[1].lower() in ('.mkv', '.mp4', '.ts', '.m2ts')]
    for p, s in sorted(vid, key=lambda x: -x[1])[:3]:
        print(f'  视频: {p[:70]} ({s/1024**3:.2f} GB)')
    mag = f'magnet:?xt=urn:btih:{ih}&dn={name}'
    for t in trackers[:5]:
        mag += f'&tr={t}'
    print(f'  MAGNET: {mag[:200]}')
    print(f'  MAGNET_FULL={mag}')
    print()

"""从 .torrent 文件提取 btih（info hash）磁链。
用法: python3 btih_from_torrent.py <file.torrent>
输出: BTIH + NAME，可直接拼 magnet:?xt=urn:btih:<HASH>&dn=<NAME>
"""
import hashlib, re, sys

def bdecode(data, i):
    if data[i:i+1] == b'i':
        j = data.index(b'e', i)
        return int(data[i+1:j]), j+1
    elif data[i:i+1] == b'l':
        items = []
        i += 1
        while data[i:i+1] != b'e':
            v, i = bdecode(data, i)
            items.append(v)
        return items, i+1
    elif data[i:i+1] == b'd':
        d = {}
        i += 1
        while data[i:i+1] != b'e':
            k, i = bdecode(data, i)
            v, i = bdecode(data, i)
            d[k] = v
        return d, i+1
    else:
        j = data.index(b':', i)
        n = int(data[i:j])
        return data[j+1:j+1+n], j+1+n

def bencode(obj):
    if isinstance(obj, int):
        return b'i' + str(obj).encode() + b'e'
    if isinstance(obj, bytes):
        return str(len(obj)).encode() + b':' + obj
    if isinstance(obj, list):
        return b'l' + b''.join(bencode(x) for x in obj) + b'e'
    if isinstance(obj, dict):
        return b'd' + b''.join(
            bencode(k) + bencode(v)
            for k, v in sorted(obj.items(), key=lambda x: x[0])
        ) + b'e'

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法: python3 btih_from_torrent.py <file.torrent>")
        sys.exit(1)
    data = open(sys.argv[1], 'rb').read()
    m = re.search(rb'4:info', data)
    if not m:
        print("无法定位 info dict")
        sys.exit(1)
    info_dict, _ = bdecode(data, m.end())
    info_bin = bencode(info_dict)
    h = hashlib.sha1(info_bin).hexdigest().upper()
    name = info_dict.get(b'name', b'?').decode('utf-8', 'ignore')
    print(f"BTIH: {h}")
    print(f"NAME: {name}")
    print(f"magnet:?xt=urn:btih:{h}&dn={name}")

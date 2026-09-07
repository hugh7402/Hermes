#!/usr/bin/env python3
"""切换代理节点：把圣何塞06三网推荐写入 reality_active.json 并重启"""
import json, re, subprocess, urllib.parse, sys

SUB = '/tmp/sub_decoded_new.txt'
ACTIVE = '/opt/data/proxy-skill/reality_active.json'
PORT = 10808

# 目标节点名
TARGET = '圣何塞06 | 三网推荐'

lines = open(SUB).read().splitlines()
target_line = None
for l in lines:
    m = re.search(r'#([^#]*)$', l)
    if m:
        name = m.group(1)
        try:
            name = urllib.parse.unquote(name)
        except Exception:
            pass
        if TARGET in name:
            target_line = l
            break
if not target_line:
    print(f'❌ 未找到节点: {TARGET}')
    sys.exit(1)
print(f'找到节点: {target_line[:100]}')

# 解析 vless
m = re.match(r'^vless://([^@]+)@([^:]+):(\d+)(.*)', target_line)
uuid, server, port = m.group(1), m.group(2), m.group(3)
query_part = m.group(4)
name_part = ''
if '#' in query_part:
    query_part, name_part = query_part.rsplit('#', 1)
p = {}
if '?' in query_part:
    q = query_part.split('?', 1)[1]
    p = {k: v[0] for k, v in urllib.parse.parse_qs(q).items()}
print(f'server={server} port={port}')
print(f'type={p.get("type")} flow={p.get("flow")} sni={p.get("sni")}')

cfg = {
    "log": {"level": "info"},
    "inbounds": [{
        "type": "mixed", "listen": "127.0.0.1", "listen_port": PORT
    }],
    "outbounds": [{
        "type": "vless",
        "server": server,
        "server_port": int(port),
        "uuid": uuid,
        "flow": p.get('flow', ''),
        "tls": {
            "enabled": True,
            "server_name": p.get('sni', server),
            "utls": {"enabled": True, "fingerprint": p.get('fp', 'chrome')},
            "reality": {
                "enabled": True,
                "public_key": p.get('pbk', ''),
                "short_id": p.get('sid', '')
            }
        }
    }]
}

json.dump(cfg, open(ACTIVE, 'w'), indent=2, ensure_ascii=False)
print(f'✅ 已写入 {ACTIVE}')
print('重启代理...')
r = subprocess.run(['bash', '/opt/data/proxy-skill/proxy.sh', 'restart'], capture_output=True, text=True, timeout=60)
print(r.stdout[-300:] if r.stdout else '(无输出)')
if r.returncode != 0:
    print('stderr:', r.stderr[-300:])

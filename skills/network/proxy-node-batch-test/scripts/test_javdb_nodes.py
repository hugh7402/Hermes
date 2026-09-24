#!/usr/bin/env python3
"""批量测试代理订阅节点的 javdb 连通性 + 测速。

用法:
  python3 test_javdb_nodes.py <sub_file|sub_url> [--region 美国,台湾] [--speed]
    <sub_file|sub_url>  订阅文件路径或 URL（base64 或明文 vless:// 行）
    --region 过滤节点名关键词（逗号分隔），默认全部
    --speed  对可用节点额外测速（Cloudflare 5MB）

输出: 每节点 ✅/❌ + javdb HTTP code + 速度；可用节点存 /tmp/javdb_ok_nodes.json

判定: HTTP 200/302 = 可用；403 = 被 javdb 封（3-7天自动解除）；000 = 连不上。
"""
import json, subprocess, os, random, time, base64, urllib.parse, re, sys, urllib.request

SB = "/opt/data/proxy-skill/sing-box"
JAVDB = "https://javdb.com/over18?respond=1"
SPEED_URL = "https://speed.cloudflare.com/__down?bytes=5000000"

def load_sub(src):
    if src.startswith('http://') or src.startswith('https://'):
        raw = urllib.request.urlopen(src, timeout=30).read()
    else:
        raw = open(src, 'rb').read()
    try:
        return [l for l in base64.b64decode(raw).decode().splitlines() if l.strip()]
    except Exception:
        return [l for l in raw.decode(errors='ignore').splitlines() if l.strip()]

def parse_url(url):
    """解析 vless/trojan/ss/socks/hysteria2 → (proto, params)。踩坑已处理：
    - https:// 前缀是 trojan（v2ray 订阅惯例）
    - 端口可能带 '/' 后缀（35000/）→ rstrip
    - ss:// userinfo 是 base64(method:password)
    """
    try:
        m = re.match(r'^([a-z0-9]+)://', url)
        if not m: return None
        proto = m.group(1)
        if proto == 'https': proto = 'trojan'
        rest = url[m.end():]
        name = ''
        if '#' in rest:
            rest, name_part = rest.rsplit('#', 1)
            name = urllib.parse.unquote(name_part)
        userinfo = ''
        if '@' in rest:
            userinfo, rest = rest.rsplit('@', 1)
        query = ''
        if '?' in rest:
            rest, query = rest.split('?', 1)
        host, port = rest.rsplit(':', 1)
        port = port.rstrip('/')
        p = {k: v[0] for k, v in urllib.parse.parse_qs(query).items()}
        p['name'] = name; p['server'] = host; p['port'] = port
        p['allowInsecure'] = p.get('allowInsecure', '0') in ('1','true','True')
        if proto in ('vless', 'trojan'):
            p['uuid'] = userinfo
            p['fp'] = p.get('fp', 'chrome')
        elif proto == 'ss':
            try:
                dec = base64.b64decode(userinfo + '==').decode()
                method, password = dec.split(':', 1)
                p['method'] = method; p['password'] = password
            except Exception:
                if ':' in userinfo:
                    method, password = userinfo.split(':', 1)
                    p['method'] = method; p['password'] = password
        elif proto == 'socks':
            if ':' in userinfo:
                u, pw = userinfo.split(':', 1)
                p['username'] = urllib.parse.unquote(u)
                p['password'] = urllib.parse.unquote(pw)
        elif proto == 'hysteria2':
            p['password'] = userinfo
        return (proto, p)
    except Exception:
        return None

def make_cfg(proto, p, port):
    common = {"log": {"level": "error"},
              "inbounds": [{"type": "mixed", "listen": "127.0.0.1", "listen_port": port}]}
    if proto == 'vless':
        tls = {"enabled": True, "server_name": p.get('sni', p['server']),
               "utls": {"enabled": True, "fingerprint": p['fp']}}
        # 0.1倍/非 reality 节点无 pbk → 不加 reality 块（否则 KeyError）
        if 'pbk' in p:
            tls["reality"] = {"enabled": True, "public_key": p['pbk'], "short_id": p.get('sid','')}
        out = {"type": "vless", "server": p['server'], "server_port": int(p['port']),
               "uuid": p['uuid'], "flow": p.get('flow',''), "tls": tls}
        # ⚠️ 默认 tcp 不要写 transport 字段，sing-box 会报 outbounds[0].transport 配置错误
        if p.get('type') == 'ws':
            out["transport"] = {"type": "ws", "path": p.get('path','/'),
                                "headers": {"Host": p.get('host','')}}
        common["outbounds"] = [out]
    elif proto == 'trojan':
        common["outbounds"] = [{"type": "trojan", "server": p['server'],
            "server_port": int(p['port']), "password": p['uuid'],
            "tls": {"enabled": True, "server_name": p.get('sni', p['server']),
                    "insecure": p['allowInsecure'],
                    "utls": {"enabled": True, "fingerprint": p['fp']}}}]
    elif proto == 'ss':
        common["outbounds"] = [{"type": "shadowsocks", "server": p['server'],
            "server_port": int(p['port']), "method": p.get('method','aes-256-gcm'),
            "password": p.get('password','')}]
    elif proto == 'socks':
        common["outbounds"] = [{"type": "socks", "server": p['server'],
            "server_port": int(p['port']), "username": p.get('username',''),
            "password": p.get('password','')}]
    elif proto == 'hysteria2':
        common["outbounds"] = [{"type": "hysteria2", "server": p['server'],
            "server_port": int(p['port']), "password": p['password'],
            "tls": {"enabled": True, "server_name": p.get('sni', p['server']),
                    "insecure": p['allowInsecure']}}]
    else:
        return None
    return common

def test_node(proto, p, do_speed):
    port = 22800 + random.randint(0, 300)
    cfg = make_cfg(proto, p, port)
    if not cfg:
        return ('SKIP', 'unsupported proto')
    cfg_path = f"/tmp/jn_{port}.json"
    json.dump(cfg, open(cfg_path, 'w'))
    r = subprocess.run([SB, "check", "-c", cfg_path], capture_output=True, text=True)
    if r.returncode != 0:
        os.remove(cfg_path)
        return ('CFGERR', r.stderr.strip()[:70])
    proc = subprocess.Popen([SB, "run", "-c", cfg_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2.5)
    code = '000'
    try:
        curl = subprocess.run(['curl','-s','--max-time','10','--proxy',f'http://127.0.0.1:{port}',
            '-A','Mozilla/5.0','-o','/dev/null','-w','%{http_code}', JAVDB],
            capture_output=True, text=True, timeout=15)
        code = curl.stdout.strip()
    except Exception:
        pass
    speed = 'N/A'
    if code in ('200','302') and do_speed:
        try:
            curl2 = subprocess.run(['curl','-s','--max-time','12','--proxy',f'http://127.0.0.1:{port}',
                '-o','/dev/null','-w','%{speed_download}', SPEED_URL],
                capture_output=True, text=True, timeout=18)
            speed = curl2.stdout.strip()
        except Exception:
            pass
    proc.kill(); proc.wait()
    os.remove(cfg_path)
    return (code, speed)

def main():
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    src = sys.argv[1]
    region_filter = None
    do_speed = False
    if '--region' in sys.argv:
        region_filter = sys.argv[sys.argv.index('--region')+1].split(',')
    if '--speed' in sys.argv:
        do_speed = True

    lines = load_sub(src)
    print(f'订阅节点总数: {len(lines)}')
    ok_nodes = []
    for l in lines:
        name_m = re.search(r'#([^#]*)$', l)
        name = ''
        if name_m:
            try: name = urllib.parse.unquote(name_m.group(1))
            except: name = name_m.group(1)
        if region_filter and not any(k in name for k in region_filter):
            continue
        parsed = parse_url(l)
        if not parsed:
            print(f'✗ 解析失败: {name}')
            continue
        proto, p = parsed
        code, speed = test_node(proto, p, do_speed)
        status = '✅' if code in ('200','302') else '❌'
        print(f'{status} {name[:30]:32s} javdb={code} speed={speed}')
        if code in ('200','302'):
            ok_nodes.append({'name': name, 'url': l, 'proto': proto, 'speed': speed})
        time.sleep(0.5)
    print(f'\n可用节点: {len(ok_nodes)}')
    if ok_nodes:
        json.dump(ok_nodes, open('/tmp/javdb_ok_nodes.json','w'), ensure_ascii=False, indent=1)
        print('结果: /tmp/javdb_ok_nodes.json')

if __name__ == '__main__':
    main()

"""批量测试订阅节点对 javdb 的连通性"""
import json, re, urllib.parse, base64, subprocess, os, time, socket, sys

nodes = json.load(open('/tmp/target_nodes.json'))

def parse_vless(link):
    """vless://uuid@server:port?params#name"""
    core = link.split('://')[1]
    params_part = core.split('?')[1] if '?' in core else ''
    auth_server = core.split('?')[0]
    uuid, server_port = auth_server.split('@')
    server, port = server_port.split(':')
    params = dict(p.split('=', 1) for p in params_part.split('&') if '=' in p)
    return {
        'type': 'vless', 'uuid': uuid, 'server': server, 'port': int(port),
        'tls': params.get('security', '') == 'tls',
        'servername': params.get('sni', params.get('host', server)),
        'path': params.get('path', ''),
        'host': params.get('host', ''),
    }

def parse_hy2(link):
    """hysteria2://password@server:port?params#name"""
    core = link.split('://')[1]
    params_part = core.split('?')[1] if '?' in core else ''
    auth_server = core.split('?')[0]
    password, server_port = auth_server.split('@')
    server, port = server_port.split(':')
    params = dict(p.split('=', 1) for p in params_part.split('&') if '=' in p)
    return {
        'type': 'hysteria2', 'password': password, 'server': server, 'port': int(port),
        'sni': params.get('sni', params.get('peer', server)),
        'insecure': params.get('insecure', '1') == '1',
    }

def build_singbox_config(node_info, listen_port):
    if node_info['type'] == 'vless':
        outbound = {
            "type": "vless",
            "server": node_info['server'],
            "server_port": node_info['port'],
            "uuid": node_info['uuid'],
            "tls": {"enabled": node_info['tls'], "server_name": node_info['servername'], "insecure": True},
            "transport": {"type": "ws", "path": node_info['path'], "headers": {"Host": node_info['host']}} if node_info['path'] else {"type": "http"},
        }
    else:  # hysteria2
        outbound = {
            "type": "hysteria2",
            "server": node_info['server'],
            "server_port": node_info['port'],
            "password": node_info['password'],
            "tls": {"enabled": True, "server_name": node_info['sni'], "insecure": True},
        }
    return {
        "log": {"level": "error"},
        "inbounds": [{
            "type": "mixed", "listen": "127.0.0.1", "listen_port": listen_port,
            "users": []
        }],
        "outbounds": [outbound],
    }

def test_node(name, link, listen_port):
    try:
        if link.startswith('vless://'):
            info = parse_vless(link)
        elif link.startswith('hysteria2://') or link.startswith('hy2://'):
            info = parse_hy2(link)
        else:
            return 'SKIP'
        cfg = build_singbox_config(info, listen_port)
        cfg_path = f'/tmp/node_test_{listen_port}.json'
        json.dump(cfg, open(cfg_path, 'w'))
        # 校验配置
        check = subprocess.run(['/opt/data/proxy-skill/sing-box', 'check', '-c', cfg_path],
                               capture_output=True, text=True, timeout=15)
        if check.returncode != 0:
            return f'CFG_FAIL: {check.stderr.strip()[:60]}'
        # 启动
        proc = subprocess.Popen(['/opt/data/proxy-skill/sing-box', 'run', '-c', cfg_path],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(2)
        try:
            # 测试 javdb
            r = subprocess.run(['curl', '-s', '--max-time', '12', '--proxy', f'http://127.0.0.1:{listen_port}',
                                '-A', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126.0',
                                '-o', '/dev/null', '-w', '%{http_code}',
                                'https://javdb.com/over18?respond=1'],
                               capture_output=True, text=True, timeout=20)
            code = r.stdout.strip()
            if code == '200':
                # 再测搜索
                r2 = subprocess.run(['curl', '-s', '--max-time', '12', '--proxy', f'http://127.0.0.1:{listen_port}',
                                     '-A', 'Mozilla/5.0', '-c', '/tmp/jdb_cookies.txt',
                                     '-o', '/dev/null', '-w', '%{http_code}',
                                     'https://javdb.com/search?q=ZOZO-077&f=all'],
                                    capture_output=True, text=True, timeout=20)
                return f'OK over18=200 search={r2.stdout.strip()}'
            elif code == '403':
                return '403 banned'
            elif code == '000':
                return 'TIMEOUT'
            return f'HTTP {code}'
        finally:
            proc.terminate()
            try: proc.wait(timeout=3)
            except: proc.kill()
    except Exception as e:
        return f'ERR: {str(e)[:50]}'

# 并行测试（用线程）
import concurrent.futures

results = {}
base_port = 21000
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
    futs = {}
    for i, (name, link) in enumerate(nodes.items()):
        port = base_port + i * 2
        futs[ex.submit(test_node, name, link, port)] = name
    for fut in concurrent.futures.as_completed(futs):
        name = futs[fut]
        try:
            results[name] = fut.result()
        except Exception as e:
            results[name] = f'EXC: {e}'

print('\n=== 测试结果 ===')
for name, res in results.items():
    print(f'{name}: {res}')

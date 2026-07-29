#!/usr/bin/env python3
"""
将 base64 编码的通用订阅链接转换为 mihomo/clash YAML 配置。

订阅格式：base64 编码的多行链接，每行一条（vless://, ss://, trojan://, hysteria2:// 等）。

用法：
  # 1. 获取订阅 → base64 解码 → 保存
  curl -s "订阅URL" | base64 -d > /tmp/nodes.txt

  # 2. 生成 clash YAML 配置
  python3 convert_sub_to_clash.py --nodes /tmp/nodes.txt --socks-port 10808 -o /opt/data/mihomo/config.yaml

  # 3. 启动
  /opt/data/mihomo/mihomo -d /opt/data/mihomo/
"""

import argparse
import sys
import re
from urllib.parse import urlparse, parse_qs, unquote


def parse_vless(url: str) -> dict | None:
    """解析 vless:// 链接为 clash proxy 字典"""
    # vless://uuid@host:port?params#name
    m = re.match(r'vless://([a-f0-9-]+)@([^:]+):(\d+)\?(.+)#(.+)', url)
    if not m:
        return None

    uuid, host, port_str, query_str, name = m.groups()
    port = int(port_str)
    params = parse_qs(query_str)
    name = unquote(name)

    proxy = {
        "name": name,
        "type": "vless",
        "server": host,
        "port": port,
        "uuid": uuid,
        "tls": params.get("security", [""])[0] in ("tls", "reality"),
        "udp": True,
    }

    # Reality
    if params.get("security", [""])[0] == "reality":
        proxy["reality"] = True
        proxy["flow"] = params.get("flow", ["xtls-rprx-vision"])[0]
        if params.get("pbk"):
            proxy["reality-opts"] = {"public-key": params["pbk"][0]}
        if params.get("sid"):
            proxy.setdefault("reality-opts", {})["short-id"] = params["sid"][0]

    # Transport
    transport = params.get("type", [""])[0]
    if transport == "ws":
        proxy["network"] = "ws"
        path = unquote(params.get("path", [""])[0])
        if path:
            proxy["ws-opts"] = {"path": path}
            host_header = params.get("host", [""])[0]
            if host_header:
                proxy["ws-opts"]["headers"] = {"Host": host_header}

    # TLS fingerprint
    fp = params.get("fp", [""])[0]
    if fp:
        proxy["client-fingerprint"] = fp

    # SNI
    sni = params.get("sni", [""])[0]
    if sni:
        proxy["servername"] = sni

    return proxy


def parse_ss(url: str) -> dict | None:
    """解析 ss:// 链接（简化版，仅支持 base64 密码格式）"""
    # ss://base64(password@host:port)#name
    m = re.match(r'ss://([A-Za-z0-9+/=]+)@([^:]+):(\d+)#(.+)', url)
    if not m:
        return None
    import base64
    try:
        decoded = base64.b64decode(m.group(1) + "==").decode()
    except:
        return None
    method, password = decoded.split(":", 1)
    name = unquote(m.group(4))
    return {
        "name": name,
        "type": "ss",
        "server": m.group(2),
        "port": int(m.group(3)),
        "cipher": method,
        "password": password,
        "udp": True,
    }


def parse_hysteria2(url: str) -> dict | None:
    """解析 hysteria2:// 链接"""
    # hysteria2://password@host:port?params#name
    m = re.match(r'hysteria2://([^@]+)@([^:]+):(\d+)\?(.+)#(.+)', url)
    if not m:
        return None
    password, host, port_str, query_str, name = m.groups()
    port = int(port_str)
    params = parse_qs(query_str)
    name = unquote(name)

    proxy = {
        "name": name,
        "type": "hysteria2",
        "server": host,
        "port": port,
        "password": password,
        "udp": True,
    }

    sni = params.get("sni", [""])[0]
    if sni:
        proxy["sni"] = sni

    insecure = params.get("insecure", ["0"])[0]
    if insecure == "1":
        proxy["skip-cert-verify"] = True

    return proxy


def parse_trojan(url: str) -> dict | None:
    """解析 trojan:// 链接"""
    # trojan://password@host:port?sni=xxx#name
    m = re.match(r'trojan://([^@]+)@([^:]+):(\d+)\?(.+)#(.+)', url)
    if not m:
        return None
    password, host, port_str, query_str, name = m.groups()
    params = parse_qs(query_str)
    name = unquote(name)

    proxy = {
        "name": name,
        "type": "trojan",
        "server": host,
        "port": int(port_str),
        "password": password,
        "udp": True,
        "tls": True,
    }

    sni = params.get("sni", [""])[0]
    if sni:
        proxy["sni"] = sni

    return proxy


def parse_node_line(line: str) -> dict | None:
    """解析单行链接，返回 clash proxy 字典"""
    line = line.strip()
    if not line:
        return None
    if line.startswith("vless://"):
        return parse_vless(line)
    elif line.startswith("ss://"):
        return parse_ss(line)
    elif line.startswith("hysteria2://") or line.startswith("hy2://"):
        return parse_hysteria2(line)
    elif line.startswith("trojan://"):
        return parse_trojan(line)
    return None


def generate_clash_yaml(proxies: list[dict], socks_port: int = 10808,
                        mixed_port: int = 10809) -> str:
    """生成 clash YAML 配置"""
    proxy_names = [p["name"] for p in proxies]

    lines = []
    lines.append(f"port: {socks_port}")
    lines.append(f"mixed-port: {mixed_port}")
    lines.append("allow-lan: false")
    lines.append("mode: rule")
    lines.append("log-level: warning")
    lines.append("ipv6: false")
    lines.append("")

    # proxies
    lines.append("proxies:")
    for p in proxies:
        lines.append(f"  - name: \"{p['name']}\"")
        lines.append(f"    type: {p['type']}")
        lines.append(f"    server: {p['server']}")
        lines.append(f"    port: {p['port']}")
        if p['type'] == 'vless':
            lines.append(f"    uuid: \"{p['uuid']}\"")
        elif p['type'] in ('ss', 'trojan'):
            lines.append(f"    password: \"{p['password']}\"")
        elif p['type'] == 'hysteria2':
            lines.append(f"    password: \"{p['password']}\"")
        lines.append(f"    udp: {str(p.get('udp', True)).lower()}")
        lines.append(f"    tls: {str(p.get('tls', False)).lower()}")

        # Reality
        if p.get('reality'):
            lines.append("    reality: true")
            lines.append(f"    flow: \"{p.get('flow', 'xtls-rprx-vision')}\"")
            ropts = p.get('reality-opts', {})
            if ropts:
                lines.append("    reality-opts:")
                if ropts.get("public-key"):
                    lines.append(f"      public-key: \"{ropts['public-key']}\"")
                if ropts.get("short-id"):
                    lines.append(f"      short-id: \"{ropts['short-id']}\"")

        # WS
        if p.get('network') == 'ws':
            lines.append(f"    network: ws")
            wsopts = p.get('ws-opts', {})
            if wsopts:
                lines.append("    ws-opts:")
                if wsopts.get("path"):
                    lines.append(f"      path: \"{wsopts['path']}\"")
                headers = wsopts.get("headers", {})
                if headers:
                    lines.append("      headers:")
                    for k, v in headers.items():
                        lines.append(f"        {k}: \"{v}\"")

        # TLS
        if p.get('client-fingerprint'):
            lines.append(f"    client-fingerprint: {p['client-fingerprint']}")
        if p.get('servername'):
            lines.append(f"    servername: \"{p['servername']}\"")
        if p.get('sni'):
            lines.append(f"    sni: \"{p['sni']}\"")
        if p.get('skip-cert-verify'):
            lines.append("    skip-cert-verify: true")

    lines.append("")

    # proxy-groups
    lines.append("proxy-groups:")
    lines.append("  - name: Proxy")
    lines.append("    type: select")
    lines.append("    proxies:")
    for name in proxy_names:
        lines.append(f"      - \"{name}\"")
    lines.append("")

    # rules - 全部走代理
    lines.append("rules:")
    lines.append("  - MATCH,Proxy")
    lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="订阅链接转 clash YAML 配置")
    parser.add_argument("--nodes", "-n", required=True,
                        help="节点列表文件（每行一个 vless/ss/trojan/hysteria2 链接）")
    parser.add_argument("--socks-port", type=int, default=10808,
                        help="SOCKS5 代理端口（默认 10808）")
    parser.add_argument("--mixed-port", type=int, default=10809,
                        help="混合代理端口（默认 10809）")
    parser.add_argument("--output", "-o", default="config.yaml",
                        help="输出 YAML 文件路径（默认 config.yaml）")
    args = parser.parse_args()

    with open(args.nodes) as f:
        lines = f.readlines()

    proxies = []
    errors = []
    for line in lines:
        p = parse_node_line(line)
        if p:
            proxies.append(p)
        elif line.strip():
            errors.append(line.strip()[:80])

    if not proxies:
        print("ERROR: 未解析到任何有效节点", file=sys.stderr)
        if errors:
            print(f"无法解析的行（示例）:", file=sys.stderr)
            for e in errors[:5]:
                print(f"  {e}", file=sys.stderr)
        sys.exit(1)

    yaml = generate_clash_yaml(proxies, args.socks_port, args.mixed_port)

    with open(args.output, "w") as f:
        f.write(yaml)

    print(f"✅ 已生成 clash YAML 配置: {args.output}")
    print(f"   共 {len(proxies)} 个节点")
    if errors:
        print(f"   ⚠️  {len(errors)} 行无法解析（非标准格式）")
    print()
    print("启动: /opt/data/mihomo/mihomo -d /opt/data/mihomo/")


if __name__ == "__main__":
    main()
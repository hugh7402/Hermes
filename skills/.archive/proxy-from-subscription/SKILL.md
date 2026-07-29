---
name: proxy-from-subscription
title: Proxy from V2Ray/VLESS Subscription
description: Set up a SOCKS5/HTTP proxy from a V2Ray subscription link (VLESS) in a container/headless environment without root access. Includes node parsing, reality/WS config generation, and batch testing.
---

# Proxy from VLESS/V2Ray Subscription

Set up xray as a SOCKS5+HTTP proxy from a V2Ray subscription link (base64-encoded VLESS links).

## Trigger

User provides a V2Ray subscription URL (ending in `/api/v1/...`, `clash.meta`, etc.) or a file containing one, and says "set up proxy" / "帮我搭代理".

## Steps

### 1. Fetch and decode subscription

```bash
curl -sL "$SUB_URL" | base64 -d 2>/dev/null
```

Extract VLESS links: `re.findall(r'vless://[^\s\r\n]+', decoded)`

### 2. Parse VLESS link

Each VLESS link format:
```
vless://UUID@HOST:PORT?type=tcp|ws&security=none|tls|reality&flow=xtls-rprx-vision&fp=ios|chrome|safari&sni=SNI&pbk=PUBLIC_KEY&sid=SHORT_ID&host=WS_HOST&path=WS_PATH#NAME
```

Key parameters to extract:
- `host`, `port` — server address
- `type` — `tcp` or `ws` (WebSocket)
- `security` — `tls`, `reality`, or `none`
- `flow` — `xtls-rprx-vision` (for reality)
- `fp` — fingerprint (ios, chrome, safari)
- `sni` — Server Name Indication (for reality/TLS)
- `pbk` — publicKey (REQUIRED for reality)
- `sid` — shortId (for reality)
- `host` — WS host header (for WS TLS)
- `path` — WS path (for WS)

### 3. Build xray config

**For reality (recommended, harder to detect):**
```python
streamSettings = {
    "network": "tcp",
    "security": "reality",
    "realitySettings": {
        "serverName": sni or host,
        "fingerprint": fp or "chrome",
        "show": False,
        "publicKey": pbk,    # REQUIRED — never omit
        "shortId": sid or ""
    }
}
```

**For WS + TLS:**
```python
streamSettings = {
    "network": "ws",
    "security": "tls",
    "tlsSettings": {
        "serverName": sni or ws_host,
        "fingerprint": fp or "chrome",
        "allowInsecure": False
    },
    "wsSettings": {
        "path": path or "/",
        "headers": {"Host": ws_host} if ws_host else {}
    }
}
```

Always include both SOCKS5 (10808) and HTTP (10809) inbounds for flexibility.

### 4. Download xray binary

From GitHub releases (if accessible) or Gitee mirror:
```bash
# Check arch
uname -m  # x86_64 → amd64, aarch64 → arm64

# From GitHub
curl -sL "https://github.com/XTLS/Xray-core/releases/latest/download/Xray-linux-64.zip"

# From Gitee mirror (for China networks)
curl -sL "https://gitee.com/hagb/xray-core/releases/latest/download/Xray-linux-64.zip"
```

Unzip to a writable directory like `/tmp/xray/`.

### 5. Test nodes

Write a test script that:
1. Kills any existing xray (`kill $(cat /opt/data/xray.pid)` — NOT `pkill -f xray` which kills itself)
2. Starts xray with target node config
3. Waits 2s for startup
4. Tests: `curl -s --socks5 127.0.0.1:10808 https://target-site.com`
5. Check exit code and HTTP status code
   - `000` means connection failed (config error or node down — check parameters!)
   - `200` = working
   - `301/302` = redirect (usually still working)
   - `403` = IP blocked by target site

**IMPORTANT**: 000 usually means config is wrong (missing pbk, wrong sni, etc.), NOT that the site blocked you.

### 6. Persist as background daemon

```bash
nohup /tmp/xray/xray run -c /opt/data/xray_config.json \
    > /opt/data/xray_stdout.log 2>&1 &
echo $! > /opt/data/xray.pid
```

Create a start script (`start_xray.sh`) with PID management.

## Pitfalls

- **Reality needs pbk**: The `publicKey` (pbk) parameter from the VLESS URL is MANDATORY. Without it xray fails with `empty "password"` error. Also include `shortId` (sid).
- **pkill xray kills itself**: When running pkill -f xray in terminal, the pkill command itself may contain "xray" in its process name and die. Use `kill $(cat /opt/data/xray.pid)` or kill specific PIDs.
- **Node naming**: Decode URL fragment (#) with `urllib.parse.unquote()` to get readable node names (e.g., "🇺🇸美国圣何塞01 | 三网推荐").
- **Subscription links may have CRLF**: VLESS links are separated by `\r\n` — use `re.findall(r'vless://[^\s\r\n]+', decoded)`.
- **Some nodes work intermittently**: Test multiple times if first attempt fails (especially WS/TLS nodes behind CDN).
- **Gateway restart block**: `hermes gateway restart` refuses to run from inside the gateway process. User must run it from a terminal outside Hermes.
- **Old xray processes linger and block ports**: After killing an xray process, `fuser -k 10808/tcp` or iterate /proc to find the socket owner.
- **Docker/container environment**: Machines in Docker may have IP 172.x.x.x that gets flagged by Cloudflare WAF. This is common and hard to bypass.

## Cloudflare/CDN Block Diagnosis

WS nodes behind Cloudflare CDN (domains like `unamecf.xn--*`, `unamecf2.xn--*`, `downloadcfpro.xn--*`) can be blocked even when the node itself is alive.

### Layer-by-layer test (Python, no proxy needed)

```python
import socket, ssl
# Layer 1: TCP
s = socket.create_connection(('unamecf2.xn--ghqu5fm27b67w.com', 443), timeout=8)
print(f'TCP: {s.getpeername()}')
# Layer 2: TLS
ctx = ssl.create_default_context()
ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
ss = ctx.wrap_socket(s, server_hostname='usa1s.xn--ghqu5fm27b67w.com')
print(f'TLS: {ss.cipher()[0]}')
# Layer 3: WebSocket upgrade (raw HTTP)
ws_key = 'dGhlIHNhbXBsZSBub25jZQ=='
ss.sendall(f'GET /pq/us1 HTTP/1.1\r\nHost: usa1s.xn--ghqu5fm27b67w.com\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: {ws_key}\r\nSec-WebSocket-Version: 13\r\n\r\n'.encode())
resp = ss.recv(4096)
print(resp.decode(errors='replace')[:300])
ss.close()
```

### Interpreting WS response codes

| Response | Meaning | Action |
|----------|---------|--------|
| `101 Switching Protocols` | WebSocket handshake OK — node is alive | VLESS config issue, check flow/uuid |
| `403 Forbidden` | **Cloudflare IP block** — machine's IP blocked by CF | Need non-CF node or different IP |
| `429 Too Many Requests` | CF rate limit — too many requests from this IP | Wait or switch nodes |
| `503 Service Unavailable` | CF temporary block | Wait or switch nodes |
| `ws closed: 1000 (normal)` | WS connected but server closed it | VLESS auth failed — check uuid/flow |
| timeout (no response) | TCP/TLS OK but no WS response | Node overloaded or path wrong |

### Root causes of all-000

- **All WS nodes → 403/429/503**: Cloudflare blocked the machine's IP. Non-CF nodes needed.
- **All Reality nodes → timeout**: Reality nodes' IPs may be directly blocked by GFW.
- **AWS/非CF nodes → TLS reset**: Connection reset by peer at TLS layer — IP block.
- **hy2 nodes → timeout**: UDP/QUIC may be throttled, or server-side bandwidth exhausted.

## Downloading tools when GitHub is blocked

Use GitHub proxy mirrors:

```bash
# ghfast.top (recommended)
curl -sL "https://ghfast.top/https://github.com/user/repo/releases/download/v1.0.0/file.tar.gz"

# gh-proxy.com (fallback)
curl -sL "https://gh-proxy.com/https://github.com/user/repo/releases/download/v1.0.0/file.tar.gz"
```

Always check file size after download — blocked/proxied downloads return tiny files (e.g. 9 bytes) instead of full size.

## Alternative: sing-box (when xray doesn't support node protocol)

Install sing-box when you need hy2/hysteria2 support (xray doesn't support it):

### Install
```bash
curl -sL "https://ghfast.top/https://github.com/SagerNet/sing-box/releases/download/v1.11.0/sing-box-1.11.0-linux-amd64.tar.gz" \
  -o /tmp/sing-box.tar.gz
tar xzf /tmp/sing-box.tar.gz -C /tmp
cp /tmp/sing-box-*/sing-box /opt/data/sing-box
```

### Config mapping (xray → sing-box)

| Aspect | xray | sing-box |
|--------|------|----------|
| SOCKS5 inbound | `{"protocol":"socks","port":10808}` | `{"type":"socks","listen_port":10808}` |
| HTTP inbound | `{"protocol":"http","port":10809}` | `{"type":"mixed","listen_port":10809}` (one mixed inbound replaces both) |
| VLESS+WS outbound | `protocol:"vless"` + `streamSettings.network:"ws"` | `type:"vless"` + `transport.type:"ws"` |
| TLS fingerprint | `tlsSettings.fingerprint:"chrome"` | `tls.utls.fingerprint:"chrome"` |
| Reality | `realitySettings.publicKey` | `tls.reality.public_key` |
| hy2 | not supported | `type:"hysteria2"` + `tls.enabled:true` |
| Routing | `routing.rules[].outboundTag` | `route.rules[].outbound` |

### hy2 specific notes
- Go 1.23+ rejects certificates using legacy Common Name (no SAN) → must set `"insecure": true`
- `mport=35000-39000` in subscription means multi-port support, but just use the base port (35000)
- Test UDP first: `timeout 5 bash -c 'echo > /dev/udp/HOST/PORT' && echo "UDP OK"`
- hy2 uses UDP/QUIC only — TCP connect will timeout, that's normal

### Running sing-box (no systemd)
```bash
nohup /opt/data/sing-box run -c /opt/data/singbox_config.json \
  > /opt/data/singbox_stdout.log 2>&1 &
echo $! > /tmp/singbox.pid
```
Use `fuser -k 10808/tcp` to free ports from old processes.

## Verification

```bash
# Check exit IP
curl -s --socks5 127.0.0.1:10808 https://httpbin.org/ip

# Test target site (follow redirects)
curl -sL -o /dev/null -w '%{http_code}' --socks5 127.0.0.1:10808 \
  -A 'Mozilla/5.0' https://target-site.com

# Also HTTP proxy works
curl -sL -o /dev/null -w '%{http_code}' -x http://127.0.0.1:10809 \
  -A 'Mozilla/5.0' https://target-site.com
```
# Cloudflare Block Diagnosis — 2026-07-15

## Environment
- Docker container, IP 172.18.0.3, running in China
- Tools available: xray 26.3.27, sing-box 1.11.0
- Subscription: `https://dash.pqjc.site/api/v1/pq/53eca709b4fb562544949681e80cae21`
- 71 total nodes: vless (ws+tls + reality) + hysteria2

## Symptoms
- All VLESS+WS nodes behind Cloudflare CDN → 403/429/503
- All Reality nodes (134.195.101.x, AWS JP) → timeout or TLS reset
- hy2 nodes → established but no data returned (timeout)

## Diagnosis Process

### 1. Python layer-by-layer test (direct, no proxy)

```python
import socket, ssl

# TCP
s = socket.create_connection((host, 443), timeout=8)
# TLS
ctx = ssl.create_default_context()
ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
ss = ctx.wrap_socket(s, server_hostname=sni)
# WebSocket raw upgrade
ss.sendall(b'GET /path HTTP/1.1\r\n... Upgrade: websocket ...')
resp = ss.recv(4096).decode(errors='replace')
# Result: "HTTP/1.1 403 Forbidden"  ← Cloudflare block
```

### 2. xray error log analysis

Set `loglevel: "debug"` in xray config, then read error log:

- Japan WS 01: `429 Too Many Requests`, `503 Service Unavailable` — Cloudflare rate limit
- Japan WS 06 (different host/path): `ws closed: 1000` then `failed to decode response header` — WS connected but VLESS auth issue
- Japan WS 04: repeated `tunneling request` then timeout — connection established but no data
- US WS 01 (via sing-box): `ws closed: 1000` — same as Japan 06

### 3. Findings

1. **Cloudflare WS nodes** (unamecf, unamecf2, downloadcfpro domains):
   - Direct Python test returns `403 Forbidden` — Cloudflare WAF blocks the Docker IP
   - 429/503 in xray logs confirms CF-side rate limiting
   - Changing path/sni/host doesn't bypass — it's IP-level block

2. **Reality nodes** (134.195.101.x, pq.aws*.yydjc.top):
   - TCP connects but TLS handshake fails or resets
   - Likely GFW interference with reality protocol

3. **hy2 nodes** (pq.us*.globals-download.com):
   - UDP port open, sing-box outbound connects, but data exchange times out
   - No error in logs — suggests server isn't responding properly

### Attempted Fixes (all failed)
- Switched nodes (US 01-07, AWS JP 01-10, Japan WS 01-09, hy2 US 01-02)
- Switched from xray to sing-box (no improvement)
- Changed TLS fingerprints (ios, chrome, safari, random)
- Changed WS host header / path / SNI
- Added/removed utls
- hy2 with `insecure: true`

## Conclusion
Cannot proxy through this subscription from this machine's IP. The Docker container's outgoing IP is blocked by Cloudflare. Need either:
1. A different machine with a clean IP
2. Nodes that don't go through Cloudflare (unlikely with this provider)
3. A different subscription/provider
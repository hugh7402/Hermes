# 443 Egress Blocking Diagnosis (July 15, 2026)

## Environment
- Provider: Beijing Unicom
- Public IP: 123.123.74.33
- Machine: Linux (5.19.17-z4pro-generic)
- Subscription: PQJC (71 nodes: VLESS+WS, VLESS+REALITY, hy2)

## Symptoms
- All 71 nodes unreachable from server
- Same subscription works on mobile (Clash Meta app, different ISP)
- TCP 443 to any foreign IP: timeout
- TCP 80 to foreign IP: works
- UDP to foreign IP: works (DNS 8.8.8.8:53 responds)
- TLS handshake to foreign IP: timeout / connection reset
- Cloudflare CDN nodes return HTTP 403
- hy2 (UDP/QUIC, port 35000): timeout

## Timeline
- **June 16** — First successful proxy test (REALITY US node, xray)
- **Early July** — xray_access.log cleared (cat /dev/null > ...)
- **July 14** — Downloaded new xray binary, old config lost
- **July 15** — Extensive debugging: xray → sing-box → mihomo, all failed

## Tests Performed

### 1. Network layer
```
# Direct TCP 443
python3 -c "import socket; s=socket.create_connection(('unamecf.xn--ghqu5fm27b67w.com',443),timeout=8)"
→ Timeout

# Direct TCP 80
python3 -c "import socket; s=socket.create_connection(('httpbin.org',80),timeout=8)"
→ OK (4-10ms)

# DNS
timeout 3 bash -c 'echo > /dev/udp/8.8.8.8/53' && echo UDP_OK
→ UDP OK

# Direct TLS
openssl s_client -connect unamecf.xn--ghqu5fm27b67w.com:443 -servername ujp1.xn--ghqu5fm27b67w.com
→ Connection timed out
```

### 2. Proxy clients tested
| Client | Protocol | Result |
|--------|----------|--------|
| xray 26.3.27 | VLESS+REALITY (US 134.195.101.x) | TLS timeout |
| xray 26.3.27 | VLESS+WS (JP, Cloudflare) | 403/429/503 |
| sing-box 1.11.4 | hy2 US01 (globals-download.com:35000) | QUIC timeout |
| sing-box 1.11.4 | VLESS+WS US01 (Cloudflare) | ws close 1000 |
| mihomo 1.19.28 | hy2 US01 (443) | i/o timeout |
| mihomo 1.19.28 | VLESS+WS JP01 (443) | SSL connect error |

### 3. CF CDN behavior
- **unamecf.xn--ghqu5fm27b67w.com** — resolves, TCP connects, TLS fails (timeout)
- **downloadcfpro.xn--ghqu5fm27b67w.com** — HTTP 403 Forbidden on WS upgrade
- **104.18.125.69** (CF IP) — TCP connects, TLS fails

## Conclusion
The server's ISP (Beijing Unicom) blocks or interferes with TCP connections to foreign IPs on port 443. This affects:
- All VLESS+WS over TLS nodes (port 443)
- All VLESS+REALITY nodes (port 443)
- hy2 (UDP/QUIC) also affected, possibly due to UDP QoS or QUIC blocking

This is a **carrier-level egress restriction**, not a proxy config issue or node outage.

## Solutions NOT Tried (for future reference)
1. Node on non-443 port (e.g., 8443, 35000, random high port) — if any exist in subscription
2. Shadowsocks on random port — different protocol, less detectable
3. SSH tunnel via a third-party relay — bypasses port detection but requires a relay server
4. WireGuard over UDP on random port — if UDP isn't fully blocked
5. Changing exit IP (different NAT, different ISP, VPN to domestic relay)
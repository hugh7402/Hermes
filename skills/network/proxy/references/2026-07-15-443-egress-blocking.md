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
- **Early July** — xray_access.log cleared
- **July 14** — Downloaded new xray binary, old config lost
- **July 15** — Extensive debugging: xray → sing-box → mihomo, all failed

## Conclusion
The server's ISP (Beijing Unicom) blocks or interferes with TCP connections to foreign IPs on port 443. This affects all VLESS+WS over TLS (port 443), VLESS+REALITY (port 443), and hy2 (UDP/QUIC).

This is a **carrier-level egress restriction**, not a proxy config issue or node outage.

## Solutions NOT Tried (for future reference)
1. Node on non-443 port (e.g., 8443, 35000, random high port)
2. Shadowsocks on random port — different protocol, less detectable
3. SSH tunnel via a third-party relay
4. WireGuard over UDP on random port
5. Changing exit IP (different NAT, different ISP, VPN to domestic relay)

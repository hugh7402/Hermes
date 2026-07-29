# sing-box REALITY Success After IP+CF Block (July 18, 2026)

## Resolution of the July 15 blocking

The July 15 diagnosis (see `2026-07-15-443-egress-blocking.md`) concluded all nodes were blocked at the carrier level. This turned out to be **partially wrong** — the real situation was more nuanced.

## What actually worked

After changing the exit IP (PPPoE reconnect: 123.123.74.33 → 111.193.27.155) and switching from VLESS+WS to **VLESS+REALITY with direct IP**, the proxy worked.

### Node that worked
- **Protocol**: VLESS + REALITY + xtls-rprx-vision
- **Server**: `134.195.101.129:443` (direct IP, NOT domain `pq.aws48.yydnjc.top`)
- **SNI**: `updates.cdn-apple.com`
- **public_key**: `XpaYw0-hwSPxgV8K-WUbEaxbAwxjYVpDkDGOMONwUiA` (43 chars)
- **short_id**: `79f44f5c`
- **fingerprint**: `ios`
- **Exit**: US Cloudflare IPv6 (`2602:feda:...`)

### Test results
- Google: HTTP 302 ✅
- javdb: HTTP 200 ✅
- ifconfig.me: returns US IPv6 ✅

## Key findings

### 1. New IP still blocked by Cloudflare (VLESS+WS)

Even after changing IP to 111.193.27.155, VLESS+WS nodes through Cloudflare CDN still return **HTTP 403**. Raw WS upgrade test (Python socket + TLS + manual WS GET) confirmed the response header:

```
HTTP/1.1 403 Forbidden
cf-mitigated: challenge
server-timing: chlray;desc="a1d17a24187daf1b"
```

`cf-mitigated: challenge` is the **definitive signal** that Cloudflare triggered a bot/human-verification challenge based on the IP segment (likely a data-center/IDC-class IP range flag). This is **not a config error** — it's CF-level IP risk scoring.

### 2. REALITY works because it bypasses Cloudflare entirely

REALITY nodes connect **directly to AWS / 中华电信 servers** (134.195.101.x), not through Cloudflare CDN. The TLS handshake masquerades as traffic to `updates.cdn-apple.com` / `iosapps.itunes.apple.com`, so there's no CF layer to trigger a challenge.

| Protocol | Goes through CF? | Result on this IP |
|:----|:---:|:----|
| VLESS + WS + TLS | ✅ | ❌ 403 (CF challenge) |
| VLESS + REALITY | ❌ (direct to AWS) | ✅ Works |
| hy2 (UDP/QUIC) | ❌ | ❌ UDP blocked by carrier |

### 3. pbk copy-paste trap

The REALITY `public_key` is **43 characters** (base64url of 32 bytes, no padding). When copy-pasting from a subscription, it's extremely easy to grab one extra character (e.g., a trailing `e` that was actually base64 padding), producing a 44-char string that decodes to 33 bytes. sing-box then fails with `invalid public_key`.

Fix: validate before using — see the Pitfall in SKILL.md.

### 4. sing-box REALITY needs direct IP, not domain

sing-box's DNS resolution fails at outbound init for REALITY nodes configured with a domain (`pq.aws48.yydnjc.top` → `name error`), even though the domain resolves fine via `dig`/`getent`. The fix is to use the direct IP variant of the node from the subscription (same node, different `@host:port` line — one with domain, one with raw IP).

## Config that worked

`/opt/data/proxy-skill/reality_us01.json`:

```json
{
  "log": {"level": "warn", "timestamp": true},
  "dns": {
    "servers": [
      {"tag": "google", "address": "tls://8.8.8.8"},
      {"tag": "local", "address": "223.5.5.5", "detour": "direct"}
    ],
    "rules": [{"outbound": "any", "server": "local"}],
    "final": "google",
    "strategy": "ipv4_only"
  },
  "inbounds": [
    {"type": "mixed", "tag": "mixed-in", "listen": "127.0.0.1", "listen_port": 10808}
  ],
  "outbounds": [
    {
      "type": "vless",
      "tag": "reality-us01",
      "server": "134.195.101.129",
      "server_port": 443,
      "uuid": "6fdafbd6-a760-40f7-9265-67385b635fb5",
      "flow": "xtls-rprx-vision",
      "tls": {
        "enabled": true,
        "server_name": "updates.cdn-apple.com",
        "reality": {
          "enabled": true,
          "public_key": "XpaYw0-hwSPxgV8K-WUbEaxbAwxjYVpDkDGOMONwUiA",
          "short_id": "79f44f5c"
        },
        "utls": {"enabled": true, "fingerprint": "ios"}
      }
    },
    {"type": "direct", "tag": "direct"}
  ],
  "route": {"final": "reality-us01"}
}
```

## Management script

`/opt/data/proxy-skill/proxy.sh` — start/stop/restart/status/test/log. Validates config, starts sing-box in background, runs a self-check (curl through the proxy to ifconfig.me).

## Global env vars

`/opt/data/home/.bashrc` exports `http_proxy`/`https_proxy`/`ALL_PROXY` = `socks5://127.0.0.1:10808` so all child agents and subprocesses inherit the proxy automatically.

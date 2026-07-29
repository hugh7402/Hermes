# sing-box REALITY Success After IP+CF Block (July 18, 2026)

## What actually worked

After changing the exit IP (PPPoE reconnect: 123.123.74.33 → 111.193.27.155) and switching from VLESS+WS to **VLESS+REALITY with direct IP**, the proxy worked.

### Node that worked
- **Protocol**: VLESS + REALITY + xtls-rprx-vision
- **Server**: `134.195.101.129:443` (direct IP, NOT domain)
- **SNI**: `updates.cdn-apple.com`
- **public_key**: `XpaYw0-hwSPxgV8K-WUbEaxbAwxjYVpDkDGOMONwUiA` (43 chars)
- **short_id**: `79f44f5c`
- **fingerprint**: `ios`
- **Exit**: US Cloudflare IPv6

### Test results
- Google: HTTP 302 ✅
- javdb: HTTP 200 ✅
- ifconfig.me: returns US IPv6 ✅

## Key findings

### 1. New IP still blocked by Cloudflare (VLESS+WS)
Even after IP change, VLESS+WS nodes through Cloudflare return **HTTP 403** with `cf-mitigated: challenge` header. This is CF-level IP risk scoring, not a config error.

### 2. REALITY works because it bypasses Cloudflare
REALITY connects directly to AWS servers, not through Cloudflare CDN. TLS handshake masquerades as traffic to `updates.cdn-apple.com`.

| Protocol | Goes through CF? | Result |
|:----|:---:|:----|
| VLESS + WS + TLS | ✅ | ❌ 403 (CF challenge) |
| VLESS + REALITY | ❌ (direct to AWS) | ✅ Works |
| hy2 (UDP/QUIC) | ❌ | ❌ UDP blocked |

### 3. pbk must be exactly 43 chars
REALITY public_key is 43 chars base64url. Copy-paste from subscription easily grabs an extra character.

### 4. sing-box REALITY needs direct IP, not domain
sing-box DNS resolution fails at outbound init for REALITY nodes with domain names. Use the direct IP variant.

## Config that worked

See `/opt/data/proxy-skill/reality_us01.json` for the complete working config.

## Management script
`/opt/data/proxy-skill/proxy.sh` — start/stop/restart/status/test/log.

## Global env vars
`/opt/data/home/.bashrc` exports proxy env vars for all child processes.

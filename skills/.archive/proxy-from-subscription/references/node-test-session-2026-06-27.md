# Node Test Results — 2026-06-27

Subscription: `https://dash.xn--cp3a08l.com/api/v1/pq/53eca709b4fb562544949681e80cae21`

## Total Nodes: 63

### US Nodes (🇺🇸)

**三网推荐 (Reality, 134.195.101.x):**
| # | Name | IP | javdb | Notes |
|---|------|----|-------|-------|
| N56 | 圣何塞01 | 134.195.101.129 | ❌ 超时 | intermittent |
| N57 | 圣何塞02 | 134.195.101.137 | ✅ 200 | 出口 134.195.101.194 |
| N58 | 圣何塞03 | 134.195.101.178 | ✅ 200 | 出口 134.195.101.197 |
| N59 | 圣何塞04 | 134.195.101.207 | ✅ 200 | 出口 134.195.101.197 |
| N60 | 圣何塞05 | 134.195.101.122 | ⚠️ 301 | 出口 134.195.101.120 |
| N61 | 圣何塞06 | 134.195.101.182 | ❌ 超时 | |
| N62 | 圣何塞07 | 134.195.101.187 | ❌ 超时 | |
| N63 | 洛杉矶08 | 203.10.96.138 | ✅ 200 | 出口 203.10.96.139 |

**圣何塞 WS TLS (Cloudflare CDN, unamecf2):**
N34-N41 all failed (000) — likely WS config timing issue, not IP block

**阿什本 WS TLS (69.84.182.109):**
N42-N44 all failed (000)

**合适下载 WS TLS (Cloudflare CDN, downloadcfpro):**
N51-N55 all failed (000)

### Current config
- **Active node**: N57 (美国圣何塞02 | 三网推荐)
- **Outbound IP**: 134.195.101.194
- **Local ports**: SOCKS5 :10808, HTTP :10809
- **Config file**: `/opt/data/xray_config.json`
- **Start script**: `/opt/data/start_xray.sh`
- **PID file**: `/opt/data/xray.pid`

### N57 full VLESS params
```
UUID: 6fdafbd6-a760-40f7-9265-67385b635fb5
Host: 134.195.101.137:443
Type: tcp
Security: reality
Flow: xtls-rprx-vision
FP: ios
SNI: download.visualstudio.microsoft.com
pbk: EIk-WIEbq7Jl81SdCDZEu55CfhNo43sojC_1ZOKspSWo
sid: 51b8a9f3
```

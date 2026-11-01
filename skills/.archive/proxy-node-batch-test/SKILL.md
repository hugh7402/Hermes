---
name: proxy-node-batch-test
description: "换订阅/节点被封时批量测哪些节点可用：解析订阅→sing-box→逐个测javdb连通性。"
tags: [proxy, 订阅, 节点测试, sing-box, javdb, vless, trojan, 被封, 403]
trigger: 用户说"换节点"、"测节点"、"哪些节点能用"、"订阅更新了测一下"、"节点被封了"、新订阅地址要验证可用节点时加载。与 proxy skill 配合：proxy 管切换，本 skill 管批量验证。
---

# 代理订阅节点批量测试

**场景**：拿到新订阅/节点被封后，需要快速找出哪些节点能访问目标站（最常见 javdb，403 = IP 被封，3-7 天自动解除）。批量验证比逐个手动试快得多。

## 核心流程

1. **取订阅**：URL 或文件 → base64 解码（失败则按明文行处理）
2. **解析每行**：`vless:// trojan:// ss:// socks:// hysteria2://`（v2ray 订阅里 `https://` 前缀 = trojan）
3. **生成 sing-box 配置**：每节点独立端口起 sing-box 实例
4. **判定**：`curl --proxy http://127.0.0.1:<port> <JAVDB_TEST_URL>` → 200/302 = ✅ 可用、403 = ❌ 被封、000 = 连不上
5. **测速**（可选）：可用节点再过 Cloudflare 5MB 测速 `https://speed.cloudflare.com/__down?bytes=5000000`

**现成脚本**：`scripts/test_javdb_nodes.py <sub_file|sub_url> [--region 美国,台湾] [--speed]` → 结果存 `/tmp/javdb_ok_nodes.json`

## 解析踩坑（全部实测）

| 坑 | 处理 |
|---|---|
| 端口带 `/` 后缀（如 `35000/`） | `port.rstrip('/')` |
| 0.1倍/域名版节点无 `pbk`（非 reality） | TLS 配置里 reality 块**可选**（有 pbk 才加），否则 KeyError |
| sing-box 默认 tcp 时写 `"transport": {"type":"tcp"}` | 报 `outbounds[0].transport` 配置错误 → **默认 tcp 不写 transport 字段**；只有 ws 才写 |
| `ss://` 的 userinfo 是 base64(method:password) | `base64.b64decode(userinfo+'==')` |
| 节点名 URL 编码（emoji 地区） | `urllib.parse.unquote(#后面的部分)` |
| hysteria2 端口同样可能带 `/` | 同上 rstrip |

## javdb 判定细节

- 测试 URL：`https://javdb.com/over18?respond=1`（302 是正常的 over18 重定向 = 可用）
- **403 + "The owner of this website has banned your access" = IP 被封**，换节点唯一解法，别反复重试同一节点
- 403 封锁规律（2026-08-26 实测 69 节点）：机场美国圣何塞 134.195.101.x 整段、AWS 日本/新加坡、台湾部分节点常被封；**台湾个别节点（如 TW3）常是最后活口**，慢但能用
- 0.1倍/域名版（TLS 非 reality）节点通常连不上（000），优先测三网推荐/直连 IP 组

## 换到可用节点

测出可用节点后，把该节点的 vless 参数（server/uuid/flow/tls.reality 的 pbk/sid/sni）写入 proxy skill 的 `reality_active.json`（保持 inbound 端口 10808），然后 `bash /opt/data/proxy-skill/proxy.sh restart`，验证 `proxy.sh status` 出口 IP 变化 + curl javdb 首页 200。

## 免费备用订阅源（2026-08-26 验证）

- `zhuhaiuk/free-nodes`：每小时更新，72 节点覆盖 US/TW/HK/KR/JP/欧洲
  - Clash: `https://raw.githubusercontent.com/zhuhaiuk/free-nodes/main/clash_config.yaml`
  - Base64: `https://raw.githubusercontent.com/zhuhaiuk/free-nodes/main/nodes.txt`
- `Au1rxx/free-vpn-subscriptions`：每小时刷新、HTTP 实测验证、按国家分类
- `Pawdroid/Free-servers`、`freefq/free`：经典老牌
- ⚠️ 免费节点无安全保证，仅用于访问公开内容，勿登录敏感账号

## 注意

- 每个节点测试约 10-15s（连接等待 + javdb 请求），71 节点全测 ≈ 15 分钟，可后台跑
- 测试用独立端口（22800+ 随机），避免与正式代理 10808 冲突
- `proxy_auto_switch.sh` 无参数跑曾因 `set -u` + `$1` 崩溃（已修为 `${1:-}`）——换节点优先手动指定 `--node usXX`

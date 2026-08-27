---
name: proxy
description: 统一代理/翻墙 skill。管理 sing-box 代理服务（启动/停止/自动切换节点/故障排查），整合 xray/sing-box/mihomo 多种方案。IP被封或节点失效时自动从订阅换节点。所有需要翻墙的应用、skill、cron 统一通过此 skill 调用，自动触发。
tags: [proxy, vpn, network, sing-box, xray, mihomo, vless, reality, 翻墙, 订阅, 自动切换]
trigger: 任何 skill/cron/service 需要访问境外资源时，自动加载本 skill。用户说"翻墙""代理""上不去""403""被墙""连不上github""IP被封""节点失效""换节点"时触发。
---

# proxy — 统一代理翻墙 skill

## 架构

```
proxy skill (Hermes 接口层)
│  SKILL.md — 使用说明 + 故障排查
│
├── 基础设施层（/opt/data/proxy-skill/）
│   ├── proxy.sh               → 启动/停止/状态/测速
│   ├── proxy_auto_switch.sh   → 自动切换节点（订阅→解析→测试→切换）
│   ├── subscription.conf      → 订阅地址 + 上次好节点（用户提供）
│   ├── sing-box               → 代理核心
│   ├── reality_active.json    → 当前活动配置（由自动切换脚本维护）
│   ├── reality_us05.json      → 已验证节点配置
│   └── node_*.json            → 自动切换生成的临时节点配置
│
└── 全局环境变量（/opt/data/home/.bashrc）
    export http_proxy=socks5://127.0.0.1:10808
    export https_proxy=socks5://127.0.0.1:10808
    export ALL_PROXY=socks5://127.0.0.1:10808
```

所有需要翻墙的 skill/cron 在 SKILL.md 的 frontmatter 中声明 `requires-skills: [proxy]`，即可自动加载本 skill 并继承代理环境。

## 快速使用

```bash
# 启动（含连通性自检）
bash /opt/data/proxy-skill/proxy.sh start

# 停止
bash /opt/data/proxy-skill/proxy.sh stop

# 查看状态 + 出口 IP
bash /opt/data/proxy-skill/proxy.sh status

# 测试 Google + 目标站
bash /opt/data/proxy-skill/proxy.sh test

# 查看实时日志
bash /opt/data/proxy-skill/proxy.sh log

# 🆕 自动切换节点（IP被封/节点失效时）
bash /opt/data/proxy-skill/proxy_auto_switch.sh --node us05   # 指定节点
bash /opt/data/proxy-skill/proxy_auto_switch.sh                # 自动遍历全部节点
```

## 🆕 自动切换节点（核心功能 2026-08-04）

**用户要求**：IP 被封或节点失效时，自行从订阅更换代理节点，不更换订阅源。

**配置文件**：`/opt/data/proxy-skill/subscription.conf`
```
SUBSCRIPTION_URL="https://dasho.xn--cp3a08l.com/api/v1/pq/..."  # 订阅地址（用户提供）
LAST_GOOD_NODE="us05"                                          # 上次成功节点
PROXY_PORT=10808
JAVDB_TEST_URL="https://javdb.com/over18?respond=1"            # 连通性测试目标
```

**脚本流程**（`proxy_auto_switch.sh`）：
1. 下载订阅（base64 解码 → 71 个节点，存 `/tmp/sub_decoded.txt`）
2. `--node usXX` 模式：把 usXX 映射到订阅节点名（us05 → "🇺🇸美国圣何塞05 | 三网推荐"）
3. 从订阅行解析节点参数（uuid/server/port/sni/pbk/sid/fp）→ 生成 sing-box 配置
4. `test_node`：独立端口启动 sing-box → curl 测试 javdb → 200/302 算可用
5. 可用 → 复制到 `reality_active.json` → 更新 proxy.sh CONFIG → 重启 → 更新 LAST_GOOD_NODE
6. 无 `--node` 参数：按优先级遍历全部节点（圣何塞直连IP > 美国 > 其他）

## 当前活动节点（2026-08-26 更新）

| 参数 | 值 |
|------|-----|
| 节点 | AWS新加坡02（SG-AWS02，三网推荐） |
| 协议 | VLESS + REALITY + xtls-rprx-vision |
| 域名 | pq.aws64.yydjc.top:443 |
| 出口 | 67.159.48.147（新加坡） |
| SNI | iosapps.itunes.apple.com |
| 实测速度 | ~7.7MB/s |
| 配置 | `/opt/data/proxy-skill/reality_active.json` |
| 启动命令 | `bash /opt/data/proxy-skill/proxy.sh start` |

**订阅地址 2026-08-26 更新**：`https://dasho.pqjc.site/api/v1/pq/53eca709b4fb562544949681e80cae21`（用户提供最新收费订阅，流量 1.33TB）

**⚠️ javdb 封锁现状（2026-08-26 全量测试 69 节点，两轮）**：
- ❌ 美国圣何塞 134.195.101.x 整段（us01-us07）403 被封
- ❌ 美国洛杉矶 203.10.96.138 403 被封
- ❌ AWS 日本 ×10 全部 403
- ❌ AWS 新加坡 01/03/04/05 403
- ✅ **AWS新加坡02（SG-AWS02）解封可用**，7.7MB/s，当前活动节点
- ✅ 台湾3（TW3）曾可用（223KB/s）作备用，08-26 晚抖动 000
- ❌ 0.1倍/域名版节点全部连不上（000）

**免费备用源（zhuhaiuk/free-nodes，用户已入 Clash Verge）**：
- Clash: `https://raw.githubusercontent.com/zhuhaiuk/free-nodes/main/clash_config.yaml`
- Base64: `https://raw.githubusercontent.com/zhuhaiuk/free-nodes/main/nodes.txt`
- 测过 22 节点仅 US 03（ss）能通 javdb 但测速≈0，仅应急

**节点命名规则**：订阅里有两组"圣何塞"节点，**必须选 "三网推荐" 组（IP 直连 134.195.101.x, REALITY 协议）**，不要选 "0.1倍" 组（域名 unamecf2, TLS 协议，通常不可用）。

| usXX | 节点名 | IP |
|------|--------|-----|
| us01 | 圣何塞01 | 134.195.101.129 |
| us02 | 圣何塞02 | 134.195.101.137 |
| us03 | 圣何塞03 | 134.195.101.178 |
| us04 | 圣何塞04 | 134.195.101.207 |
| **us05** | **圣何塞05** | **134.195.101.122** ✅ 当前 |
| us06 | 圣何塞06 | 134.195.101.182 |
| us07 | 圣何塞07 | 134.195.101.187 |

## 故障排查

### 所有节点全超时 / IP 被封
```bash
# 1. 检查代理是否运行
bash /opt/data/proxy-skill/proxy.sh status

# 2. 检查 javdb 是否被封（403 + "banned your access" = IP 被封）
curl -s --max-time 15 --proxy http://127.0.0.1:10808 -A "Mozilla/5.0" \
  -c /tmp/jdb_cookies.txt "https://javdb.com/over18?respond=1" -w "%{http_code}\n"

# 3. 自动切换节点（核心命令！）
bash /opt/data/proxy-skill/proxy_auto_switch.sh --node us05   # 指定上次好节点
bash /opt/data/proxy-skill/proxy_auto_switch.sh                # 全节点遍历

# 4. 检查本地端口
ss -tlnp | grep 10808

# 5. 检查日志
bash /opt/data/proxy-skill/proxy.sh log | tail -20
```

**⚠️ 判断 IP 是否被封**：javdb 返回 `403` + 内容含 "The owner of this website has banned your access" + 显示出口 IP = 该节点 IP 被封（3-7天自动解除）。**换节点是唯一即时解法**，不要反复重试同一节点。

### Cloudflare 403/503
REALITY 节点不走 CF，如果 REALITY 也不通，换其他协议配置：
```bash
bash /opt/data/proxy-skill/proxy.sh stop
bash /opt/data/proxy-skill/proxy.sh restart   # 换 reality_active.json 指向别的节点
```

## 其他 skill 如何调用本代理

### 方式 1：声明依赖（推荐）
在其他 skill 的 frontmatter 加：
```yaml
requires-skills: [proxy]
```
自动生效：代理环境变量 + 未运行时自动启动 + 出口 IP 验证。

### 方式 2：直接调用
```bash
bash /opt/data/proxy-skill/proxy.sh start
```

## 全局代理（所有子进程/子智能体自动使用）

```bash
# ~/.bashrc 中的配置（已设好，无需重复操作）
export http_proxy=socks5://127.0.0.1:10808
export https_proxy=socks5://127.0.0.1:10808
export HTTP_PROXY=socks5://127.0.0.1:10808
export HTTPS_PROXY=socks5://127.0.0.1:10808
export ALL_PROXY=socks5://127.0.0.1:10808
export NO_PROXY=localhost,127.0.0.1,.local,.internal,223.5.5.5,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16
```

## 踩坑记录

### 🚨 订阅节点解析陷阱（2026-08-04）
1. **REALITY 节点 ≠ TLS 节点**：订阅里 `security=reality` 的节点必须用 reality 配置（pbk/sid/fp），用普通 TLS 配置会全部超时（"bad HTTP protocol version"）。检查 `security` 参数决定配置类型。
2. **`usXX` 映射歧义**：订阅里可能有两个"圣何塞05"（如 "0.1倍" 域名版和 "三网推荐" IP直连版）。**优先映射"三网推荐"组**（`'三网推荐' in full_name` 判断，注意要用完整名字——`split('|')[0]` 会切掉 "三网推荐" 导致判断永远 False）。
3. **URL 编码的 sid**：订阅参数 `sid` 的值是 `2546d239#%F0%9F%87%BA...`（URL 编码的节点名混入），解析时必须 `urllib.parse.unquote(params.get('sid','')).split('#')[0]`，否则 sing-box 报配置错误。
4. **base64 订阅 vs 解码后行号**：`sed` 取行必须用解码后的 `/tmp/sub_decoded.txt`（原始 base64 是一整行）。python 里 0-indexed 行号 → sed 用 `$((idx+1))`。
5. **端口冲突**：test_node 用随机端口（21900+RANDOM%50），避免和正式代理 10808 冲突。

### 历史踩坑
- **443 端口阻断**（2026-07-15）：某些网络环境封 443 出站，REALITY 全挂。诊断见 references。
- **Cloudflare 出口封禁**（2026-07-18）：VLESS WS 节点返回 403 + `cf-mitigated: challenge` 时是 CF 封了出口 IP 段，换 REALITY 直连节点（不走 CF CDN）。

## 多协议支持对比

| 协议 | 适用场景 | 需安装 | skill 中用法 |
|------|---------|--------|-------------|
| **sing-box + REALITY** | 主力，抗封强 | 已装 | proxy.sh start |
| **xray + REALITY** | 备用 | 未装（需下载） | 见参考文档 |
| **sing-box + hysteria2** | UDP/QUIC 场景 | 已装 | 切 hy2_sg.json |
| **mihomo** | 各选方案 | 未装 | 见参考文档 |

## 参考文档

本 skill 目录下的 reference/ 文件包含详细的技术细节：
- `references/2026-06-27-node-test-results.md` — 节点测速数据
- `references/2026-07-15-443-egress-blocking.md` — 443 端口阻断诊断
- `references/2026-07-18-singbox-reality-success.md` — sing-box + REALITY 配置成功记录
- `references/gepa-evolution-findings.md` — GEPA 优化分析
- `references/2026-08-04-auto-switch.md` — 自动切换节点实现记录（订阅解析/us05映射/踩坑）

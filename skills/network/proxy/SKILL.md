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

### 节点能通但被限速（几百 KB/s / 大文件中途归零）—— 出口配额打光

第三种故障态，既不是 403 也不是超时：`proxy.sh status` 一切正常、`curl` 探测返回 204、目标站也能连，**但大流量下载卡在几百 KB/s，或者跑到一半进度直接归零**。

**根因**：节点出口带宽/配额被打光。同一个节点连续拉几个 GB 之后就会进这个状态（本次：新加坡节点上午拉了 1.33GB 后，下一批就掉到 566KB/s 并中途停住）。此时**加代理和不加代理一样慢**——因为你已经在走代理了，慢的是代理那一侧。

**误判警示**：这种状态很容易被当成「单个文件被限速」去反复换片源/换版本，**白耗时间**。判据很干脆：

> **同期别的文件快不快？** 快 → 是该文件被限速；**不快/都慢 → 是节点配额，换版本没用，换节点。**

**解法**：换节点（不是重启代理，重启同一个节点没用）：

```bash
bash /opt/data/proxy-skill/proxy.sh status                      # 看当前出口 IP，记住它
bash /opt/data/proxy-skill/proxy_auto_switch.sh --node us05     # 换成另一个节点
bash /opt/data/proxy-skill/proxy.sh status                      # 确认出口 IP 已变
```

实测：同一批 2.85GB 文件，旧节点 566KB/s 且中途归零，切到圣何塞05 后**立刻 25MB/s**。

**大流量下载的用法**：命令行工具要把代理**显式传给它**（而不是只靠环境变量），例如 rclone 的 webdav 后端：

```bash
rclone copy "pikpak:/Movie" /tmp/dest --http-proxy "http://127.0.0.1:10808" ...
```

**用量预算**：一个节点大约能跑几个 GB 的大流量下载。**不要拿同一个节点连续跑十几 GB**，分批换节点比中途发现限速再重试划算。

### 🚨 进程在跑但端口没监听 —— 「假活」的 sing-box（并发切节点之后最常见的坏状态）

第四种故障态，和前三种都不一样：`ps` 里能看到 `sing-box run -c …/reality_active.json`，但

- `proxy.sh status` 报「未运行」
- `proxy.sh start` 报 `FATAL start service: start inbound/mixed[0]: listen tcp 127.0.0.1:10808: bind: address already in use`
- 所有 `curl -x http://127.0.0.1:10808` 返回 `000`

**根因**：上一个实例还占着端口但已经失去功能。典型诱因是**两条进程并发 `proxy.sh stop/start` 抢切节点**——
后起的那个 bind 失败、却没退出，于是「端口被占」和「连不通」同时成立。它既不监听也不退出，重启也没用。

**处置（按顺序，不要跳过第 1 步直接 restart）**：

```bash
# 1. 按精确 PID 杀掉那个假活的 sing-box
ps -eo pid,etime,cmd | grep -F '/opt/data/proxy-skill/sing-box run' | grep -v grep
kill <pid>

# 2. 用已知能通的节点配置重启（先 check 配置，再 start）
cp "/opt/data/proxy-skill/node_🇺🇸美国圣何塞03.json" /opt/data/proxy-skill/reality_active.json
/opt/data/proxy-skill/sing-box check -c /opt/data/proxy-skill/reality_active.json
bash /opt/data/proxy-skill/proxy.sh start

# 3. 用真实请求验活
curl -s -o /dev/null -w '%{http_code}\n' -m 10 -x http://127.0.0.1:10808 https://www.google.com/generate_204
```

**`ss -lntp | grep 10808` 可能是空的，而代理其实是好的**（权限不足看不到 socket）。
**判活一律以 `curl … generate_204` 返回 204 为准**：不要因为 `ss` 没输出就判代理没起来，
也不要因为 `ps` 有进程就判代理正常。

**不要用 `pkill -f sing-box` / `pkill -f 'python3 xxx.py'` 这类按模式杀的写法**——模式串会出现在执行它的
那个 shell 自己的命令行里，把它们自己也杀掉（本环境还有工具守卫会直接拦下这类命令）。
一律 `kill <精确 pid>`，或对 Hermes 后台任务用 `process_manage(action='kill', session_id=...)`。

**根本预防：同一时刻只允许一个进程切节点。** 所有轮换脚本都在改写 `reality_active.json` 并
`proxy.sh stop/start`，两条并发就是互相把对方刚切好的节点顶掉，甚至造出上面这种假活状态。
收到新任务先看有没有轮换在跑，排队，不要并发。走直连的任务（WebDAV rclone、`--noproxy '*'` 的站点）
不受影响，可以和切节点任务同时跑。

### 🚦 常用金融/宏观数据源可达性（2026-11-26 实测）

做数据类任务前先看这张表，不要逐个盲试。**原则：能直连的一律直连（不占代理带宽、不依赖代理存活），只有被 403 的才走代理。**

| 数据源 | 直连 | 走代理 | 备注 |
|---|---|---|---|
| 美财政部实际收益率曲线 CSV | ✅ | — | `home.treasury.gov/.../daily-treasury-rates.csv`，含 10Y TIPS，免 key，全年历史 |
| 美财政部 FiscalData API | ✅ | — | 国债总额 `api.fiscaldata.treasury.gov/.../debt_to_penny` |
| 新浪行情 hq.sinajs.cn | ✅ | — | 需带 `Referer: finance.sina.com.cn` |
| 东财 push2 / push2his | ✅ | — | Au99.99 历史日线（secid=118.AU9999） |
| **CFTC COT** | ❌ 403 | ✅ | 新旧两个接口直连都 403，必须走代理 |
| **Yahoo Finance** query1/query2 | ❌ 403 | ✅ | ^VIX、GLD、GC=F、DX-Y.NYB、ZQ=F 全靠它 |
| WGC gold.org | — | ✅ | 央行购金、ETF 流量 |
| **FRED** fred.stlouisfed.org | ❌ 超时 | ❌ SSL 错 | **全部路径不通，不要再试**，用财政部替代 |
| CME FedWatch 页面 | ❌ | ❌ 403 | 改用 Yahoo `ZQ=F` 自己算降息概率 |

**调用要点**：Python 里建带代理的 opener 时必须同时换 HTTPSHandler 的 context，否则某些站报 `RECORD_LAYER_FAILURE`：
```python
ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
op = urllib.request.build_opener(
    urllib.request.ProxyHandler({'http':'http://127.0.0.1:10808','https':'http://127.0.0.1:10808'}),
    urllib.request.HTTPSHandler(context=ctx))
```
代理端口是 **HTTP 混入**（`http://127.0.0.1:10808` 可用），不是纯 socks5；`curl -x http://127.0.0.1:10808` 也一样。

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

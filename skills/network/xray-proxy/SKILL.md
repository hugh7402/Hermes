---
name: xray-proxy
description: 在无 systemd 的容器/无头服务器中，从 V2Ray VLESS 订阅链接搭建 xray SOCKS5/HTTP 代理，批量测试节点可用性，持久后台运行。
---

# xray-proxy

在容器/无头环境中从 VLESS 订阅搭建 xray 代理，用于访问被墙网站（javdb, YouTube 等）。

## 触发条件

- 用户说「装个代理」「翻墙」「上不去 javdb」「xray」「V2Ray」
- **任何 skill 或接口被墙时**（用户偏好 2026-07-18）：当 web_search/web_extract/javdb/github 等海外接口超时或返回 403/连接重置时，**先启动代理再重试**，不要反复重试同一不通的路径。启动命令：`bash /opt/data/proxy-skill/proxy.sh start`
- 用户提供了 VLESS 订阅链接或节点配置
- 容器/服务器没有 systemd，不能跑标准 VPN 客户端

## 工作流

### 1. 获取 xray 二进制

如果 GitHub 被墙，从 Gitee 镜像下载（实测 gitee.com 在国内可访问）：

```bash
# 从 GitHub 官方下载
curl -sL https://github.com/XTLS/Xray-core/releases/latest/download/Xray-linux-64.zip -o /tmp/xray.zip

# 从 Gitee 镜像下载（GitHub 被墙时）
curl -sL https://gitee.com/xtls/Xray-core/releases/download/v26.3.27/Xray-linux-64.zip -o /tmp/xray.zip

cd /tmp && unzip -o xray.zip -d xray/ && rm xray.zip
# 验证: /tmp/xray/xray version
```

> ⚠️ 如果 `unzip` 未安装，用 `apt install unzip -y` 安装。

### 2. 解析订阅链接

订阅内容为 base64 编码的多行 VLESS 链接，每行格式：
```
vless://<uuid>@<host>:<port>?type=<transport>&security=<tls|reality>&...&pbk=<publicKey>&sid=<shortId>#<名称>
```

关键参数：
| 参数 | 用途 | 必填（reality） |
|:----|:----|:----:|
| `type` | 传输协议：`tcp` / `ws` | ✅ |
| `security` | 加密方式：`tls` / `reality` | ✅ |
| `flow` | 流控：`xtls-rprx-vision` | ✅ |
| `sni` | TLS SNI 域名 | ✅ |
| `fp` | TLS 指纹：`chrome` / `ios` / `safari` | ✅ |
| `pbk` | Reality 公钥（**极易遗漏！**） | ✅ reality only |
| `sid` | Reality shortId（**极易遗漏！**） | ✅ reality only |
| `host` | WebSocket Host 头 | ✅ WS TLS only |
| `path` | WebSocket 路径 | ✅ WS TLS only |

**⚠️ 关键陷阱**：解析 VLESS 链接时，`pbk` 和 `sid` 参数在链接末尾（`#` 之前），如 `curl` 输出截断会丢失！务必获取完整链接（400+ chars）。使用 `re.findall(r'vless://[^\s\r\n]+', decoded)` 确保捕获完整链接。

### 3. 构建 xray 配置

#### Reality（三网推荐节点）

```python
config = {
    "log": {"loglevel": "warning"},
    "inbounds": [{
        "tag": "socks-in", "port": 10808, "listen": "127.0.0.1",
        "protocol": "socks", "settings": {"auth": "noauth", "udp": True}
    }, {
        "tag": "http-in", "port": 10809, "listen": "127.0.0.1",
        "protocol": "http", "settings": {}
    }],
    "outbounds": [{
        "tag": "proxy", "protocol": "vless",
        "settings": {
            "vnext": [{
                "address": host, "port": port,
                "users": [{"id": uuid, "encryption": "none", "flow": flow}]
            }]
        },
        "streamSettings": {
            "network": "tcp", "security": "reality",
            "realitySettings": {
                "serverName": sni,           # 从 VLESS 的 sni 参数
                "fingerprint": fp,            # ios/chrome/safari
                "show": False,
                "publicKey": pbk,             # ⚠️ 必须！从 VLESS 的 pbk 参数
                "shortId": sid                # ⚠️ 必须！从 VLESS 的 sid 参数
            }
        }
    }]
}
```

#### WebSocket + TLS（Cloudflare CDN 节点）

```python
config["outbounds"][0]["streamSettings"] = {
    "network": "ws",
    "security": "tls",
    "tlsSettings": {
        "serverName": sni or host_header,
        "fingerprint": fp,
        "allowInsecure": insecure == "1"
    },
    "wsSettings": {
        "path": path,                        # 从 VLESS 的 path 参数
        "headers": {"Host": host_header}     # 从 VLESS 的 host 参数
    }
}
```

### 4. 启动和测试

```bash
# 启动 xray（后台持久运行）
nohup /tmp/xray/xray run -c /opt/data/xray_config.json > xray_stdout.log 2>&1 &

# 测试代理
export https_proxy=socks5://127.0.0.1:10808
curl -s --socks5 127.0.0.1:10808 https://httpbin.org/ip   # 查出口 IP
curl -s -L -o /dev/null -w "%{http_code}" --socks5 127.0.0.1:10808 https://www.javdb.com  # 测试目标站
```

测试结果解释：\n- `200` ✅ 完全可用\n- `301` / `302` ⚠️ 可用（重定向到首页/登录）\n- `403` ❌ IP 被目标站封禁\n- `000` / 超时 ❌ 代理未连通或配置错误\n\n### 4a. 直连验证法（绕过 xray）\n\n当 xray 报超时但不确定是配置问题还是节点问题时，直接用 Python 测试节点本身：\n\n```python\nimport socket, ssl\n# Reality 节点直连测试\ns = socket.create_connection((\n    # host:port 从订阅解析\n), timeout=8)\nprint('TCP:', s.getpeername())\ns.close()\n\n# WS+TLS 节点直连测试\nhost = 'unamecf.xn--ghqu5fm27b67w.com'  # 节点的实际域名\nsni = 'ujp1.xn--ghqu5fm27b67w.com'      # VLESS 链接中的 sni 参数\ns = socket.create_connection((host, 443), timeout=8)\nctx = ssl.create_default_context()\nctx.check_hostname = False\nctx.verify_mode = ssl.CERT_NONE\nss = ctx.wrap_socket(s, server_hostname=sni)\nprint('TLS OK, cipher:', ss.cipher()[0])\nss.close()\n```\n\n如果直连 TCP+TLS 都成功但 xray 超时，说明配置本身有误或节点触发了限流。如果直连都失败（TCP 超时/TLS reset），说明节点已宕机。

### 5. 批量测试节点

从订阅中提取所有节点，逐个启动 xray → 测试目标站 → 记录结果。重点优先测试标有「三网推荐」的节点。

典型测试方法：

```python
# 对每个节点:
# 1. 构建配置写入临时文件
# 2. 启动 xray 子进程，等 2s 启动
# 3. curl --socks5 127.0.0.1:10808 测试目标站
# 4. 终止 xray，清临时文件
# 5. 间隔 1s 再测下一个（避免端口冲突）
```

> ⚠️ 子进程启动后要 `time.sleep(2)` 等 xray 初始化完成再测。

## 持久化运行

在无 systemd 的容器中，用 nohup + PID 文件管理：

```bash
# start_xray.sh
PIDFILE="/opt/data/xray.pid"
nohup /tmp/xray/xray run -c /opt/data/xray_config.json > /opt/data/xray_stdout.log 2>&1 &
echo $! > $PIDFILE

# 停止
kill $(cat /opt/data/xray.pid)

# 检查是否存活
kill -0 $(cat /opt/data/xray.pid) && echo "running"
```

> 容器重启后需要手动重新启动 xray。

## sing-box（替代xray，支持hy2/hysteria2）

当订阅包含 hy2/hysteria2 节点时，xray不支持此协议，需使用 sing-box。

### 安装

当 GitHub 被墙时使用 ghfast.top 镜像：

```bash
curl -sL "https://ghfast.top/https://github.com/SagerNet/sing-box/releases/download/v1.11.0/sing-box-1.11.0-linux-amd64.tar.gz" -o /tmp/sing-box.tar.gz
tar xzf /tmp/sing-box.tar.gz -C /tmp
cp /tmp/sing-box-*/sing-box /opt/data/sing-box
```

验证文件大小：被墙的下载会返回 9-12 bytes，正常约 12MB。

### 配置映射（xray → sing-box）

| 功能 | xray | sing-box |
|------|------|----------|
| SOCKS5 inbound | `{"protocol":"socks","port":10808}` | `{"type":"socks","listen_port":10808}` |
| HTTP inbound | `{"protocol":"http","port":10809}` | `{"type":"mixed","listen_port":10809}`（一个mixed替代两个） |
| VLESS+WS | `protocol:"vless"` + `streamSettings.network:"ws"` | `type:"vless"` + `transport.type:"ws"` |
| TLS指纹 | `tlsSettings.fingerprint:"chrome"` | `tls.utls.fingerprint:"chrome"` |
| Reality | `realitySettings.publicKey` | `tls.reality.public_key` |
| hy2 | 不支持 | `type:"hysteria2"` + `tls.enabled:true` |
| 路由 | `routing.rules[].outboundTag` | `route.rules[].outbound` |

### hy2 配置要点

```json
{
  "type": "hysteria2",
  "tag": "proxy",
  "server": "pq.us1.globals-download.com",
  "server_port": 35000,
  "password": "UUID_从订阅获取",
  "tls": {
    "enabled": true,
    "server_name": "www.apple.com",    // 从订阅 sni 参数
    "insecure": true                   // Go 1.23+ 需要，因为很多hy2节点证书无SAN
  },
  "down_mbps": 50,
  "up_mbps": 10
}
```

**hy2 注意事项**：
- Go 1.23+ 拒绝使用旧版 Common Name 字段（无 SAN）的证书 → 必须设 `"insecure": true`
- 订阅中的 `mport=35000-39000` 表示多端口支持，配置时只用基端口（35000）
- hy2 使用 UDP/QUIC 传输，TCP 连接会超时（正常现象）
- 测试UDP连通性：`timeout 5 bash -c 'echo > /dev/udp/HOST/PORT' && echo "UDP OK"`
- 部分 hy2 节点首次连接需要约 3-5s 的 QUIC 握手时间

### 运行 sing-box（无 systemd）

```bash
nohup /opt/data/sing-box run -c /opt/data/singbox_config.json > /opt/data/singbox_stdout.log 2>&1 &
echo $! > /tmp/singbox.pid
```

**端口释放**：旧xray/ss进程可能占用10808端口不释放，用 Python 遍历 /proc 找到 socket inode 对应的进程强制 kill：
```python
import os
with open('/proc/net/tcp') as f:
    for line in f.readlines()[1:]:
        port = int(line.split()[1].split(':')[1], 16)
        if port == 10808:
            sock_inode = line.split()[9]
            for pid in os.listdir('/proc'):
                if not pid.isdigit(): continue
                try:
                    for fd in os.listdir(f'/proc/{pid}/fd'):
                        link = os.readlink(f'/proc/{pid}/fd/{fd}')
                        if f'socket:[{sock_inode}]' in link:
                            os.kill(int(pid), 9)
                except: pass
            break
```

## mihomo（Clash Meta 内核 — 备选方案）

当 xray 和 sing-box 都连不上时，mihomo（原 Clash.Meta）可能走通——它使用不同的协议实现栈，部分订阅商的 CF 风控策略对 mihomo 的 TLS 指纹握手容忍度更高。

### 安装

```bash
# 通过 ghfast.top 加速下载
VER="v1.19.28"
curl -fSLo /tmp/mihomo.gz \
  "https://ghfast.top/https://github.com/MetaCubeX/mihomo/releases/download/${VER}/mihomo-linux-amd64-${VER}.gz"
gunzip -f /tmp/mihomo.gz
chmod +x /tmp/mihomo
mkdir -p /opt/data/mihomo
cp /tmp/mihomo /opt/data/mihomo/
/opt/data/mihomo/mihomo -v  # 验证版本
```

### 订阅转 Clash YAML 配置

标准 clash 配置格式 vs xray JSON——mihomo 原生支持 YAML 配置，不能直接用 xray 的 JSON。

订阅通常是 base64 编码的通用链接（vless://、ss://、trojan:// 每行一个），需要用 Python 转换为 clash YAML 格式。

参考脚本 `scripts/convert_sub_to_clash.py`（见本技能 `scripts/` 目录）——将 base64 订阅链接转换为 mihomo 可以直接用的 YAML 配置。

快速配置步骤：

```bash
# 1. 下载订阅 → base64 解码为每行一个链接
curl -s "订阅URL" | base64 -d > /tmp/nodes.txt

# 2. 用脚本生成 clash YAML 配置
python3 /opt/data/skills/network/xray-proxy/scripts/convert_sub_to_clash.py \
  --nodes /tmp/nodes.txt \
  --socks-port 10808 \
  --mixed-port 10809 \
  -o /opt/data/mihomo/config.yaml

# 3. 启动
/opt/data/mihomo/mihomo -d /opt/data/mihomo/ &
```

### 配置要点

mihomo 的 YAML 配置结构：

```yaml
# config.yaml 核心结构
port: 10808          # SOCKS5 代理端口
mixed-port: 10809    # HTTP(S)+SOCKS 混合端口
allow-lan: false
mode: rule
log-level: warning

proxies:
  - name: "🇯🇵日本东京01-0.1倍"
    type: vless
    server: unamecf.xn--ghqu5fm27b67w.com
    port: 443
    uuid: 6fdafbd6-a760-40f7-9265-67385b635fb5
    network: ws
    tls: true
    udp: true
    servername: ujp1.xn--ghqu5fm27b67w.com
    ws-opts:
      path: "/pq/jp1"
      headers:
        Host: ujp1.xn--ghqu5fm27b67w.com
    client-fingerprint: ios  # 必须匹配 VLESS 链接的 fp 参数

proxy-groups:
  - name: Proxy
    type: select
    proxies:
      - 🇯🇵日本东京01-0.1倍
      # ... 更多节点

rules:
  - MATCH,Proxy  # 所有流量走代理
```

**重要参数对照（VLESS → Clash YAML）：**

| VLESS 参数 | Clash YAML 字段 | 说明 |
|:----------|:----------------|:-----|
| `type=ws` | `network: ws` | 传输协议 |
| `security=tls` | `tls: true` | TLS 加密 |
| `security=reality` | `reality: true` + `flow: xtls-rprx-vision` | Reality 协议 |
| `host` | `ws-opts.headers.Host` | WS Host 头 |
| `path` | `ws-opts.path` | WS 路径 |
| `fp` | `client-fingerprint` | TLS 指纹（⚠️ 关键！） |
| `sni` | `servername` | TLS SNI |
| `pbk` | `reality-opts.public-key` | Reality 公钥 |
| `sid` | `reality-opts.short-id` | Reality shortId |

### 运行（无 systemd）

```bash
cd /opt/data/mihomo
nohup ./mihomo -d . > mihomo.log 2>&1 &
echo $! > /tmp/mihomo.pid
```

测试代理：
```bash
curl -s --socks5 127.0.0.1:10808 --connect-timeout 5 --max-time 10 https://httpbin.org/ip
curl -s -L -o /dev/null -w "%{http_code}" --socks5 127.0.0.1:10808 https://www.google.com
```

### mihomo vs xray vs sing-box 对比

| 能力 | xray | sing-box | mihomo |
|:----|:----|:---------|:-------|
| VLESS+REALITY | ✅ | ✅ | ✅ |
| VLESS+WS+TLS | ✅（已deprecated） | ✅ | ✅ |
| Hysteria2 | ❌ | ✅ | ✅ |
| Shadowsocks | ✅ | ✅ | ✅ |
| Trojan | ✅ | ✅ | ✅ |
| Tuic | ❌ | ✅ | ✅ |
| Clash YAML 配置 | ❌ | ❌ | ✅（原生） |
| 订阅自动转换 | ❌（需手动配置JSON） | ❌ | ✅（sub-store等工具） |
| TLS 指纹多样性 | ✅（chrome/ios/safari） | ✅ | ✅（更多指纹选项） |

**使用策略**：当 xray 和 sing-box 都连不上时，mihomo 是值得一试的备选——不同的 TLS 握手实现和指纹选项有时能绕过风控。

## 管理脚本

参考 `/opt/data/proxy-skill/proxy.sh` — sing-box 启动/停止/验证一体化脚本：

```bash
bash /opt/data/proxy-skill/proxy.sh start    # 启动（含连通性自检）
bash /opt/data/proxy-skill/proxy.sh stop     # 停止
bash /opt/data/proxy-skill/proxy.sh restart  # 重启
bash /opt/data/proxy-skill/proxy.sh status   # 状态 + 出口 IP
bash /opt/data/proxy-skill/proxy.sh test     # 测 Google/javdb
bash /opt/data/proxy-skill/proxy.sh log      # 查看日志
```

## 全局代理环境变量

所有子智能体（delegate_task）和终端会话自动继承代理配置。配置文件：`/opt/data/home/.bashrc`

```bash
export http_proxy=socks5://127.0.0.1:10808
export https_proxy=socks5://127.0.0.1:10808
export HTTP_PROXY=socks5://127.0.0.1:10808
export HTTPS_PROXY=socks5://127.0.0.1:10808
export ALL_PROXY=socks5://127.0.0.1:10808
export NO_PROXY=localhost,127.0.0.1,.local,.internal,223.5.5.5,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16
```

## 当前可用配置（2026-07-18 验证）

**节点**: 🇺🇸美国圣何塞01 REALITY（直连 IP 134.195.101.129:443）
**配置文件**: `/opt/data/proxy-skill/reality_us01.json`
**出口**: 美国 Cloudflare IPv6 (`2602:feda:...`)
**验证**: Google HTTP 302, javdb HTTP 200 ✅

### 历史故障与解决

| 日期 | 出口 IP | 问题 | 解决 |
|:----|:----|:----|:----|
| 2026-07-15 | 123.123.74.33 | Cloudflare 对 VLESS WS 返回 403；UDP 全封 | 换 IP |
| 2026-07-18 | 111.193.27.155 | 同上，新 IP 也被封 | **用 REALITY 直连节点（不走 CF）** |

**关键教训**：当出口 IP 被 Cloudflare 封禁（VLESS WS 全 403）且 UDP 被封（hy2 全超时）时，**REALITY 协议走 TCP 443 直连 AWS/中华电信节点可以绕过**——因为 REALITY 不走 CF CDN，且用 TLS 伪装成访问 apple.com 等正常流量。

## 节点切换与故障转移

### 手动切换

当当前节点不可用时，从订阅中选另一个节点：

1. 拉取订阅 → base64 解码 → 提取 VLESS 链接列表
2. 用 Python 解析目标节点的参数（host/port/pbk/sid/sni）
3. 更新 `xray_config.json` 中的 outbounds[0]
4. 重启 xray（`bash start_xray.sh`）
5. 测试连通性

### 自动切换脚本

参考 `switch_node.sh` — 从订阅拉取 → 解析节点 → 选目标节点 → 生成配置 → 重启 xray → 测试。

**功能**：
```bash
# 随机选美国节点并切换
bash /opt/data/switch_node.sh

# 列出所有可用节点
bash /opt/data/switch_node.sh --list

# 按编号选节点
bash /opt/data/switch_node.sh --select 3
```

**注意**：自动切换脚本目前只能处理 VLESS 协议。Hysteria2 节点需用 sing-box。

## 验证

```bash
curl -s --socks5 127.0.0.1:10808 --connect-timeout 5 --max-time 10 https://www.google.com
# 应返回 HTTP 200

curl -s --socks5 127.0.0.1:10808 --connect-timeout 5 --max-time 10 https://httpbin.org/ip
# 应返回出口 IP（非本地 IP）
```

## 系统级代理配置（所有子进程/智能体自动使用）

当需要确保所有子智能体（delegate_task 创建的）都自动使用代理时，配置环境变量比每个子进程手动指定更可靠：

```bash
# 在 ~/.hermes/.env 或 ~/.bashrc 中添加：
export http_proxy=socks5://127.0.0.1:10808
export https_proxy=socks5://127.0.0.1:10808
export HTTP_PROXY=socks5://127.0.0.1:10808
export HTTPS_PROXY=socks5://127.0.0.1:10808
export ALL_PROXY=socks5://127.0.0.1:10808
export NO_PROXY=localhost,127.0.0.1,.local,.internal,223.5.5.5
```

**注意**：有些客户端（如curl）识别小写 `http_proxy`，有些识别大写 `HTTP_PROXY`。两个都设。SOCKS5代理格式为 `socks5://127.0.0.1:10808`，HTTP(S)代理也可以走 `http://127.0.0.1:10809`（HTTP inbound）。

**子智能体自动继承**：Hermes 的 `delegate_task` 启动的子进程继承当前 shell 的环境变量。如果在当前会话的 system prompt 中已导出代理变量，子智能体自动使用。

## 用户偏好

- 用户要求 **所有智能体都能用代理翻墙**，不要每个都单独配置。用系统级环境变量或SOCKS5统一代理。
- 用户偏好 **简洁直接**，不要频繁汇报进度，通知结果即可。
- 用户说「不要每个智能体都要折腾一遍」——一次配好全局生效。

### 关键诊断信号：手机上能通，服务器上全不通

**这是最核心的诊断信号。** 当你的手机/电脑上用同一订阅能正常翻墙，但服务器上所有节点都返回超时/403/Connection refused，说明：

1. **节点本身是好的**（手机上能通就是明证）
2. **不是配置问题**（同一份配置手机上能用）
3. **不是服务商问题**（全部71个节点不可能同时宕机）
4. **是服务器网络的 egress 限制**

#### 根因判断

| 现象集合 | 大概率根因 |
|:---------|:-----------|
| 所有 443 端口节点（VLESS+WS/REALITY）全超时；同配置手机能通 | 服务器出口 IP 被 Cloudflare/GFW 标记，**TCP 443 出境被干扰** |
| 所有 hy2 节点（UDP 非标端口）也超时 | UDP/QUIC 也被限制，**全协议阻断** |
| 只有 443 不通，非标端口能通 | **仅 443 端口被封**，可改用非标端口节点 |
| 某些节点返回 403/429 而非超时 | IP 被 Cloudflare 风控命中（非完全阻断，但不可用） |

#### 快速验证

```bash
# 验证 1: 出口 IP
curl -s --connect-timeout 5 http://httpbin.org/ip
# 如果很快返回国内 IP → 国内直连正常

# 验证 2: 境外 443 直连（不走代理）
curl -s -o /dev/null -w "HTTP %{http_code}\n" --connect-timeout 5 --max-time 10 https://www.google.com
# 如果超时/000 → 443 出境被干扰

# 验证 3: 境外非443端口直连
curl -s -o /dev/null -w "HTTP %{http_code}\n" --connect-timeout 5 --max-time 10 http://httpbin.org:80/ip
# 如果 80 端口能通但 443 不通 → 仅 TLS 443 被封

# 验证 4: 直连节点 TCP 端口
python3 -c "import socket; s=socket.create_connection(('unamecf.xn--ghqu5fm27b67w.com', 443), timeout=8); print('TCP OK:', s.getpeername()); s.close()"
# TCP 通但后续 TLS/WS 失败 → 协议层问题
# TCP 都超时 → 端口/IP 被直接封
```

#### 应对策略（按优先级排序）

1. **找非 443 端口的节点** — 检查订阅里有没有 `port=xxxx` 不是 443 的（如 35000、8443、10000-65535 随机端口）
2. **改用非 TLS 的协议** — Shadowsocks（端口随机）、Trojan（端口 443 但握手方式不同）、SSH tunnel
3. **通过中转服务器** — 在国内云服务商开一台有独立公网 IP 的小鸡（如阿里云香港/新加坡，但注意政策风险），在这台机器和代理节点之间搭隧道
4. **换出口 IP** — 这台机器的 IP 可能被标记了，换 NAT 出口（重启路由器/换宽带/用 4G 热点）可能恢复
5. **换订阅服务商** — 有些服务商提供非 443 端口或非 CF 线路的专线节点

#### 常见误区

- ❌ 反复测试同一批 443 节点期望有不同结果（服务器网络环境不变，结果不会变）
- ❌ 在三个不同代理客户端（xray/sing-box/mihomo）之间反复切换（问题不在客户端实现）
- ❌ 花大量时间微调 TLS 指纹/fingerprint/混淆参数（这些只影响握手阶段的协议指纹，对完全阻断的端口无效）
- ✅ 正确做法：**判断阻断层面（端口/协议/IP）→ 找该层面未被阻断的节点 → 不行就换网络出口**

#### 所有节点不可用时的诊断流程

当所有订阅节点都超时（curl 返回 000/超时）时，按以下顺序排查：

### 1. 检查基础连通性
```bash
# 检查本地端口是否在监听
ss -tlnp | grep 10808

# 检查 xray 是否存活
kill -0 $(cat /opt/data/xray.pid) && echo "running" || echo "dead"

# 检查是否能解析目标域名
ping -c 1 -W 3 www.javdb.com
```

### 2. 检查 xray 自身日志
```bash
tail -20 /opt/data/xray_error.log
tail -20 /opt/data/xray_access.log  # 看有没有新连接记录
```

### 3. 区分是「配置错误」还是「节点宕机」

观察 xray stdout 日志：
- `Warning: core: Xray ... started` — 启动正常
- 无 error log 但 curl 000 — **远端节点问题**（IP被封、节点宕机、端口阻断）
- `Failed to build REALITY config. > empty "password"` — **配置错误**（缺 pbk）

### WebSocket/CDN 节点诊断（Cloudflare 403/429/503）\n\nWS 节点走 Cloudflare CDN（域名如 `unamecf.xn--*`、`unamecf2.xn--*`、`downloadcfpro.xn--*`）时可能被CF盾拦截。\n\n#### 分层直连测试（Python，不走代理）\n\n```python\nimport socket, ssl\n# Layer 1: TCP\ns = socket.create_connection(('unamecf2.xn--ghqu5fm27b67w.com', 443), timeout=8)\nprint(f'TCP: {s.getpeername()}')\n# Layer 2: TLS  (用 VLESS 链接中的 sni 参数作为 server_hostname)\nctx = ssl.create_default_context()\nctx.check_hostname = False\nctx.verify_mode = ssl.CERT_NONE\nss = ctx.wrap_socket(s, server_hostname='usa1s.xn--ghqu5fm27b67w.com')\nprint(f'TLS: {ss.cipher()[0]}')\n# Layer 3: WebSocket upgrade (raw HTTP GET + Upgrade)\nimport base64\nws_key = 'dGhlIHNhbXBsZSBub25jZQ=='\npath = '/pq/us1'  # 从 VLESS 链接的 path 参数\nsni = 'usa1s.xn--ghqu5fm27b67w.com'  # 从 VLESS 链接的 host/sni 参数\nreq = (\n    f'GET {path} HTTP/1.1\\r\\n'\n    f'Host: {sni}\\r\\n'\n    'Upgrade: websocket\\r\\n'\n    'Connection: Upgrade\\r\\n'\n    f'Sec-WebSocket-Key: {ws_key}\\r\\n'\n    'Sec-WebSocket-Version: 13\\r\\n'\n    '\\r\\n'\n)\nss.sendall(req.encode())\nresp = ss.recv(4096)\nprint(f'WS response: {resp.decode(errors=\"replace\")[:200]}')\nss.close()\n```\n\n#### WS 响应码解读\n\n| 响应 | 含义 | 应对 |\n|------|------|------|\n| `101 Switching Protocols` | WS 握手成功，节点存活 | VLESS 配置问题，检查 uuid/flow/fingerprint |\n| `403 Forbidden` | **Cloudflare IP 封禁** | 需非CF节点或换出口IP |\n| `429 Too Many Requests` | CF 限流 | 换不同路径的节点，等冷却 |\n| `503 Service Unavailable` | CF 临时屏蔽 | 换节点或等冷却 |\n| `ws closed: 1000 (normal)` | WS连接成功但服务器主动关闭 | VLESS 验证失败，检查 uuid/fingerprint/flow |\n| 超时（TLS OK但无响应） | 节点过载或路径错误 | 检查 path 参数 |\n\n#### 所有节点不可用的根因判断\n\n| 现象 | 可能原因 | 对策 |\n|------|---------|------|\n| 所有 WS 节点 → 403/429/503 | CF 封了出口 IP | 用非CF节点（直连IP或hy2） |\n| 所有 Reality 节点 → 超时 | GFW 封端口/IP | 换协议（WS/hy2） |\n| 非CF节点（AWS等）→ TLS reset | IP被目标重置 | 换不同地域的节点 |\n| hy2 节点 → 超时 | UDP/QUIC 被限或节点带宽满 | 试不同 hy2 端口、切换协议 |\n\n---\n\n#### xray error.log 常见错误解读

| error.log 内容 | 含义 | 应对 |
|:--------------|:----|:-----|
| `websocket: failed to dial to (wss://...): 429 Too Many Requests` | 节点限流，同一IP请求过多 | 换不同路径/域名的节点，等几分钟冷却 |
| `websocket: failed to dial to (wss://...): 503 Service Unavailable` | 节点临时不可用/被拉黑 | 换节点，不要继续重试同一节点 |
| `failed to decode response header > websocket: close 1000 (normal)` | WebSocket握手成功但VLESS协议层拒绝 | 检查 fingerprint 参数是否与原始链接一致（ios vs safari），以及 path 是否正确 |
| `tunneling request to tcp:X.X.X.X:443 via HOST:443` + 后续无报错但curl超时 | 隧道已建立但远端响应慢或连不上目标站 | 直连测试节点本身，确认节点存活 |
| `Connection reset by peer` | 服务端主动断开 | 节点可能宕机或IP被封，换节点 |
| `failed to find an available destination > common/retry: all retry attempts failed` | 所有重试均失败，xray放弃连接 | 检查网络、节点连通性、配置参数 |

### 4. 尝试不同协议的节点

当 VLESS+REALITY 节点全挂时，尝试订阅里 WebSocket + TLS 节点：

| 协议 | 适用场景 | 关键参数 |
|:----|:---------|:---------|
| REALITY (tcp) | 抗检测强 | `pbk` + `sid` + `flow=xtls-rprx-vision` |
| WebSocket + TLS | 可过 CDN | `host` + `path`，`security=tls` |
| Hysteria2 | QUIC，抗丢包 | 需 sing-box（xray 不支持） |

⚠️ **不要在一个订阅的所有节点都超时后就认定全部宕机** — 某些节点只是响应慢（10s+）。中国网络环境下偶尔的超时可能只是临时丢包，重试一次再判断。

### 5. 换订阅

如果订阅中所有节点全挂超过 24 小时，联系服务商获取新链接。

## Pitfalls

- **🚨 REALITY pbk 参数长度必须是 43 字符**（2026-07-18 发现）：base64url 编码的 32 字节 x25519 公钥 = 43 字符（无 padding）。从订阅复制时**极易多复制一个字符**（如末尾的 `e` 实际是 base64 padding 被误当字符），导致 sing-box 报 `invalid public_key`、xray 报 `empty "password"`。验证方法：
  ```python
  import base64
  k = base64.urlsafe_b64decode(pbk + '=' * (4 - len(pbk) % 4) if len(pbk) % 4 else pbk)
  assert len(k) == 32, f"应为32字节，实际{len(k)}字节，pbk长度{len(pbk)}（应为43）"
  ```
  如果解码出 33 字节，说明多复制了字符——截取前 43 字符即可。详见 `references/2026-07-18-singbox-reality-success.md`。

- **🚨 sing-box REALITY 节点必须用直连 IP，不能用域名**（2026-07-18 发现）：sing-box 的 DNS 解析在 outbound 初始化阶段可能失败，报 `name error`（即使域名能 ping 通）。**解决**：从订阅里找该节点对应的直连 IP（如 `134.195.101.129` 而非 `pq.aws48.yydnjc.top`）。订阅里同时有域名版和 IP 版节点，优先用 IP 版。同时配置块需加 `dns.servers` 段（local + google，`rules: [{outbound: any, server: local}]`）。

- **Cloudflare `cf-mitigated: challenge` 是 CF 封锁的 definitive 信号**（2026-07-18 确认）：当 VLESS WS 节点返回 HTTP 403 时，检查响应头。若有 `cf-mitigated: challenge` 和 `server-timing: chlray;desc="..."`，说明是 Cloudflare 主动触发人机验证挑战（基于 IP 段风控），**不是配置错误**。换 IP 不一定解决（新 IP 可能仍触发同样 challenge）。**正确做法**：换用 REALITY 协议（直连 AWS 节点，不走 CF CDN），而非继续尝试 WS 节点或反复换 IP。

- **🚨 节点测试脚本会写坏现有配置**：Python 批量测试脚本遍历节点时逐个覆盖 `xray_config.json`。如果最后一个被测试节点的 SNI/publicKey/shortId 与最终保存的 IP 不匹配，配置就损坏了。

  **症状**：xray 正常启动、端口打开、连接被 accepted，但 curl 报 `Connection reset by peer` / `TLS connect error`。xray 不报任何错误（config 语法合法，只是 reality 握手参数不匹配）。

  **修复**：不要依赖被覆盖过的 config 文件。回退到从订阅链接重新解析该节点的 VLESS 链接，逐个参数对照：`sni`、`pbk`、`sid`、`address` 必须全部匹配原始 VLESS 链接。例：N57（圣何塞02，134.195.101.137）的正确参数为 `sni=updates.cdn-apple.com`、`pbk=AzQlCUikY30iQK5pgK2nW_AiYJkvi2Lm5rDjWGHvzUo`、`sid=182dc224`。

  **预防**：测试脚本在开始时备份 `xray_config.json`，结束后恢复。或使用独立的临时配置文件测试，不覆盖生产 config。

- **Reality 配置缺少 pbk/sid 会直接启动失败**：错误信息 `Failed to build REALITY config. > empty "password"`。必须从 VLESS 链接的 `pbk` 和 `sid` 参数提取。
- **curl 输出截断**：VLESS 链接长度 300-500 chars，使用 `re.findall` 正则提取完整链接，不要手工截取。
- **端口冲突**：前一个 xray 进程未完全退出时，新进程绑定 10808 会失败。每次测试先 `pkill -f xray` 并 `sleep 1`。
- **子进程启动等待**：xray 需要约 2s 初始化。测试前必须 `time.sleep(2)`，否则会返回 000。
- **Gateway 内重启限制**：`hermes gateway restart` 在 gateway 进程中执行会拒绝（防止死循环）。需从独立终端执行或让用户手动重启。
- **节点 IP 被封**：目标站（如 javdb）会封禁已知代理 IP 段。同一节点的不同子节点（圣何塞01-08）可能部分被封、部分可用，需全部测试。
- **🚨 WebSocket 节点高频测试触发限流**：同一 IP 在短时间内对同一 WS 节点多次测试（如批量脚本或调试重试），会导致节点返回 `429 Too Many Requests` 甚至 `503 Service Unavailable`。症状：初次直连 TCP+TLS 正常，但 xray 出站 WS 握手后收到 HTTP 429/503。**解决**：换同域名不同路径的节点（如 /pq/jp1 → /pq/jp2），或换完全不同的节点，等待几分钟冷却。**预防**：批量测试时每个节点只测 1 次，不要反复重试。
- **⚠️ WS 节点的 fingerprint 必须匹配原始 VLESS 链接**：同一订阅下不同 WS 节点可能使用不同指纹（如 `ios` vs `safari`）。`fingerprint` 不匹配会导致 WebSocket 握手成功后 VLESS 协议层报 `close 1000 (normal)` / `failed to decode response header`。务必从原始 VLESS 链接的 `fp` 参数提取指纹。
- **⚠️ xray 26.3.27 标记 WebSocket 为 deprecated**：启动时打印 `The feature WebSocket transport is deprecated, not recommended for using and might be removed`。这不是错误，仍可正常使用，但应关注 xray 后续版本是否移除 WS 支持。`headers: { Host: ... }` 也被标记为即将移除，建议迁移到独立 `host` 参数。
- **pkill -f xray 自杀问题**：在 terminal() 中执行 `pkill -f xray` 会连带杀掉自己的进程（因为它也匹配了 xray）。解决：先 `pkill -f "xray" 2>/dev/null; sleep 2` 确保旧进程退出，再在新 terminal() 中启动。

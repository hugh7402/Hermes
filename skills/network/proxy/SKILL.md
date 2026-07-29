---
name: proxy
description: 统一代理/翻墙 skill。管理 sing-box 代理服务（启动/停止/切换节点/故障排查），整合 xray/sing-box/mihomo 多种方案。所有需要翻墙的应用、skill、cron 统一通过此 skill 调用，自动触发。
tags: [proxy, vpn, network, sing-box, xray, mihomo, vless, reality, 翻墙]
trigger: 任何 skill/cron/service 需要访问境外资源时，自动加载本 skill。用户说"翻墙""代理""上不去""403""被墙""连不上github"时触发。
---

# proxy — 统一代理翻墙 skill

## 架构

```
proxy skill (Hermes 接口层)
│  SKILL.md — 使用说明 + 故障排查
│
├── 基础设施层（/opt/data/proxy-skill/）
│   ├── proxy.sh         → 启动/停止/状态/测速
│   ├── sing-box          → 代理核心
│   ├── reality_us01.json → 当前活动配置
│   ├── hy2_sg.json       → 备用 hysteria2 配置
│   ├── vless_ws.json     → 备用 WS 配置
│   └── reality_aws01.json→ 备用 AWS 配置
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
```

## 其他 skill 如何调用本代理

### 方式 1：声明依赖（推荐）
在其他 skill 的 frontmatter 加：
```yaml
requires-skills: [proxy]
```

本 skill 加载后，以下内容自动生效：
- 代理环境变量（http_proxy/https_proxy/ALL_PROXY → socks5://127.0.0.1:10808）
- 代理未运行时自动尝试启动
- 出口 IP 验证

### 方式 2：直接调用
```bash
bash /opt/data/proxy-skill/proxy.sh start
```

## 当前活动节点（2026-07-18 验证）

| 参数 | 值 |
|------|-----|
| 协议 | REALITY |
| IP | 134.195.101.129:443 |
| 出口 | 美国 Cloudflare IPv6 |
| 配置 | `/opt/data/proxy-skill/reality_us01.json` |
| 启动命令 | `bash /opt/data/proxy-skill/proxy.sh start` |

## 节点切换

当当前节点不可用时（出口被封/超时），从订阅拉取新节点：

1. 拉取订阅 → base64 解码 → 提取 VLESS 链接列表
2. Python 解析目标节点参数（host/port/pbk/sid/sni）
3. 生成新 JSON 配置写入 `/opt/data/proxy-skill/`
4. 重启代理：`bash /opt/data/proxy-skill/proxy.sh restart`
5. 验证：`bash /opt/data/proxy-skill/proxy.sh test`

订阅地址在 /opt/data/proxy-skill/ 中管理。

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

## 故障排查

### 所有节点全超时
```bash
# 1. 检查代理是否运行
bash /opt/data/proxy-skill/proxy.sh status

# 2. 检查本地端口
ss -tlnp | grep 10808

# 3. 检查日志
bash /opt/data/proxy-skill/proxy.sh log | tail -20

# 4. 直连测试节点
python3 -c "import socket; s=socket.create_connection(('134.195.101.129',443),timeout=8); print('TCP OK:',s.getpeername()); s.close()"

# 5. 确认出口 IP 未被封
curl -s --connect-timeout 5 http://httpbin.org/ip
```

### Cloudflare 403/503
REALITY 节点不走 CF，如果 REALITY 也不通，换其他协议配置：
```bash
# 停止当前代理
bash /opt/data/proxy-skill/proxy.sh stop

# 切换不同协议的配置
# 编辑 config 指向备用节点 → restart
bash /opt/data/proxy-skill/proxy.sh restart
```

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

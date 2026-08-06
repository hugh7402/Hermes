# 代理自动切换实现记录（2026-08-04）

## 背景

javdb 封了 us01 节点出口 IP（134.195.101.193，返回 "The owner of this website has banned your access based on your browser's behaving"，3-7日解除）。用户提供订阅地址，要求：IP 被封/节点失效时自动换节点，不换订阅源。

## 订阅信息

- 地址：`https://dasho.xn--cp3a08l.com/api/v1/pq/<token>`（存于 subscription.conf）
- 返回：base64 编码的 71 个 VLESS/Hysteria2 链接
- 用户常用节点：us05

## 节点解析要点

订阅每行格式：
```
vless://uuid@server:port?params#节点名
```

params 关键参数：
- `security=reality` → REALITY 协议（需要 pbk/sid/fp）
- `security=tls` → 普通 TLS
- `type=ws` → WebSocket transport（有 path/host）
- `flow=xtls-rprx-vision` → REALITY 的 flow

## 节点命名（71 个节点中的圣何塞组）

有两组"圣何塞"节点：
1. **"三网推荐"组（IP 直连 134.195.101.x）** — REALITY 协议，✅ 可用
2. **"0.1倍"组（域名 unamecf2.xn--ghqu5fm27b67w.com）** — TLS 协议，❌ 实测不可用

**规则：必须选"三网推荐"组。** 判断时用完整节点名（`'三网推荐' in full_name`），不能只用 `split('|')[0]` 截断后的名字。

## 踩坑记录

### 1. REALITY ≠ TLS
- 症状：所有节点测试超时（000），sing-box 日志报 `bad HTTP protocol version`
- 原因：把 security=reality 的节点按普通 TLS 配置（`"tls": {"enabled": true}`）
- 修复：正确配置：
```json
"tls": {
  "enabled": true,
  "server_name": "www.mi.com",
  "reality": {
    "enabled": true,
    "public_key": "<pbk>",
    "short_id": "<sid>"
  },
  "utls": {"enabled": true, "fingerprint": "ios"}
}
```

### 2. usXX 映射歧义
- 症状：`--node us05` 匹配到错误的节点（域名版而非 IP 版）
- 原因：两个"圣何塞05"，us_map 被覆盖
- 修复：优先映射含"三网推荐"的节点，且用完整名字判断

### 3. sid URL 编码
- 症状：生成的配置 `short_id` 带 `#%F0%9F%87%BA...`（URL 编码的节点名）
- 原因：订阅里 sid 参数值 = `2546d239#🇺🇸美国圣何塞05 | 三网推荐`（URL 编码），split('#') 前必须 unquote
- 修复：`urllib.parse.unquote(params.get('sid','')).split('#')[0]`

### 4. base64 订阅行号
- 症状：`sed -n "68p"` 取到空行
- 原因：/tmp/sub_raw.txt 是 base64 编码（一整行），sed 按物理行取
- 修复：先解码到 /tmp/sub_decoded.txt，sed 从那里取；python 0-indexed → sed `$((idx+1))`

### 5. test_node 端口冲突
- 症状：测试实例与正式代理端口冲突
- 修复：随机端口 `21900 + RANDOM % 50`，测试完 kill + 清理

## 验证命令

```bash
# 指定节点切换
bash /opt/data/proxy-skill/proxy_auto_switch.sh --node us05

# 全节点遍历（自动找可用）
bash /opt/data/proxy-skill/proxy_auto_switch.sh

# 验证 javdb 连通
curl -s --max-time 15 --proxy http://127.0.0.1:10808 -A "Mozilla/5.0" \
  -c /tmp/jdb_cookies.txt "https://javdb.com/over18?respond=1" -w "%{http_code}\n"
# 302 = 正常（over18 重定向）

# 验证出口 IP
bash /opt/data/proxy-skill/proxy.sh status
```

## 结果

- 当前活动节点：us05（134.195.101.122 → 出口 134.195.101.120）
- javdb 访问恢复正常（over18 302，搜索 200）
- ZOZO-077 下载链路全程正常

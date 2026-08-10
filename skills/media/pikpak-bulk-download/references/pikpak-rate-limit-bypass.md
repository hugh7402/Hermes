# PikPak 限速排查与绕过实测（2026-08-10）

## 症状

AI短剧 1248 文件/242GB 全量下载：直连 aria2（8 连接分片）所有文件 0.02-0.09MB/s，
SLOW 换 URL 无效，重排队空转。多 CDN 节点（dl-a10b-1551/1555/1194/0869）全慢
→ 排除单节点问题。真实原因：**服务器出口 IP 被 PikPak 限流**。

## 排查步骤（可复现）

```bash
# 1. 直连测速（下载 10-20MB 看 speed_download）
curl -s -o /dev/null -w "%{speed_download}" -r 0-20971520 --max-time 25 "$URL"

# 2. 走代理测速（对比出口 IP 差异）
curl -s -o /dev/null -w "%{speed_download}" -x http://127.0.0.1:10808 -r 0-20971520 --max-time 25 "$URL"

# 3. 查出口 IP
curl -s --max-time 10 -x http://127.0.0.1:10808 https://api.ip.sb/ip
curl -s --max-time 10 https://api.ip.sb/ip
```

URL 获取：`PikPakApi.get_download_url(fid)` → `info['web_content_link']`。

## 出口 IP 速度矩阵（同一文件，20MB 测速）

| 出口 IP | 节点 | 速度 |
|---------|------|------|
| 111.193.27.155 | 服务器直连 | 0.05-0.09 MB/s ❌ |
| 134.195.101.120 | us05 圣何塞 | 0.26-0.28 MB/s |
| 134.195.101.193/194/195 | us01-03 | 0.25-0.34 MB/s |
| 103.62.49.138 | AWS 日本01/05/06/08 | 0.9-2.2 MB/s（快，但周期性断流）|
| 103.62.49.178 | AWS 日本04/07 | 0.91-0.95 MB/s |

峰值记录：103.62.49.138 曾到 8.7MB/s（短暂高峰窗口），稳定值约 0.9-2.2MB/s。

## 结论

- **PikPak 按出口 IP 限流**，换 IP 可绕过（10 倍+提速），不是 CDN 全局限流。
- 同一节点配置可能映射不同出口 IP（us04/us05 → 103.62.49.138），**以测速为准**。
- AWS 日本段（103.62.49.x）对本任务最快；圣何塞段（134.195.101.x）慢。
- 出口 IP 周期性断流：快几分钟 → 0 速度十几分钟 → 恢复。SLOW 检测 + FAIL 重排队会自动应对，无需人工干预。

## 关键命令

```bash
# 测速脚本（>1MB/s 才输出，供 no_agent cron 空输出=静默）
/opt/data/scripts/ai_cdn_speed_test.sh

# 换节点（指定节点，避免无参数全遍历卡死）
bash /opt/data/proxy-skill/proxy_auto_switch.sh --node us05
# auto_switch 无参数遍历会卡在死节点（新加坡01 挂起 300s+），必须外层加超时

# aria2 走代理
aria2c --all-proxy=http://127.0.0.1:10808 ...

# 代理状态/出口 IP
bash /opt/data/proxy-skill/proxy.sh status
```

## 代理注意事项

- 代理按流量计费：**先直连省钱，限速了才切代理**（用户明确偏好）。
- 用户确认策略：直连试 → 不行切代理 → 代理出口被限再换节点。
- 换节点后 aria2 无需重启（每次新 URL 都走当前代理），但 SLOW 检测阈值需适配代理速度（0.2MB/s）。

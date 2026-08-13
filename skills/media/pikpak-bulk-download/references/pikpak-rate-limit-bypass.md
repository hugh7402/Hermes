# PikPak 限速排查与绕过实测（2026-08-10，2026-08-12 补充）

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
| **67.159.48.147** | **SG-AWS02（🇸🇬AWS新加坡02）** | **25-30MB/s 稳定（最快）** |

峰值记录：103.62.49.138 曾到 8.7MB/s（短暂高峰窗口），稳定值约 0.9-2.2MB/s。

## 2026-08-12 补充：限流是 IP 总量级（WebDAV/并发救不了）

出口 111.193.27.155（联通家宽）持续被限多日，实测同一出口 IP 下所有通道：

| 通道 | 速度 | 说明 |
|------|------|------|
| CDN 直连 | 0.07-0.16 MB/s | 连续 3 次稳定，非抖动 |
| WebDAV 单线程 (rclone copy) | 0.17 MB/s | dav.mypikpak.com 阈值略高 |
| WebDAV 单文件 8 线程 | 0.24 MB/s | `--multi-thread-streams=8` |
| WebDAV 多文件并发 | 0.35 MB/s | `--transfers=8` |
| 代理 SG-AWS02 | 2.6-30 MB/s | 干净 IP |

**结论**：PikPak 按出口 IP 掐**总带宽**，连接数/线程数/通道全无效。判断直连是否恢复
只测 CDN 直连即可（0.07 是稳定限流值，不是瞬时抖动）。

## 已排除的免费换 IP 方案（2026-08-12，勿再试）

- **CF Workers 中转**：`*.workers.dev` 国内被墙（直连 HTTP 000 15s 超时）；
  cloudflare.com 边缘节点直连却通（200/301 600ms）→ 需自有自定义域名才能用，用户没有。
- **公共免费 HTTP 代理**（阿里云新加坡 8.219.68.44、阿里云香港 47.91.104.15、
  Azure 新加坡 20.205.61.143）：测 PikPak 直链全 0.00MB/s，不可用。

## 根治方案

1. **重启光猫/路由器重拨换 IP**（PPPoE 必换 IP）→ 新 IP 干净、限流解除。唯一免费根治。
2. 等临时 IP 处罚自动解除（几小时~几天）→ 靠测速 cron（00:30/06:30，>1MB/s 才提醒）盯。
3. 小文件/不着急：WebDAV 0.3MB/s 挂着免费下。
4. 大文件/批量：代理 SG-AWS02（25-30MB/s，按流量收费）——用户 2026-08-12 决定
   "最近走代理下载，等回家重启路由换 IP"。

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

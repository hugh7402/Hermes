# PikPak 完整接入记录

## 连接信息

- **URL**: http://dav.mypikpak.com:80
- **用户名**: xqji
- **密码**: rtabnsvs
- **rclone remote name**: pikpak
- **工具脚本**: /opt/data/pikpak.sh

## 服务端口（当前配置）

| 服务 | 端口 | 说明 |
|------|------|------|
| WebDAV API | **23456** | rclone serve webdav（原 8080，防火墙拦截后改） |
| Web UI | **23457** | Python http.server + index.html（原 8081，防火墙拦截后改） |

> ⚠️ 改端口后必须同步更新两处：`pikpak.sh` 中的启动命令 + `index.html` 中的 `BASE` JS 变量。

## SSH 隧道（外网访问）

```bash
ssh -L 23457:localhost:23457 -L 23456:localhost:23456 你的服务器IP
```

然后浏览器打开 http://localhost:23457

## Docker 网络模式检测

容器实际可能不是 host 模式，即使 docker-compose.yml 写的是 `network_mode: host`。

**从容器内检测方法**：
```bash
# 看 MAC 地址
cat /sys/class/net/eth0/address
# 02:42:xx:xx:xx:xx → Docker bridge 网络
# 真实 MAC → host 网络

# 看 hosts
cat /etc/hosts | grep $(hostname)
# 172.x.x.x → bridge
# 192.168.x.x → host
```

如果是 bridge 网络，需在 docker-compose.yml 加 ports 映射才能局域网访问。

## Web UI 密码

FileBrowser（如果需要切换回来）：admin / pikpak2026!!

## PikPak 目录结构

```
/
├── 20240610-目录-Backup
├── Inbox-JAV
├── Movie
├── My Pack
├── My Pornhub
├── My Telegram
├── My Twitter
├── Pack From Shared
├── Pic-CosPlay
├── Pic-nsfw
├── Pic-日韩美女
└── 视频分类
```

## Docker/容器自动启动

如果容器重启，需要手动执行：
```bash
bash /opt/data/pikpak.sh start
```

可以加 cron 实现开机自启（如果容器支持），或手动重启。

## 已知问题

- **列表慢**: PikPak 境外服务器延迟高，首次列表可能 15-30s。设置 `--dir-cache-time 300s` 后第二次就快了。
- **不支持挂载**: 容器无 FUSE，只能 serve webdav 代理访问
- **大文件下载**: rclone 支持多线程下载大文件
- **端口被防火墙拦**: 改成非标端口（如 23456/23457），但必须同步更新两处（脚本 + 前端 HTML）

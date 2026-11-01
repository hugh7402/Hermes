# WebDAV 直连下载 — 2026-08-15 实测实录

## 背景

用户重启路由换 IP（111.193.27.155 → 123.123.74.83）后，测 PikPak 下载通道。发现 **WebDAV 直连（dav.mypikpak.com）稳定 5-7 MB/s 且 0 流量费**，成为批量下载省钱首选。

## 实测数据

| 通道 | 速度 | 说明 |
|:----|:----|:----|
| WebDAV 直连（rclone copy） | 4.8 → 6.8 MB/s（15s/30s 采样，持续不降速） | 0 流量费 |
| aria2 CDN 直连 | 间歇 0.25MB/s（z01a 全限）→ 167MB/s（a10b 短暂解封） | 节点分配看运气 |
| 代理 SG-AWS02（67.159.48.147） | 9-52 MB/s | 按流量收费 |
| 代理 us03（134.195.101.195） | 0.24 MB/s | 美国节点也被 PikPak 限速 |

## 关键结论

1. **换 IP 后 CDN 部分节点解封**（dl-a10b-* 组 4/28 文件 1.9-2.2MB/s，dl-z01a-* 全限 0.25MB/s）。解封是**节点级**不是全量，aria2 多连接并行时快节点能拉高总吞吐。
2. **WebDAV 直连是最稳定免费的通道**：换 IP 前后都 5-7MB/s，不依赖 CDN 节点分配。
3. 代理 us03 也会被 PikPak 限速（0.24MB/s）——**代理节点不是都有用**，只有 SG-AWS02 快。

## 坑：WebDAV 不支持 Range 请求（curl 测速 0 的真相）

```bash
# ❌ 错误测速：返回 HTTP 200 但 size=0（服务器忽略 Range 头返回空）
curl -u "user:pass" -H "Range: bytes=0-20971520" "http://dav.mypikpak.com/dav/xxx.mp4"

# ✅ 正确：rclone copy 全量流式下载，跑 15-30s 后 stat 落盘字节算速度
```

## 坑：rclone copy "directory not found"

- 远程路径解析：`rclone copy pikpak:目录/文件` 把路径当目录 → 先 `rclone lsf pikpak:` 确认实际路径（文件可能在子文件夹内）
- 本地目标目录必须先 `mkdir -p`，否则同样报 directory not found

## rclone 配置要点

- 配置文件：`/opt/data/.config/rclone/rclone.conf`
- 密码解密：`/tmp/rclone reveal "<encrypted_pass>"`（从 conf 直接读，`config show` 会遮罩）
- 当前密码（2026-08-15）：`rtabnsvs`（用户 xqji，URL http://dav.mypikpak.com:80）

## 批量下载脚本增强（network_video_dl.py 模式）

本会话 28 文件/48GB 下载验证的 asyncio 模式：
- 直连失败 2 次自动切代理（`use_proxy=True` 时 aria2 加 `--all-proxy`）
- 但**更好的默认**：WebDAV rclone copy 优先，代理最后
- 完成验证：`stat -c %b 文件 × 512` 看实际占用（区分 aria2 fallocate 预分配假象），`ffprobe` 校验时长
- 下载完成后删 PikPak 源文件（用户 2026-08-15 规则）：`delete_to_trash(ids)` 分批 20 个，再删空文件夹

## 注意

- 2026-06 旧数据（WebDAV 1.4MB/s→50KB/s + 503）已过时，以本次为准
- 超大文件长时间传输若 WebDAV 降速，暂停 10 分钟恢复（旧经验，未复现但保留）

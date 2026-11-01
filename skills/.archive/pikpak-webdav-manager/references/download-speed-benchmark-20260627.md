# PikPak 下载速度评测 (2026-06-27)

本服务器 (Linux 5.19.17-z4pro-generic) 测试的各方案速度对比。

## 环境

- 服务器：某 IDC 机房，位于中国
- PikPak WebDAV：`dav.mypikpak.com:80`（直连）
- PikPak CDN：`dl-z01a-*.mypikpak.com`（直连）
- Xray 代理：N57 美国圣何塞 02 节点
- 网络限制：服务器到 PikPak 的海外出口被限速

## 各方案速度

| 方案 | 速度 | ETA(5GB) | 稳定性 | 备注 |
|:----|:---:|:--------:|:------|:------|
| 🥇 **aria2 8连接分片** | **5.6~13 MB/s** | **~8-15min** | ✅ 稳定，原生重试 | **推荐方案** |
| 🥈 CDN Python 8线程 Range | 0.3~1.5 MB/s | ~1h | ⚠️ 进程易被SIGTERM | 低于预期，用 aria2 |
| 🥉 rclone copy WebDAV | 1.4MB→50KB/s | ~28h | ❌ 降速+503 | 初快后慢 |
| rclone copyurl CDN | 200-250KB/s | ~6h | ✅ 稳定但慢 | 备选 |
| ❌ Python urllib CDN | 0.2 MB/s | ~7h | ✅ 稳定 | 单线程太慢 |
| ❌ 走 SOCKS5 代理 | ~0.3 KB/s | 数月 | ❌ 极差 | 代理按流量收费 |
| ❌ 多线程 rclone cat | 并发被限 | ∞ | ❌ WebDAV 限流 | 不可用 |

## 关键发现

### WebDAV 行为
- 初始速度 1-1.4 MB/s，约 5 分钟后开始降速
- 逐步降至 50-70 KB/s（约原始速度的 5%）
- 长时间传输触发 503 Service Unavailable
- 等待 5-10 分钟后恢复，但再次重复降速周期
- 多线程并发（rclone cat --offset --count）所有额外连接都被限流

### CDN 行为
- 单线程 0.2 MB/s 稳定（受限于服务器到 CDN 的路由）
- **支持 Range 请求**（206 Partial Content），可多线程分片
- 并发 Range 每线程 ~0.2 MB/s，8 线程合计 ~0.3~1.5 MB/s
- **aria2 8 连接分片可达 5.6~13 MB/s**（比 Python 多线程快 ~4-18 倍）
  - 单文件 8 连接：5~8 MB/s 稳定（峰值 13 MB/s 收尾）
  - 3 文件各 8 连接并行：每文件 ~2-5 MB/s，合计 ~10-13 MB/s 总带宽
- 不会触发 503，速度不降
- 直链有效期约 24 小时
- 不同 CDN 节点（dl-z01a-0041 ~ 0049）速度相近，无显著差异

### aria2 速度波形

单文件 8 连接分片下载的典型速度曲线：
- 起始：2~3 MB/s（TCP 慢启动）
- 加速期：逐渐升至 5~8 MB/s
- 维持期：5~8 MB/s 稳定
- 收尾（99%+）：降至 1~3 MB/s（仅 1-2 连接收尾）
- ⚠️ 中间检查 ffprobe 必然报 moov atom not found（元数据在文件末尾）

### Python 下载器问题
- `pikpak_cdn_dl.py`（Python urllib 多线程）经常被 **SIGTERM（exit code 143）** 杀死
- 从进程输出看，下载到一半突然退出，无错误日志
- 疑似 Python GIL + 多线程 + 大量 socket 操作触发系统 OOM killer 或 watchdog 超时
- 解决：**换 aria2**（C 二进制，单进程轻量，25MB RSS，无 GIL 问题）

### 代理
- 走代理下载 PikPak 速度极慢 (~0.3 KB/s)
- 代理按流量收费，**禁止用于下载**
- 代理仅用于 javdb/subtitlecat 等被墙网站的访问

## 2026-06-27 实测数据汇总

| 文件 | 大小 | 方法 | 速度 | 耗时 |
|:----|:---:|:----|:---:|:----:|
| MIDA-646 (首轮) | 5.98GB | aria2 8连接 | 5.6 MB/s | ~18min |
| MIDA-646 (次轮) | 5.98GB | aria2 8连接 | 4.7 MB/s (峰值5.5) | ~20min |
| MFYD-144 | 7.55GB | aria2 8连接 | **12 MB/s** | ~10min ⚡ |
| CAWD-992 | 5.1GB | aria2 8连接 | ~15 MB/s (估计值) | ~30s 🔥 |
| SNOS-227 | 5.2GB | aria2 8连接 | ~15 MB/s (估计值) | ~30s 🔥 |

说明 aria2 速度在 4~12 MB/s 范围浮动，受 CDN 当前负载影响。最佳实测 12~13 MB/s。

## 推荐策略

1. 先用 `pikpakapi` 获取 CDN 直链，保存到 `/tmp/pikpak_urls.json`
2. **首选 aria2 下载**，8 连接分片
3. 下载到临时目录 `/tmp/dl/` 避免与目标目录的 inode 冲突
4. 完成后 ffprobe 校验，再 mv 到最终目录
5. 如果 CDN 直链过期，降级到 `pikpak_cdn_dl.py` Python 多线程（0.3~1.5 MB/s）或 rclone copy WebDAV

## PC 端对比

用户使用 Neat Download Manager 从 PC 下载同样文件可达 5 MB/s（快 10 倍），说明：
- PikPak 对服务器 IP 做了更严格的限流
- PC 的宽带出口和 CDN 路由更优
- 大文件建议从 PC 下载

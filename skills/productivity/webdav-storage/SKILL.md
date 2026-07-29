---
name: webdav-storage
description: "Mount and manage WebDAV cloud storage on headless servers without FUSE/sudo. rclone setup, local web UI file browser, Python programmatic access, sync automation. Covers PikPak, NextCloud, ownCloud, and any WebDAV-compatible storage."
version: 1.0.0
author: Emma
created_by: agent
metadata:
  hermes:
    tags: [webdav, cloud-storage, rclone, pikpak, file-manager, storage-mount]
    category: productivity
---

# WebDAV 云存储集成

在无 root / 无 FUSE 的头服上（NAS、容器、VPS）挂载和管理 WebDAV 云存储。本 skill 以 PikPak 为例，但适用于任何 WebDAV 兼容存储。

## 适用场景

- 你的 NAS/Docker/VPS 没有 root 权限，无法安装 FUSE 或 mount
- 你需要从 WebDAV 云盘下载/上传文件
- 你想要一个网页端的文件管理器来操作云盘
- 你希望 Python 脚本能直接从云盘读取文件（文档入库、备份等）

## 前提条件

- `curl` 可用（大多数系统自带）
- Python 3 可用
- 目标 WebDAV 服务的 URL、用户名、密码

## 解决方案矩阵

| 方案 | 需要 | 适合 |
|------|------|------|
| rclone CLI | 无 root | 命令行操作、脚本集成 |
| rclone serve webdav + web UI | 无 root | 网页浏览器管理 |
| Python webdavclient3 | pip/uv 安装 | 程序化接入，自动化入库 |
| FileBrowser | 无 root，单文件二进制 | 完整网页文件管理器 |
| rclone mount | **FUSE** + `/dev/fuse` | 真实文件系统挂载（需要 root 设备节点） |

## 快速开始

### 1. 安装 rclone（无 root）

```bash
python3 -c "
import urllib.request, zipfile, os, stat
urllib.request.urlretrieve('https://downloads.rclone.org/rclone-current-linux-amd64.zip', '/tmp/rclone.zip')
with zipfile.ZipFile('/tmp/rclone.zip', 'r') as zf:
    for f in zf.namelist():
        if f.endswith('/rclone'):
            zf.extract(f, '/tmp/')
            os.rename(f'/tmp/{f}', '/tmp/rclone')
            os.chmod('/tmp/rclone', stat.S_IRWXU)
            break
"
/tmp/rclone version
```

### 2. 配置 WebDAV Remote

```bash
/tmp/rclone config create <remote-name> webdav \
  url <WEBDAV_URL> \
  vendor other \
  user <USERNAME> \
  pass "$(/tmp/rclone obscure <PASSWORD>)" \
  --non-interactive
```

配置保存路径：`~/.config/rclone/rclone.conf`。建议复制到持久路径并创建软链接。

### 3. 启动 Web 文件管理器

两步走：
- **端口 8080**：rclone serve webdav（API）
- **端口 8081**：Python http.server 提供 Web UI

```bash
# 启动 WebDAV API
/tmp/rclone serve webdav <remote-name>:/ \
  --addr :8080 \
  --vfs-cache-mode full \
  --dir-cache-time 300s &
  
# 启动 Web UI（提供 index.html 文件浏览器）
cd /path/to/web/root && python3 -m http.server 8081 &
```

### 4. 网页文件浏览器 HTML

一个自包含的暗黑主题 WebDAV 文件浏览器，纯前端（HTML + JS），无需后端框架：

- 使用 `PROPFIND` 方法通过 WebDAV API 列出目录
- 支持目录树导航（面包屑）
- 点击目录进入，点击文件下载
- 发到引用处：自己搭建一个 HTML 文件，JS 的 BASE 变量指向 WebDAV 端口

**关键实现要点**：
- WebDAV API 和 HTML 页面必须在不同端口时，JS 的 `fetch` 用完整地址（含端口号）
- `PROPFIND` 的响应是 XML，用 `DOMParser` 解析
- 响应标签带命名空间 `D:` 前缀（如 `D:response`, `D:href`）
- XML 选择器要用 `querySelector('D\\:href, href')` 兼容两种格式

## 无 FUSE 挂载方案

当 FUSE 不可用时（`/dev/fuse` 不存在，无法 `mknod`），不能做真正的文件系统挂载。替代方案：

### 方案 A：rclone serve webdav（推荐）

把 WebDAV 暴露为本地端口上的 WebDAV 服务，其他支持 WebDAV 的工具（Windows 资源管理器、macOS Finder、RaiDrive）可以连接。

```bash
/tmp/rclone serve webdav remote:/ --addr :8080
```

然后本地电脑用 SSH 隧道访问：
```bash
ssh -L 8080:localhost:8080 your-server
```

### 方案 B：Python webdavclient3（程序化访问）

```python
from webdav3.client import Client
c = Client({
    'webdav_hostname': 'http://dav.example.com:80',
    'webdav_login': 'user',
    'webdav_password': 'pass'
})
# 列出文件
files = c.list('/')
# 下载
c.download('/remote/path/file.txt', '/local/path/file.txt')
# 上传
c.upload('/local/path/file.txt', '/remote/path/file.txt')
```

安装：`uv pip install webdavclient3`

### 方案 C：rclone sync 定期同步

```bash
# 单向同步（云端 → 本地）
/tmp/rclone sync remote:/ /opt/data/storage -P

# 只同步小文件（< 50MB）
/tmp/rclone sync remote:/ /opt/data/storage --max-size 50M -P

# 仅同步目录结构（空目录）
/tmp/rclone sync remote:/ /opt/data/storage --create-empty-src-dirs
```

## 工具脚本模板

创建一个 `storage.sh` 管理脚本（参见 `scripts/` 目录下的脚本示例）：

```bash
#!/usr/bin/env bash
RCLONE="/tmp/rclone"
REMOTE="mystorage"
LOCAL="/opt/data/storage"
PIDFILE="/tmp/storage_webdav.pid"

case "${1:-help}" in
  start)
    # WebDAV API
    nohup $RCLONE serve webdav "$REMOTE:/" --addr :8080 \
      --vfs-cache-mode full --dir-cache-time 300s > /tmp/storage_webdav.log 2>&1 &
    echo $! > "$PIDFILE"
    # Web UI
    cd "$LOCAL" && nohup python3 -m http.server 8081 > /tmp/storage_ui.log 2>&1 &
    echo $! > "/tmp/storage_ui.pid"
    ;;
  stop)
    kill $(cat "$PIDFILE" 2>/dev/null) 2>/dev/null
    kill $(cat /tmp/storage_ui.pid 2>/dev/null) 2>/dev/null
    ;;
  ls)
    $RCLONE tree "$REMOTE:${2:-/}" --max-depth 1
    ;;
  get)
    $RCLONE copy "$REMOTE:${2}" "${3:-$LOCAL}" -P
    ;;
  put)
    $RCLONE copy "${2}" "$REMOTE:${3:-/}" -P
    ;;
  sync)
    $RCLONE sync "$REMOTE:${2:-/}" "${3:-$LOCAL}" -P
    ;;
esac
```

## 批量下载多个文件

当需要从云盘下载多个特定文件时（如连续剧的指定集数），使用 `scripts/batch-download.sh`：

```bash
bash /opt/data/skills/productivity/webdav-storage/scripts/batch-download.sh \
  pikpak "/Movie/大军师司马懿之军师联盟" \
  /opt/data/PikPak/大军师司马懿之军师联盟 \
  EP12 EP17 EP21 EP25 EP28
```

脚本特性：
- **自动模糊匹配** — `EP12` 自动匹配 `The.Advisors.Alliance.2017.EP12...mp4`
- **顺序下载** — 逐个下载，不压垮远程服务器
- **断点续传** — 中断后重跑自动从断点继续
- **自动重试** — 失败后等 3 秒再试，最多 3 次
- **校验** — `--checksum` 保证文件完整性

## 大文件下载 & Token 优化

大文件下载建议用**后台模式**，避免消耗对话 token：

```bash
# 在 Hermes 代理会话中，用 background + notify_on_complete
bash /opt/data/pikpak.sh get /路径/大文件.mp4
```

- `notify_on_complete=true` — 下完了自动通知用户
- 中间不消耗 token，用户可以继续聊别的
- 用户可以随时问"下到哪了"查看进度

## 支持文件

- `scripts/batch-download.sh` — 批量下载脚本，支持模糊匹配文件名、断点续传、自动重试
- `references/pikpak-setup.md` — PikPak 具体连接信息、端口配置、Docker 网络排查

## 已知陷阱

1. **FUSE 不可用时不要强求 mount** — 容器/受限环境无法创建设备节点（`mknod /dev/fuse` 被拒），`rclone mount` 报 `fusermount: exec: "fusermount3" not found`。改用 serve webdav + web UI。
2. **慢速远程列表超时** — PikPak 等境外服务列表可能 >30s。设置 `--dir-cache-time 300s` 缓存。Web UI 要显示 loading 状态而不是白屏。
3. **rclone 配置持久化** — `rclone config create` 默认写 `~/.config/rclone/rclone.conf`。容器重启可能丢失，需手动复制到持久路径。
4. **rclone serve http vs serve webdav** — `serve http` 提供 HTTP 文件浏览（可下载），`serve webdav` 提供完整 WebDAV（可读写+删除）。选择取决于需求。
5. **大文件下载** — PikPak 上文件可能数 GB，rclone 支持断点续传和多线程（`--multi-thread-streams 4`）
6. **FileBrowser 的密码长度** — FileBrowser 默认密码最短长度 12 位。配置时注意。

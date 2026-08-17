# PikPak 下载策略 (2026-06-27)

## 禁忌
- ❌ **严禁走代理**下载 PikPak 文件。代理按流量收费且速度极慢（0.3 KB/s 级）
- ❌ **严禁多线程 rclone cat --offset --count** 并发分片——PikPak WebDAV 严格限制并发 Range 请求，会触发 503 或返回空数据
- ❌ 不要在 **1 小时内频繁中断重试**——每次新连接都会触发新的限流计数器

## 方案排名

### 🥇 CDN 直链 + Python urllib 多线程 Range（推荐）
- **速度**：8线程 × 0.2MB/s ≈ **1.6 MB/s**，稳定不掉速
- **原理**：`PikPakApi.get_download_url()` 获取 CDN URL → Python urllib Range 分片并发
- **缺点**：需要 pikpakapi 库和缓存的 token
- **代码**：`/opt/data/pikpak_cdn_dl.py`

### 🥈 rclone copy (单线程)
- **速度**：0.3~1.5 MB/s，**持续降速**（1h 后可能掉到 50 KB/s）
- **命令**：`timeout 3600 rclone copy pikpak:/Inbox-JAV/FILE.mp4 /local/ --buffer-size=128M --multi-thread-streams=0 --progress --timeout 60s --contimeout 30s`
- **适用**：纯 WebDAV 通道，无依赖

### 🥉 rclone copyurl + CDN 直链
- **速度**：0.2 MB/s 稳定
- **命令**：`timeout 3600 rclone copyurl "$CDN_URL" /local/FILE.mp4 --progress --timeout 60s --contimeout 30s`
- **优点**：绕过 WebDAV 限流，不需要 pikpakapi 留在脚本中

### ❌ 其他方案
| 方式 | 速度 | 原因 |
|:----|:---:|:-----|
| Python urllib 直连 WebDAV | 403 | 密码解密问题 |
| CDN 单连接 Range | 0.2 MB/s | 单连接限流 |
| 代理 + 任何方式 | 0.3 KB/s | 代理到 PikPak 路由差 |
| aria2 | 无法安装 | GitHub 被墙，镜像不可用 |

## CDN 直链获取流程

```python
import asyncio, json
from pikpakapi import PikPakApi

with open('/opt/data/.pikpak_token.json') as f:
    token = json.load(f)

async def get_url(filename):
    client = PikPakApi(encoded_token=token['encoded_token'])
    files = await client.file_list()
    for f in files.get('files', []):
        if 'Inbox-JAV' in f.get('name',''):
            inbox = await client.file_list(parent_id=f['id'])
            for sf in inbox.get('files', []):
                if sf.get('name') == filename:
                    dl = await client.get_download_url(sf['id'])
                    # 取 links 里的 URL（比 web_content_link 更稳定）
                    links = dl.get('links', {})
                    for k, v in links.items():
                        return v.get('url', '')
                    return dl.get('web_content_link', '')
```

### CDN URL 特点
- 有效期 ~24h（expire 字段）
- **支持 Range 请求**（206 Partial Content）✅
- 支持**并发 Range 分片**（8 线程同时跑没问题）
- 不像 WebDAV 那样限流并发数

## Python 多线程下载参数

最佳实践（来自实测）：

```python
# 从 /tmp/pikpak_urls.json 读取预存的 URL
# 先用 pikpakapi 一次性获取所有文件的直链，存起来再用

THREADS = 8           # 8 线程并发
CHUNK_SIZE = 8 * 1024 * 1024  # 8MB/片，适中
CHUNK_TIMEOUT = 120   # 每片超时 2min（8MB @ 0.2MB/s ≈ 40s）
RETRIES = 3           # 每片重试 3 次
```

## 注意事项

1. **先拿直链再下载**：pikpakapi 的 `get_download_url()` 可能耗时 3-8s，先存到 `/tmp/pikpak_urls.json` 再跑下载脚本
2. **后台运行**：Python 脚本在 Hermes background=true 模式运行时，输出默认被缓冲，需要加 `PYTHONUNBUFFERED=1` 或 `-u` 参数
3. **分片不宜过大**：64MB/片会导致单片耗时超 5 分钟，易触发超时；8MB/片约 40s 合适
4. **文件名硬编码大小**：CDN HEAD 请求可能不返回 Content-Length，建议在脚本里硬编码已知文件大小或提前获取
5. **合并阶段**：所有分片下载完成后按 index 顺序合并，不需要额外校验（HTTP Range 保证数据完整性）

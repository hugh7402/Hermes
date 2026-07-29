# PikPak API 踩坑记录（实战案例）

本文件记录了开发 JAV 下载智能体时遇到的 PikPak API 问题，作为 `agent-smart-development` 方法论的真实案例参考。

## API 特性速查

| 操作 | 端点 | 方法 | 备注 |
|:----|:----|:----:|:----|
| 添加离线下载 | `/drive/v1/files` | POST | `upload_type: UPLOAD_TYPE_URL` |
| 查文件夹子文件 | `/drive/v1/files` | GET | `?parent_id={folder_id}` ← 不要用 `params.files` |
| 移动文件 | `/drive/v1/files:batchMove` | POST | 必须是 POST，不是 PATCH parent_id |
| 重命名 | `/drive/v1/files/{id}` | PATCH | `{"name": "新名称"}` |
| 删除到回收站 | `/drive/v1/files:batchTrash` | POST | `{"ids": [... ]}` |
| 任务列表 | `/drive/v1/tasks` | GET | 离线下载任务状态 |

## 坑 1：`params.files` 永远为 0

**直觉猜测**：`offline_file_info(file_id)` 返回的 `params.files` 会列出磁链内的所有文件。

**真相**：PikPak 根本不返回这个字段。查子文件必须用 `file_list(parent_id=folder_id)`。

**教训**：不要对着 API 响应结构猜字段含义——先 curl 看实际返回。

## 坑 2：`selected_files` PATCH 来不及

**直觉猜测**：PATCH 文件夹的 `selected_files` 可以只下载指定文件。

**真相**：PikPak 解析磁链极快（4-6s 从 "not found" → "PHASE_TYPE_COMPLETE"），PATCH 根本来不及生效，返回 `file_nothing_updated`。等你能查到子文件时，PikPak 已经全部下完了。

**正确方案**：等所有子文件下载完成后，删除广告文件。虽然浪费了几十 MB 广告下载带宽，但这是唯一可靠方案。

## 坑 3：PATCH parent_id 移不出文件

**直觉猜测**：`PATCH /drive/v1/files/{id} {"parent_id": "新目录ID"}` 可以移动文件。

**真相**：返回 `file_nothing_updated`。必须用 **`POST /drive/v1/files:batchMove`** 端点，body 为 `{"ids": ["文件ID"], "to": {"parent_id": "目标目录ID"}}`。

## 坑 4：重命名必须在删文件夹之前

**顺序错误**：
```
1. delete_to_trash([folder_id])  ← 先删文件夹
2. PATCH rename(file_id)         ← 报 "file_rename_in_recycle_bin"
```

**正确顺序**：
```
1. batchMove(video, parent)      ← 移出视频
2. sleep(1)                      ← 等 PikPak 处理完
3. PATCH rename(video)           ← 重命名
4. delete_to_trash([folder_id])  ← 最后删空文件夹
```

## 坑 6：javdb 字幕关键词——破解不算法

**用户纠正 (2026-06-27)**：磁链名称中 `破解` 不代表有字幕。`破解` 通常指无码/破解版，不等于字幕版。

**正确的字幕关键词**：`-C`、`字幕`、`中字`。不含 `破解`。

```python
# ✅ 正确的检测逻辑
has_sub = '-C' in name or '字幕' in ctx or '中字' in name

# ❌ 错误：破解不代表有字幕
has_sub = '-C' in name or '字幕' in ctx or '中字' in name or '破解' in name
```

**教训**：领域特定词汇不要靠猜，用户纠正后立即记录。

## 坑 5：创建完成后 file_id 可能为空

添加磁链后，`offline_download()` 返回的 `file_id` 可能为空字符串。需要轮询 `offline_list()` 拿到实际的 `file_id`。

```python
file_id = task.get('file_id', '') or task.get('reference_resource', {}).get('id', '')
for i in range(10):
    await asyncio.sleep(2)
    flist = await client.offline_list(size=1)
    ...
    file_id = tasks[0].get('file_id', '') or tasks[0].get('reference_resource', {}).get('id', '')
    if file_id: break
```

## 坑 7：PikPak WebDAV rclone 同步——503 限流与速度波动

**rclone 配置**（WebDAV 直连，不走代理）：
```
type = webdav
url = http://dav.mypikpak.com:80
vendor = other
```

**关键发现**：
- **不走代理**：WebDAV 直接 HTTP 连接 dav.mypikpak.com:80，无需 SOCKS5
- **速度波动大**：实测 500 KB/s ~ 3.2 MB/s，受时段和并发数影响
- **503 Service Unavailable**：PikPak 服务端限流。两个下载同时跑时更易触发
- **文件大小差异**：磁链显示 4.35GB，PikPak 实际文件可达 10.9GB（含额外流/轨道数据）
- **partial 文件被删**：kill rclone 进程后 partial 缓存被清理，进度丢失。下次重启从头传
- **rclone 二进制位置**：`/tmp/rclone`（非 PATH 内），需用全路径调用

**代理使用策略**（用户 2026-06-27 确认）：
```
✅ 必须用代理：javdb 搜索、subtitlecat 搜索/字幕下载（被墙网站）
❌ 不用代理：PikPak API 调用、rclone WebDAV 同步（直连可达）
注意：SOCKS5 代理按流量计费且慢，只给被墙的站点用。
```

**推荐下载策略**：一次只传一个文件，避免并发触发 503。rclone 命令：
```bash
/tmp/rclone copy pikpak:/Inbox-JAV/番号.mp4 /opt/data/PikPak/Inbox-JAV/ --progress --verbose
```

## 开发流程复盘（对照方法论）

### ❌ 实际走的弯路
```
猜 selected_files 可行 → 写完整函数 → 跑(60s) → 失败
改 retry → 跑(60s) → 还是失败
换 params.files 思路 → 跑(60s) → 还是不行
最终发现 file_list + batchMove
→ 浪费 4 轮 × 60s + 无数来回改
```

### ✅ 应该怎么走
```
Spike 阶段：
  curl API 测试 → 发现 params.files=0 (2分钟)
  改用 file_list → 确认可行

开发阶段：
  写删除广告 → curl 验证 → ok
  加 batchMove → curl 验证 → ok
  加重命名 → curl 验证 → ok
  集成 → 一次过

→ 省下 3 轮完整测试 ≈ 3分钟 + 避免来回试错
```

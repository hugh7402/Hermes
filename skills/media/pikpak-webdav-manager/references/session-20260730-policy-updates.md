# 2026-07-30 更新的下载策略

## aria2 启动命令模板

```bash
export LD_LIBRARY_PATH=/opt/data && exec /opt/data/aria2c \
  --max-connection-per-server=8 --split=8 --min-split-size=8M \
  --continue=true --max-tries=5 --retry-wait=5 --timeout=120 \
  --console-log-level=notice --dir=/tmp/dl --out=番号.mp4 \
  "$CDN_URL"
```

- 安全扫描每次报 `CRITICAL`（LD_LIBRARY_PATH 注入风险），但自动放行。
- 每个文件独立 `terminal(background=true, notify_on_complete=true)` 启动。
- 必须 `rm -f` 旧文件后再用新 URL 重下，不能依赖 `--continue=true` 续传 403 后的文件。

## 并发限制

最多 5 个文件同时下载，其余排队顺序处理。

## 死种/异常重试

- 死种（从 PikPak 离线列表消失）、size=0、javdb 无磁链 → 等待 30 分钟后重新搜索 javdb 并重试，最多 3 次。
- 用户确认放弃前不要私自跳过。

## 状态汇报规范

汇报进度时包含：速度（MB/s）、进度百分比、ETA。示例：
`ATID-537 | 573MiB/5.0GiB (11%) CN:8 DL:11MB/s ETA:7min`

## 文件夹内文件处理

jav_manager.py 的广告清理/移出步骤可能未执行，导致文件留在 PikPak 文件夹内（`kind=drive#folder`, `size=0` 但内部有视频）。处理方式：
1. `file_list(parent_id=folder_id)` 列出子文件
2. 直接对内部视频文件（>1GB）调用 `get_download_url(child_id)`
3. 广告文件（<100MB）忽略

## 后下载字幕审计（新增）

所有番号下载到本地并自定义重命名后，需执行一遍字幕全检：
1. 按文件名区分：`-C`/`-UC` → 内嵌字幕，跳过
2. 裸版文件 → 检查 Inbox-JAV 目录下有无对应 `.srt`
3. 有 `.srt` 但文件名是原始名（如 `[88k.me]NDRA-059.srt`）→ 同步重命名为自定义视频同名
4. 无 `.srt` → subtitlecat 搜索下载 + 重命名

**本会话案例**：
- NDRA-059：jav_manager.py Phase 2.5 下载了 `[88k.me]NDRA-059.srt` 到 Inbox-JAV，但 aria2 下载视频并用自定义名改后，.srt 未被自动同步。需手动 `cp`。
- NSPS-979：用户反馈实际无内嵌字幕（磁链名含 `C字幕` 但用户说没有）。subtitlecat 找到 `NSPS-979 whisper-zh-CN.srt`（2669行，32KB）→ 下载 + 重命名。
- GMEN-010：裸版，subtitlecat 无资源 → 告知用户后放弃。

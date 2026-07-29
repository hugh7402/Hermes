# PikPak 多文件磁链广告清理参考

## 问题

javdb 的磁链经常包含文件夹，里面除了主视频还有广告视频/HTML/readme。PikPak 没有提供在下载前选择单文件的有效 API。

## 最终方案：下载后清理 + 移出 + 重命名

尝试过的方案：PATCH `selected_files` → ❌ PikPak 解析太快，来不及生效
最终方案：`file_list() + delete_to_trash() + batchMove() + rename` → ✅ 可靠

## API 行为验证

### 添加磁链后文件状态变化

用 DSOD-005-C 磁链测试的时间线：

```
t+0s    POST offline_download → file_id=xxx, msg=Saving
t+0s    offline_file_info(file_id) → ❌ "File or folder is not found"
t+4s    offline_file_info(file_id) → kind=drive#folder, phase=PHASE_TYPE_COMPLETE
t+4s    file_list(parent_id=file_id) → 3 files (1 video + 2 ads)
t+4s    所有子文件 phase=PHASE_TYPE_COMPLETE → 已全部下载
```

关键发现：PikPak 从 "not found" → "COMPLETE" 仅需 ~4 秒，期间不存在可操作的中间状态。

### PATCH selected_files 测试结果

```
PATCH drive/v1/files/{folder_id}
{
  "kind": "drive#folder",
  "params": {},
  "selected_files": [{"id": "489155.com@DSOD-005.mp4", "size": "6764512256", "required": true}]
}
→ 400 {"error": "file_nothing_updated", "error_code": 3}
```

### 正确方案：file_list

```python
children = await client.file_list(parent_id=folder_id)
cfiles = children.get('files', [])
# cfiles = [
#   {"name": "社 區 最 新 情 報.mp4", "size": "15089802", "phase": "PHASE_TYPE_COMPLETE"},
#   {"name": "台湾uu美少女直播 20年信誉保证服务全球.mp4", "size": "13890047", "phase": "PHASE_TYPE_COMPLETE"},
#   {"name": "489155.com@DSOD-005-C.mp4", "size": "6091520253", "phase": "PHASE_TYPE_COMPLETE"}
# ]

# 删广告
await client.delete_to_trash([ad_file_id_1, ad_file_id_2])
```

### 文件夹结构特征

- `kind=drive#folder` — 多文件磁链创建的是文件夹
- `params.files` 始终为 0 — PikPak 不通过 `offline_file_info` 暴露子文件
- 子文件通过 `file_list(parent_id=folder_id)` 查看
- 广告文件名特征：`社 區 最 新 情 報.mp4`、`台湾uu美少女直播...mp4`、`sample.html`、`readme.txt`、`JAV目录.html`
- 视频文件名可能带推广前缀：`489155.com@DSOD-005-C.mp4`（番号匹配不受影响）

## 清理逻辑

```python
video_exts = {'.mp4','.mkv','.avi','.wmv','.mov','.flv','.ts','.m4v','.webm'}
code = 'DSOD-005'
code_nohyphen = code.replace('-', '').upper()  # 'DSOD005' — 必须同时匹配两种形式！

for f in cfiles:
    fname = f.get('name', '')
    ext = os.path.splitext(fname)[1].lower()
    fname_upper = fname.upper()
    if ext in video_exts and (code in fname_upper or code_nohyphen in fname_upper):
        keep = f  # 主视频
    else:
        to_delete.append(f['id'])  # 广告/非视频
```

**⚠️ 番号匹配横杠陷阱（2026-07-18）**：磁链文件名经常省略横杠（如 `CAWD001C.mp4` 而非 `CAWD-001-C.mp4`）。如果只匹配 `code in fname.upper()`，带横杠的 `CAWD-001` 匹配不上 `CAWD001C`，**主视频会被误当广告删除**。必须同时检查 `code.replace('-','').upper() in fname.upper()`。

## 最终整理：移出视频 + 删空文件夹

### PikPak API 正确方法名（关键）\n\npikpakapi 库的方法名是下划线风格，不是驼峰：\n\n| 正确 | 错误（不存在） |\n|------|---------------|\n| `client.file_batch_move([ids], parent_id)` | `client.batchMove([ids], '')` ❌ |\n| `client.file_rename(id, name)` | `client.update_file(id, name=...)` ❌ |\n| `client.file_list(parent_id=...)` | `client.file_list(limit=...)` ❌ （无 limit 参数）|\n| `client.delete_to_trash([ids])` | — ✅ |\n| `client.offline_download(magnet)` | — ✅ |\n| `client.offline_file_info(id)` | — ✅ |\n| `client.get_download_url(id)` | — ✅ |\n| `client.offline_list()` | — ✅ |\n\n### batchMove API（而非 PATCH parent_id）

简单 PATCH `parent_id` 会失败：`{"error":"file_nothing_updated"}`。

必须用专用 batchMove 端点：

```python
url = f"https://{client.PIKPAK_API_HOST}/drive/v1/files:batchMove"
hdrs = client.get_headers()
hdrs['Content-Type'] = 'application/json'
data = {"ids": [video_file_id], "to": {"parent_id": target_parent_id}}
resp = await client.httpx_client.post(url, json=data, headers=hdrs)
# 200 → 成功移出
```

### 完整序列（⚠️ 顺序重要）

```
1. delete_to_trash([广告文件ID列表])   → 删广告
2. batchMove(视频文件, Inbox-JAV ID)   → 视频移到根目录
3. asyncio.sleep(1)                   → 等 PikPak 处理完毕
4. PATCH rename: 视频文件 → DSOD-005-C.mp4  → 重命名（保留 -C 后缀）
5. delete_to_trash([空文件夹ID])       → 删空文件夹
6. 最终: 根目录只有 DSOD-005-C.mp4 ✅
```

**为什么重命名必须在删文件夹之前？**
先删文件夹再重命名会报：`"file_rename_in_recycle_bin"` — PikPak 认为文件在回收站里。正确顺序是 move → rename → delete_folder。

## 重命名实现

```python
# 保留 -C 后缀
old_name = keep.get('name', '')
base = os.path.splitext(old_name)[0]
ext = os.path.splitext(old_name)[1]
suffix = ''
for s in ['-C', '-U', '_C', '_U']:
    if s in base.upper():
        suffix = s
        break
clean_name = f'{code}{suffix}{ext}'  # e.g. DSOD-005-C.mp4

# PATCH 重命名
rename_url = f"https://{client.PIKPAK_API_HOST}/drive/v1/files/{video_id}"
rename_hdrs = client.get_headers()
rename_hdrs['Content-Type'] = 'application/json'
await client.httpx_client.patch(rename_url, json={"name": clean_name}, headers=rename_hdrs)
```

## Phase 3: 本地同步

下载完成后，`jav_manager.py` 自动执行 rclone 同步：

```python
# 1. 查远程文件列表
r = subprocess.run(["/tmp/rclone", "lsjson", "pikpak:/Inbox-JAV"],
                   capture_output=True, text=True, timeout=120)
files = json.loads(r.stdout)

# 2. 比对已下载记录
downloaded = set(json.load(open(RECORD_FILE))) if os.path.exists(RECORD_FILE) else set()
new = [(f["Name"], f"{f['Name']}|{f['Size']}|{f.get('ModTime','')}")
       for f in files if f["Size"] > 0 and key not in downloaded]

# 3. rclone copy 新文件
subprocess.run(["/tmp/rclone", "copy", "--files-from", list_file,
    "pikpak:/Inbox-JAV", "/opt/data/PikPak/Inbox-JAV/",
    "--transfers", "2", "--checksum"], timeout=7200)
```

记录文件格式：
```json
["DSOD-005-C.mp4|6091520253|2026-06-27T02:41:...", "HMN-850.mp4|6507940156|..."]
```
每条 = `文件名|文件大小|修改时间`，用于去重。

## 看门狗模式（--watch）

每 10 分钟 cron 执行 `jav_manager.py --watch`：

```
1. 检查 .watch_active 标志 → 不存在则静默退出
2. rclone_sync() 同步新文件
3. 有新文件 → 刷新 .watch_idle_since
4. 无新文件 > 55 分钟 → 清除标志，休眠
```

## API 参考

| 操作 | 端点 | 方法 | 状态码 |
|------|------|:----:|:------:|
| 添加离线下载 | `/drive/v1/files` | POST | 200 |
| 查文件详情 | `/drive/v1/files/{id}` | GET | 200 |
| 列子文件 | `/drive/v1/files?parent_id={id}` | GET | 200 |
| 批量删除 | `/drive/v1/files:batchTrash` | POST | 200 |
| 批量移动 | `/drive/v1/files:batchMove` | POST | 200 |
| 重命名 | `/drive/v1/files/{id}` | PATCH | 200/204 |

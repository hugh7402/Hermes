# PikPak 文件夹清理：move-后-验证 工作流（2026-08-14 教训）

## 事故复盘

给 u9a9.com 的 Retsu_dao 搜索页批量离线 34 个磁链后清理时：
- 日志显示 31 个文件夹"✅ 移出成功"（batchMove 返回 200）
- 实际目标目录只有 18 个视频 → **13 个视频被彻底删除**
- 回收站查不到（`files?trashed=true` 只有 10 个 0MB 根目录文件夹壳）

根因：**batchMove 是异步操作，HTTP 200 只代表请求被接受，不代表移动完成**。
清理脚本紧接着 `delete_to_trash([folder_id])` 删源文件夹，还在文件夹里（未移动完）的视频被连带彻底删除。删文件夹时子文件不进回收站。

## 正确清理流程（每个文件夹）

```python
VIDEO_EXTS = {'.mp4', '.mkv', '.avi', '.wmv', '.mov', '.flv', '.ts', '.m4v', '.webm'}
TARGET_ID = '...'  # 目标文件夹 id（用 file_list 逐级找，别用 path_to_id 解析含 @ 的二级路径）

r2 = await api.file_list(parent_id=folder_id, size=50)
subs = r2.get('files', [])
videos = [f for f in subs if int(f.get('size', 0)) > 100*1024*1024
          and os.path.splitext(f.get('name', ''))[1].lower() in VIDEO_EXTS]
if not videos:
    # 文件夹里没有大视频：可能是广告文件夹或还在下载
    # 不要删！等下载完成再处理，或识别为广告假种子（任务名含 U5A5/U6A6）才删
    continue

vid = max(videos, key=lambda x: int(x.get('size', 0)))  # 取最大的视频
vname = vid['name']

# 1. 移出
url = f"https://{api.PIKPAK_API_HOST}/drive/v1/files:batchMove"
hdrs = api.get_headers(); hdrs['Content-Type'] = 'application/json'
resp = await api.httpx_client.post(url, json={
    "ids": [vid['id']], "to": {"parent_id": TARGET_ID}}, headers=hdrs)

# 2. 必须 sleep 让异步移动生效
await asyncio.sleep(2)

# 3. 验证目标目录确实出现该视频
r3 = await api.file_list(parent_id=TARGET_ID, size=100)
tgt_names = [f['name'] for f in r3.get('files', [])]
verified = any(vname in n or n in vname for n in tgt_names)

if verified:
    # 4. 验证通过才删广告 + 删空文件夹
    del_ids = [f['id'] for f in subs if f['id'] != vid['id']]
    if del_ids:
        await api.delete_to_trash(del_ids)
    await api.delete_to_trash([folder_id])
    print(f"✅ 已移出并清理: {vname[:30]}")
else:
    print(f"⚠️ 移动未验证，保留文件夹: {vname[:30]}")  # 别删！
```

## 其它本次踩坑

- **假种子**：`offline_download` 返回成功但任务名是 `【U5A5.COM】_全網最新國產資源站_xxx` / `2849.【U6A6.SU】...` → 磁链本身是广告，解包后无视频。识别后直接删文件夹，别等。
- **死种**：`offline_list()` 里 progress 卡 5-8、status=None、task_id=None → 无源。`offline_task_retry` 报 `Task does not exist`（文件夹删了任务就失效）。
- **重复添加被静默拒绝**：同一磁链添加过（即使任务已失败/文件夹已删）再 add，PikPak 不建新任务，0 命中——重试前先查离线任务列表确认真的没在跑。
- **数量核对**：目标目录文件名带 `2048.vip-`、`1 `、`-` 前缀，自动匹配（前 12 字符包含）会误报缺失/误报存在。最终核对必须**打印全名人工比对**。

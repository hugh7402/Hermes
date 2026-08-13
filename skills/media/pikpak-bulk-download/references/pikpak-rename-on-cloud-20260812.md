# PikPak 上批量重命名番号视频（2026-08-12 实战）

用户新工作流（CDN 限流期）：番号只离线到 PikPak + 在 PikPak 上直接改自定义文件名，不拉本地，等直连恢复后统一拉回。

## 流程

1. 逐个跑 `jav_manager.py --no-sync <番号>`（PikPak API 限频，一批 ≤8-10 个，逐个等完成）
   - javdb 搜索 → 选磁链（-C 内嵌字幕优先）→ 离线 → 清广告 → 自动重命名为 `{番号}{后缀}.mp4`
   - 无内嵌字幕的裸磁链版，Phase 2.5 会下 .srt 到本地 Inbox-JAV（PikPak 上只有视频）
2. 全部离线完成后，遍历 PikPak Inbox-JAV，按番号前缀匹配文件，PATCH 改自定义名：

```python
import json, asyncio, sys
sys.path.insert(0, '/opt/data/.venv/lib/python3.13/site-packages')
from pikpakapi import PikPakApi

RENAMES = {
    'ATID-691': 'ATID-691-水戶香奈-多P痴汉轮奸中出 ...女搜查官.mp4',
    # ... 每个番号一行
}

async def rename_all():
    state = json.load(open('/opt/data/.pikpak_token.json'))
    api = PikPakApi.from_dict(state)
    result = await api.path_to_id('/Inbox-JAV')
    inbox_id = result[0]['id']
    r = await api.file_list(parent_id=inbox_id, size=100)
    files = r.get('files', [])
    for code, new_name in RENAMES.items():
        target = next((f for f in files if code in f.get('name', '').upper()), None)
        if not target:
            print(f'❌ {code}: 未找到'); continue
        url = f"https://{api.PIKPAK_API_HOST}/drive/v1/files/{target['id']}"
        hdrs = api.get_headers(); hdrs['Content-Type'] = 'application/json'
        resp = await api.httpx_client.patch(url, json={"name": new_name}, headers=hdrs)
        print(f"{'✅' if resp.status_code in (200,201,204) else '❌'} {code} → {new_name[:50]}")

asyncio.run(rename_all())
```

## 要点

- 重命名在 **PikPak 上**完成（旧规则"PikPak 保留原名只本地改"已废弃——用户 2026-08-12 明确要求改在网盘上，这样拉回本地时文件名直接正确）
- 用户给的命名格式：`{番号}-{女优}-{标签} {描述}.mp4`（如 `SNOS-321-紫堂-多P轮奸 在学校穿着暴露的泳衣被学生们轮奸的极品没胸尤物女教师.mp4`）
- 用户给什么番号就搜什么番号，严禁替换/近似匹配（CAWB/CAWD 视觉相近坑）
- 汇报给用户的待同步清单含：番号 + 大小 + 字幕类型（内嵌 -C / 外挂 srt）
- 外挂 srt 在本地 Inbox-JAV，等 CDN 恢复拉回视频后需手动配同名

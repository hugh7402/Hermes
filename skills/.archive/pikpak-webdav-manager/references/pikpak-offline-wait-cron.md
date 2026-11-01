# PikPak 离线下载等待 + CDN 下载（no_agent cron 模式）

## 场景

PikPak 的离线下载（磁链/种子）需要时间处理，从几秒到几十分钟不等。如果直接用 rclone WebDAV 同步（Phase 3），对大文件容易超时（7200s timeout 仍可能不够）。

**更好的方案**：用 no_agent cron 每 5 分钟检查一次 PikPak 离线任务状态 → 完成后获取 CDN 直链 → 通知用户 → aria2 拉回本地。

## 架构

```
cron (no_agent, 每5分钟)
  └→ check_pikpak_dl.py (纯脚本，0 token)
        ├→ 检查离线任务列表
        ├→ 未完成 → 静默退出 (不通知用户)
        └→ 已完成 → 写直链到 /tmp/pikpak_urls.json → 通知用户
                         └→ 收到通知后，手工或后续 cron 跑 aria2 下载
```

## 脚本：check_pikpak_dl.py

脚本存放在 `~/.hermes/scripts/check_pikpak_dl.py`：

```python
#!/usr/bin/env python3
"""检查 PikPak 离线下载状态，完成时保存直链"""
import json, os, asyncio
from pikpakapi import PikPakApi

PIKPAK_TOKEN='/opt/data/.pikpak_token.json'
URLS_OUT = '/tmp/pikpak_urls.json'

async def check():
    with open(PIKPAK_TOKEN) as f:
        state = json.load(f)
    api = PikPakApi.from_dict(state)
    
    off = await api.offline_list(size=20)
    tasks = off.get('tasks', [])
    
    new_urls = {}
    for t in tasks:
        name = t.get('name', '')
        status = t.get('status', '?')
        prog = t.get('progress', 0)
        
        if status == 'completed' or prog == 100:
            fid = t.get('file_id', '') or t.get('reference_resource', {}).get('id', '')
            if fid:
                info = await api.get_download_url(fid)
                url = info.get('url', '')
                if url:
                    fn = f'{name}.mp4' if not name.endswith('.mp4') else name
                    new_urls[fn] = url
    
    if new_urls:
        existing = {}
        if os.path.exists(URLS_OUT):
            with open(URLS_OUT) as f:
                existing = json.load(f)
        existing.update(new_urls)
        with open(URLS_OUT, 'w') as f:
            json.dump(existing, f)
        print(f'✅ 新增 {len(new_urls)} 个直链')
        for n in new_urls:
            print(f'  {n}')
        return True  # exit 0 → 通知用户
    
    # 未完成 → 静默退出
    for t in tasks:
        print(f'⏳ {t.get("name","?")[:40]} | {t.get("status","?")} | {t.get("progress",0)}%')
    return False  # exit 1 → 不通知

if __name__ == '__main__':
    ok = asyncio.run(check())
    exit(0 if ok else 1)
```

## 创建 cron 任务

```bash
hermes cron create \
    --name "pikpak-offline-check" \
    --schedule "every 5 minutes" \
    --script "check_pikpak_dl.py" \
    --no-agent
```

## 收到通知后的操作

1. 检查直链文件：`cat /tmp/pikpak_urls.json`
2. 用 aria2 下载：
   ```bash
   export LD_LIBRARY_PATH=/opt/data
   /opt/data/pikpak_dl_aria2.sh
   ```
3. 验证完整性：
   ```bash
   ffprobe -v error -show_entries format=duration file.mp4
   ```

## 已知问题

- PikPak 磁链下载前期可能卡在 "Saving" 状态很久（0%，status=?），需要耐心等待
- CDN 直链有效期约 24 小时，如果检查间隔过大可能失效
- `path_to_id('/Inbox-JAV')` 比 `file_list(parent_id=...)` 更可靠——后者有时报 "File or folder is not found"

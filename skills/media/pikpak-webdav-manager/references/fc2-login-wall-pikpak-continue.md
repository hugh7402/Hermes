# FC2 番号 javdb 登录墙 → 用户自加 PikPak 后续流程（2026-08-04）

## 问题

FC2 番号在 javdb 是**隐藏分类**，未登录用户看不到磁链：
- jav_manager.py 搜索能命中视频页（`✅ FC2-xxx -> https://javdb.com/v/xxx`），但随即 `❌ 无磁链`
- 手动 curl 视频页：加 `-L` 后 `<title> 登入 | JavDB`（302 跳到登录页，页面含 `/login`、`/activate_registration` 链接）
- 普通番号不需要登录，只有 FC2 类隐藏内容触发登录墙

**先排除代理/节点问题**（javdb 403 + "banned your access" = IP 被封，换节点；302 到登入页 = 登录墙）。两者症状不同。

## 处理流程

1. **如实告知用户**："FC2 需 javdb 登录才能看磁链，自动流程无法获取"
2. **用户自行把资源加入 PikPak**（离线下载磁链或直链，用户在自己设备上登录 javdb 拿磁链）
3. **Agent 从 PikPak 继续**（等价于 jav-auto-download 的"重复番号处理"路径）：

```python
import json, asyncio
from pikpakapi import PikPakApi

async def run():
    token = json.load(open('/opt/data/.pikpak_token.json'))
    client = PikPakApi(encoded_token=token['encoded_token'])
    client.access_token = token['access_token']
    client.refresh_token = token['refresh_token']
    client.user_id = token['user_id']
    client.device_id = token['device_id']
    r = await client.path_to_id('/Inbox-JAV')
    files = await client.file_list(parent_id=r[0]['id'])
    for f in files.get('files', []):
        n = f.get('name', '')
        if 'FC2-xxx' in n.upper() and f.get('kind') == 'drive#file':
            print(f'{n} | {int(f.get("size",0))/1024**3:.2f}GB | id={f["id"]}')
            info = await client.get_download_url(f['id'])
            url = info.get('web_content_link') or ''
            json.dump({n: url}, open('/tmp/fc2_url.json', 'w'))
asyncio.run(run())
```

4. aria2 拉回 → ffprobe 校验 → **入库 `/opt/data/PikPak/Inbox-JAV/`**（番号视频，不是 Movie/）

## 关键点

- PikPak 中文件名可能是裸番号（`FC2-2769290.mp4`），本地下载时用 aria2 `--out` 改成带后缀的最终名（`FC2-2769290-白川柚子-...mp4`）
- 自定义后缀命名与 jav-auto-download 规则一致：`番号-女优-描述.mp4`
- 无字幕属正常（FC2 通常无字幕源），不要报错

# PikPak 文件夹内容列举（用于种子广告清理检查）

当 torrent 种子将文件下载到 PikPak 文件夹中时，主视频文件常与广告文件混在一起。需要列出文件夹内容以确认哪些是广告、哪些是主视频。

## 查询脚本

```python
import json, asyncio
sys.path.insert(0, '/opt/hermes/.venv/lib/python3.13/site-packages')
from pikpakapi import PikPakApi

FOLDER_IDS = {
    "PRED-847-C": "VOw8KjqBZLOA2jww_1g-",
    "atid-665": "VOw8Kzzyrrcj-weyYmAU",
}

async def list_folder(api, folder_id):
    ls = await api.file_list(parent_id=folder_id)
    files = ls.get('files', [])
    return files

async def main():
    with open('/opt/data/.pikpak_token.json') as f:
        state = json.load(f)
    api = PikPakApi.from_dict(state)

    for name, fid in FOLDER_IDS.items():
        print(f"\n📁 {name}")
        try:
            ls = await api.file_list(parent_id=fid)
            files = ls.get('files', [])
            print(f"  文件数: {len(files)}")
            for f in files:
                n = f.get('name', '?')
                sz = int(f.get('size', 0))
                kind = f.get('kind', '?')
                phase = f.get('phase', '?')
                sz_mb = sz / 1048576
                print(f"  [{phase}] {n:40s} {sz_mb:>8.0f}MB  kind={kind}")
        except Exception as e:
            print(f"  ❌ {e}")
        await asyncio.sleep(1)

asyncio.run(main())
```

## 典型输出

```
📁 atid-665
  文件数: 3
  [PHASE_TYPE_COMPLETE] 苍老师强力推荐.mp4                               74MB kind=drive#file    ← 广告
  [PHASE_TYPE_COMPLETE] 三上悠亚想要跟你决胜负.mp4                           19MB kind=drive#file    ← 广告
  [PHASE_TYPE_COMPLETE] 4k2.me@atid-665.mp4                          7597MB kind=drive#file    ← 主视频 ✅

📁 PRED-847-C
  文件数: 3
  [PHASE_TYPE_COMPLETE] 社区最新情报.mp4                                   14MB kind=drive#file    ← 广告
  [PHASE_TYPE_COMPLETE] 台湾uu美少女直播20年信誉保证服务全球.mp4                13MB kind=drive#file    ← 广告
  [PHASE_TYPE_COMPLETE] 489155.com@PRED-847-C.mp4                    5203MB kind=drive#file    ← 主视频 ✅
```

## 筛选规则

- 广告文件通常 < 100MB，文件名包含"推荐"、"直播"、"情报"等
- 主视频文件 > 1GB，文件名含番号
- 用 `jav_manager.py` 的 `pikpak_cleanup_ads()` 自动处理
- 如果 jav_manager 尚未处理（文件夹仍在），手动拉直链时取最大 mp4 的 file_id

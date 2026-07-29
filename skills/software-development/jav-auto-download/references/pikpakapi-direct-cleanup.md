# 直连 pikpakapi 清理磁链文件夹（DSOD-008 案例）

## 场景

磁链添加后 PikPak 创建了一个文件夹（非直接文件），需要手动清理广告、移动视频、重命名、删文件夹。

## 完整工作流

```python
import json, asyncio
from pikpakapi import PikPakApi

async def cleanup(api, inbox_id, folder_name='DSOD-008'):
    # 1. 列出 Inbox-JAV 找文件夹
    files = await api.file_list(parent_id=inbox_id)
    for f in files.get('files', []):
        if f.get('name') == folder_name and f.get('kind') == 'drive#folder':
            folder_id = f['id']
            
            # 2. 列出文件夹内容
            subfiles = await api.file_list(parent_id=folder_id)
            main_video = None
            ads = []
            for sf in subfiles.get('files', []):
                name = sf.get('name','')
                # size 是字符串！必须 int() 转换
                if 'hhd800' in name.lower():
                    main_video = sf['id']
                elif int(sf.get('size', '0')) < 50 * 1024 * 1024:
                    ads.append(sf['id'])
            
            # 3. 删除广告
            if ads:
                await api.delete_to_trash(ads)
            
            # 4. 移动主视频到 Inbox-JAV 根目录
            if main_video:
                await api.file_batch_move([main_video], inbox_id)
            
            # 5. 重命名（去掉广告前缀）
            files2 = await api.file_list(parent_id=inbox_id)
            for f2 in files2.get('files', []):
                if 'hhd800' in f2.get('name','').lower():
                    await api.file_rename(f2['id'], 'DSOD-008.mp4')
            
            # 6. 删除空文件夹
            await api.delete_to_trash([folder_id])

asyncio.run(main())
```

## 关键点

- **`size` 是字符串**：`file_list()` 返回的 `size` 字段是字符串，不是 int。比较大小必须 `int(sf.get('size', '0'))`
- **`kind=drive#folder`**：检测文件夹而非文件
- **执行顺序重要**：先 batchMove 移出 → 重命名 → 最后 delete_to_trash 删文件夹（不能先删文件夹再重命名，会报 `file_rename_in_recycle_bin`）
- **主视频识别规则**：文件名含番号或常见域名前缀（如 `hhd800.com@`） → 选最大的视频文件

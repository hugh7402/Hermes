# PikPak 种子下载文件夹结构

PikPak 离线下载种子（磁链）后，如果种子包含多个文件，会创建一个**文件夹**而非单个文件。
文件夹内可能有：主视频文件 + 广告视频文件。

## 典型结构

```
Inbox-JAV/
├── atid-665/              ← 文件夹（种子含多文件）
│   ├── 4k2.me@atid-665.mp4          7.6GB  ← 主视频（要下的）
│   ├── 苍老师强力推荐.mp4              74MB  ← 广告（跳过）
│   └── 三上悠亚想要跟你决胜负.mp4        19MB  ← 广告（跳过）
├── PRED-847-C/            ← 文件夹（种子含多文件）
│   ├── 489155.com@PRED-847-C.mp4    5.2GB  ← 主视频（要下的）
│   ├── 社区最新情报.mp4                14MB  ← 广告（跳过）
│   └── 台湾uu美少女直播...mp4         13MB  ← 广告（跳过）
└── MIDA-406-C.mp4          ← 直接是文件（单个种子）
```

## 判断规则

1. `drive#folder` → 种子包含多文件，需 `file_list(parent_id=文件夹id)` 展开
2. `drive#file` + `.mp4` → 直接可下
3. 广告文件特征：体积极小（<100MB）、中文文件名（如"苍老师推荐"、"社区最新情报"）、不包含番号
4. 主视频特征：体积最大（数GB）、文件名含番号或网站标记（`489155.com@`, `4k2.me@`）

## API 处理流程

```python
# 列出 Inbox-JAV 内容
ls = await client.file_list(parent_id=inbox_id)
for f in ls.get('files', []):
    if f.get('kind') == 'drive#folder':
        # 展开文件夹
        sub = await client.file_list(parent_id=f['id'])
        # 找最大的 mp4 文件
        mp4_files = [sf for sf in sub.get('files', [])
                     if sf.get('name','').endswith('.mp4')]
        main_file = max(mp4_files, key=lambda x: int(x.get('size', 0)))
        # 下载主文件
    else:
        # 直接下载
```

## 文件夹 ID 注意

`file_list(parent_id=文件夹ID)` 有时返回 "File or folder is not found"。
用 `path_to_id()` 获取的 ID 更可靠，或者直接从 `file_list()` 返回的 `id` 字段取完全 ID。

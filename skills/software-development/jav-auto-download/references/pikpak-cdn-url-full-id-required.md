# PikPak CDN 直链获取 — 完整 file ID 要求

## 坑

使用 `pikpakapi.get_download_url(file_id)` 获取 CDN 直链时，**必须传入完整的 file ID**，截断版本会返回 "File or folder is not found"。

### 正确 vs 错误

```
错误: get_download_url('VOw8FDYPL1n6I5mr2b3Q')
      → ❌ "File or folder is not found"

正确: get_download_url('VOw8FDYPL1n6I5mr2b3QkmiLo2')
      → ✅ 返回 URL
```

### 原因

`file_list()` 返回的 `id` 字段是完整的（如 `VOw8FDYPL1n6I5mr2b3QkmiLo2`），但终端显示时可能截断显示为 `VOw8FDYPL1n6I5mr2b3Q...`。如果用显示看到的截断 ID 去调 API，会失败。

### 正确做法

始终使用 `file_list()` 返回的完整 `f['id']`：

```python
ls = await api.file_list(parent_id=folder_id)
for f in ls.get('files', []):
    full_id = f['id']  # 完整 ID，不要手动截断
    info = await api.get_download_url(full_id)
    url = info.get('web_content_link', '') or \
          info.get('links', {}).get('application/octet-stream', {}).get('url', '') or \
          info.get('medias', [{}])[0].get('link', {}).get('url', '')
```

### 备用 URL 字段

`get_download_url()` 返回的 dict 可能在不同的字段携带 URL：

| 字段 | 适用场景 | 优先级 |
|------|---------|-------|
| `web_content_link` | 直接下载用 | 1st |
| `links.application/octet-stream.url` | 通用下载链接 | 2nd |
| `medias[0].link.url` | 流媒体播放用 | 3rd |

三个字段依次尝试，取第一个非空值。

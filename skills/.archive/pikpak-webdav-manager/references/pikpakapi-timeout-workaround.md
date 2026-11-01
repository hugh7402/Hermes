# pikpakapi 超时/慢速时的 fallback

## 问题现象

`pikpakapi` 在以下情况可能长时间无响应或超时：
- Token 需要刷新时的内部重试
- 网络延迟高时（某些 CDN 节点响应慢）
- `get_download_url()` 在文件较多时逐个请求

## 解决方案：直接调用 PikPak REST API

当 pikpakapi 超时（>30s），用 `urllib.request` + 手动 token 刷新替代：

```python
import json, urllib.request, urllib.parse

# 1. 刷新 token
tk = json.load(open('/opt/data/.pikpak_token.json'))
data = urllib.parse.urlencode({
    'client_id': 'YNxT9w7GMdWvEOKa',
    'client_secret': 'dbw2OtmVEe9R4uTjSBWG3xvS1Q1bqt24',
    'grant_type': 'refresh_token',
    'refresh_token': tk['refresh_token']
}).encode()

req = urllib.request.Request('https://user.mypikpak.com/v1/auth/token', data=data,
    headers={'Content-Type': 'application/x-www-form-urlencoded'})
with urllib.request.urlopen(req, timeout=10) as r:
    nt = json.loads(r.read().decode())

access_token = nt['access_token']
headers = {'Authorization': 'Bearer ' + access_token, 'Content-Type': 'application/json'}

# 2. 列出 Inbox-JAV 内容
base = 'https://api-drive.mypikpak.com/drive/v1/files'
url = f'{base}?parent_id=&page_size=100&type=ALL'
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req, timeout=10) as r:
    root = json.loads(r.read().decode())

# 找 Inbox-JAV 文件夹
inbox_id = [f['id'] for f in root.get('files', []) if f['name'] == 'Inbox-JAV'][0]

# 3. 列出文件夹内容
url = f'{base}?parent_id={inbox_id}&page_size=200&type=ALL'
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req, timeout=10) as r:
    files = json.loads(r.read().decode())

# 4. 获取单个文件详情（含 CDN URL）
# 对于文件：GET /drive/v1/files/{file_id}?space=DRIVE
# CDN URL 在 response['web_content_link'] 字段
fid = files['files'][0]['id']  # 取第一个文件的 ID
url = f'{base}/{fid}?space=DRIVE'
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req, timeout=10) as r:
    info = json.loads(r.read().decode())

cdn_url = info.get('web_content_link', '')
```

## 关键 API 端点

| 用途 | 方法 | URL | 超时 |
|:----|:----|:----|:----:|
| 刷新 token | POST | `https://user.mypikpak.com/v1/auth/token` | 10s |
| 文件列表 | GET | `https://api-drive.mypikpak.com/drive/v1/files?parent_id={id}&page_size=200&type=ALL` | 15s |
| 文件详情(含CDN) | GET | `https://api-drive.mypikpak.com/drive/v1/files/{file_id}?space=DRIVE` | 15s |
| 添加离线任务 | POST | `https://api-drive.mypikpak.com/drive/v1/task` | 15s |
| 离线任务列表 | GET | `https://api-drive.mypikpak.com/drive/v1/task?page_size=50&type=offline` | 15s |

## 注意事项

- 所有请求带 `Authorization: Bearer {access_token}` 和 `Content-Type: application/json`
- `client_id` 和 `client_secret` 是固定的（从 pikpakapi 源码获取）：`YNxT9w7GMdWvEOKa` / `dbw2OtmVEe9R4uTjSBWG3xvS1Q1bqt24`
- 直链有效期 24 小时
- 每次操作前先刷新 token，保存到 `.pikpak_token.json`

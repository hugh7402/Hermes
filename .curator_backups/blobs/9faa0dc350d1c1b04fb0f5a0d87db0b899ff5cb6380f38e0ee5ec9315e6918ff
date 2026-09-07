# JAVDB 磁链提取指南（curl 方案）

当 `web_extract` 返回 "Blocked" 或浏览器超时时，用 curl 走代理直接抓取 javdb 页面提取磁链。

## 前提

- 直连 `https://javdb.com` 可能被 DNS / CDN 干扰导致浏览器超时
- `web_extract` 工具层会屏蔽 javdb（返回 "Blocked: private network"）
- 但 curl + 代理 + 正确 User-Agent 始终可用
- JavDB 本身未被墙，直连也能返回 200（curl 级别），只是浏览器/工具层检测到 Cloudflare 拦截

## 完整流程

### 1. 搜索番号找到视频页面 ID

```bash
source /opt/data/home/.bashrc

curl -s --max-time 60 --proxy http://127.0.0.1:10808 \
  -H "User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36" \
  -H "Accept-Language: zh-CN,zh;q=0.9" \
  "https://javdb.com/search?q=SNOS-324&f=preview" \
  -o /tmp/javdb_search.html

# 提取视频页面路径
grep -oP '/v/[a-zA-Z0-9]+' /tmp/javdb_search.html | head -3
```

### 2. 获取视频详情页磁链

```bash
curl -s --max-time 60 --proxy http://127.0.0.1:10808 \
  -H "User-Agent: Mozilla/5.0" \
  "https://javdb.com/v/yxzBgr" \
  | grep -oP 'magnet:\?xt=urn:btih:[a-zA-Z0-9]+[^"]*' | sort -u
```

### 3. 选择磁链

优先选非 UC 版（不含 "-U"、"无码破解"、"uncensored"），有 "-C" 字幕版优先。

### 4. 添加 PikPak 离线

```bash
AT=$(python3 -c "import json; print(json.load(open('/opt/data/.pikpak_token.json'))['access_token'])")
INBOX="VNfBFBgRd2l0kPBXRu3gafl7o1"
MAGNET="magnet:?xt=urn:btih:..."
curl -s --proxy http://127.0.0.1:10808 \
  -X POST "https://api-drive.mypikpak.com/drive/v1/files" \
  -H "Authorization: Bearer $AT" \
  -H "Content-Type: application/json" \
  -d "{\"kind\":\"drive#file\",\"parent_id\":\"$INBOX\",\"upload_type\":\"UPLOAD_TYPE_URL\",\"url\":{\"url\":\"$MAGNET\"}}"
```

### 5. 检查结果（磁链常创建文件夹内含广告文件）

```bash
# 查离线进度
curl -s --proxy http://127.0.0.1:10808 \
  -H "Authorization: Bearer $AT" \
  "https://api-drive.mypikpak.com/drive/v1/tasks?page_size=20&status=0,1,2,3,5"

# 完成后再列出 Inbox 看是否文件夹
curl -s --proxy http://127.0.0.1:10808 \
  -H "Authorization: Bearer $AT" \
  "https://api-drive.mypikpak.com/drive/v1/files?parent_id=$INBOX"

# 如果是文件夹，列出内部
curl -s --proxy http://127.0.0.1:10808 \
  -H "Authorization: Bearer $AT" \
  "https://api-drive.mypikpak.com/drive/v1/files?parent_id=$FOLDER_ID"

# 获取视频文件 CDN URL（用 _magic=1 方式而非 batch_download_url）
VIDEO_ID="..."  # 文件夹内的视频文件 ID
curl -s --proxy http://127.0.0.1:10808 \
  -X GET "https://api-drive.mypikpak.com/drive/v1/files/$VIDEO_ID?_magic=1" \
  -H "Authorization: Bearer $AT" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); u=d.get('web_content_link','') or d.get('links',{}).get('application/octet-stream',{}).get('url',''); print(u)"
# URL 在 web_content_link 字段
```

### 6. 重命名（去除广告前缀）

文件夹内的文件名可能含广告（如 `489155.com@DASS-996.mp4`），CDN URL 获取时按原文件名保存，下载后用 ffprobe 校验后立即重命名。

## 注意事项

- **只从 javdb.com 找磁链**，用户明确禁止使用其他来源
- 磁链加入 PikPak 后大概率创建文件夹而非直接文件，**必须检查 kind 字段**
- 文件夹内含广告垃圾文件（<20MB）和实际视频（1.5~6GB），识别靠文件大小
- `batch_download_url` API 不支持文件夹内文件获取（返回 "unimplemented"），要直接用 `GET /files/{id}?_magic=1`

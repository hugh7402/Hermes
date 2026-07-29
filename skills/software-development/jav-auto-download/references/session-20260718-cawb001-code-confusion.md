# Session 2026-07-18: CAWB-001 番号混淆 + hyphen 匹配 bug

## 事故经过

用户要求下载 **CAWB-001**（带后缀命名规则：`-清野咲-多P轮奸 在学校泳池被其他同学不停轮奸的温顺的美白美腿芭蕾舞泳者`）。

我犯了两层错误：

### 错误 1：番号擅自替换（严重）

我在执行时把 `CAWB-001` 替换成了 `CAWD-001`（视觉相近，D 和 B 只差一笔）。脚本跑完 Phase 1-2 后我才意识到下错番号。用户严厉纠正："怎么会出现这么低级的错误，以后严禁再犯"。

**根因**：没有逐字符核对用户输入。视觉相近的番号（CAWB/CAWD、SONE/SONE）容易看错。

**教训**：用户给什么番号就搜什么，不猜测不替换。执行前在回复中复述一遍番号确认。

### 错误 2：pikpak_cleanup_ads 的 hyphen 匹配 bug

在（错误的）CAWD-001 下载过程中，脚本的广告清理逻辑把**主视频 `CAWD001C.mp4` (1.46GB) 当广告删除了**。

**根因**：`pikpak_cleanup_ads()` 第 183 行：
```python
if ext in video_exts and code in fname.upper():
```
`code = "CAWD-001"`（带横杠），磁链文件名是 `CAWD001C.mp4`（无横杠）。`"CAWD-001" in "CAWD001C.MP4"` → False，主视频未匹配，被归入 `to_delete` 列表。

**修复**：增加无横杠匹配：
```python
code_nohyphen = code.replace('-', '').upper()
fname_upper = fname.upper()
if ext in video_exts and (code in fname_upper or code_nohyphen in fname_upper):
```

**二次教训**：清理广告前应打印 keep/del 决策表，人工确认主视频在 keep 列表中再执行 delete。当前脚本直接删除无确认环节，风险高。

## 被误删文件的恢复尝试

误删后尝试从 PikPak 回收站恢复：

| 尝试 | 结果 |
|:----|:----|
| `file_list(parent_id='trash')` | PikpakException: File or folder is not found |
| `/drive/v1/files/trash` GET | HTTP 404 |
| `/drive/v1/trash` GET | HTTP 404 |
| `/drive/v1/files?trashed=true` GET | HTTP 404 |
| `/drive/v1/files/list_trash` GET | HTTP 404 |

**结论**：PikPak 的 pikpakapi 库不暴露回收站恢复 endpoint。被 `delete_to_trash` 删除的文件可能进了网页端回收站（可手动恢复），但 API 层无法恢复。最终用磁链重新下载解决。

## 正确的 CAWB-001 磁链

javdb 页面 `/v/2mrYZq`，4 个磁链：

| 名称 | 大小 |
|:----|:----|
| **CAWB-001-C.torrent** | **7.04GB** ✅ 字幕版（用户要的）|
| CAWB-001-U.无码破解 | 3.18GB |
| CAWB-001 | 6.61GB |
| CAWB-001 | 6.59GB |

注意：CAWB-001 的字幕版是 7.04GB，不是 1.51GB（1.51GB 是 CAWD-001 的字幕版，番号搞错时下的）。

## PikPak CDN URL 获取的坑

`client.get_download_url(file_id)` 返回的是 **dict**（完整文件对象），不是字符串。直接 `url[:100]` 会报 `slice` 错误。正确提取：

```python
result = await client.get_download_url(file_id)
# result 是 dict，含 web_content_link 字段
if isinstance(result, dict):
    url = result.get('web_content_link') or result.get('url') or ''
    if not url and 'medias' in result:
        for m in result['medias']:
            if m.get('link', {}).get('url'):
                url = m['link']['url']
                break
```

## PikPak token 401 刷新

长时间未用后 `file_list()` 报 401。刷新方法：

```python
client = PikPakApi(encoded_token=state['encoded_token'])
client.refresh_token = state.get('refresh_token', '')
# 不设 access_token，触发自动 refresh
await client.refresh_access_token()
# 保存新 token
state['access_token'] = client.access_token
state['refresh_token'] = client.refresh_token
json.dump(state, open('/opt/data/.pikpak_token.json', 'w'))
```

注意：多进程同时刷新会冲突（`invalid refresh token for it may be has been refreshed by other process`），刷新后立即保存，新实例建立时手动设回 access_token 跳过自动刷新。

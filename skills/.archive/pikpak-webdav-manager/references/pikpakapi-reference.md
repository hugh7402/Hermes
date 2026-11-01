# PikPak API 参考（pikpakapi v0.1.11）

库安装：`uv pip install pikpakapi`
Python 路径：`/opt/hermes/.venv/lib/python3.13/site-packages/pikpakapi/`

## 核心类：PikPakApi

### 构造参数

| 参数 | 类型 | 说明 |
|:----|:----|:----|
| `username` | str | 手机号（+86123…）或邮箱 |
| `password` | str | 密码 或 短信验证码 |
| `encoded_token` | str | 编码后的 access+refresh token（替代 username+password） |
| `device_id` | str | 设备标识，不传则自动 md5(username+password) 生成 |
| `httpx_client_args` | dict | httpx.AsyncClient 额外参数 |
| `token_refresh_callback` | Callable | Token 刷新后的回调 |

### 登录流程

```
PikPakApi(username=phone, password=code) → await client.login()
```

- `login()` 内部自动调用 `captcha_init()` 获取 captcha_token
- 手机号格式：`+86` 开头，不含空格或分隔符
- 验证码作为 password 传入（需先通过 PikPak App 获取）

### Token 持久化

```python
# 保存
client = PikPakApi(username=phone, password=code)
await client.login()
token_data = client.to_dict()
json.dump(token_data, open('/path/to/token.json', 'w'))

# 恢复（无需再登录）
client = PikPakApi.from_dict(json.load(open('/path/to/token.json')))
# 此时 client 已包含 access_token 和 refresh_token
```

### 主要方法

| 方法 | 说明 |
|:----|:----|
| `login()` | 登录 |
| `offline_download(url, parent_path)` | 添加磁链/网盘链接到离线下载 |
| `offline_list(page, page_size)` | 列出离线下载任务列表 |
| `offline_file_info(file_id)` | 获取离线文件信息 |
| `offline_task_retry(file_id)` | 重试失败的离线任务 |
| `file_list(parent_path)` | 列出目录内容 |
| `file_rename(file_id, name)` | 重命名文件 |
| `create_folder(name, parent_path)` | 创建文件夹 |
| `delete_tasks(file_ids)` | 删除文件到回收站 |
| `get_download_url(file_id)` | 获取文件下载直链 |
| `get_user_info()` | 获取用户信息 |
| `get_quota_info()` | 获取存储配额 |
| `refresh_access_token()` | 刷新 access_token |
| `decode_token()` | 从 encoded_token 解码 |
| `encode_token()` | 编码为 encoded_token |

### offline_download 详解（⚠️ 用 parent_id 而非路径名）

```python
# 第一步：获取目录 ID
result = await client.path_to_id('/Inbox-JAV')
folder_id = result[0]['id'] if isinstance(result, list) else result

# 第二步：传入 parent_id（不是路径字符串）
result = await client.offline_download(
    url='magnet:?xt=urn:btih:...',  # 磁链或 HTTP 链接
    parent_id=folder_id             # ⚠️ 参数名是 parent_id，不是 parent_path
)
```

返回任务信息 dict，包含 `task_id`、`file_id`、`name`、`file_size`、`message`（进度状态）等。

### 调用注意事项

- 所有方法都是 **async**，需要用 `asyncio.run()` 或 `await`
- 使用的 HTTP 客户端是 `httpx.AsyncClient`，超时默认 10s
- 设备 ID 固定化避免频繁 captcha 验证：`device_id='jav_agent_device_001'`
- 登录后 access_token 有效期 7200 秒，库会自动用 refresh_token 刷新

## 常见错误

| 错误 | 原因 | 解决 |
|:----|:----|:----|
| `Invalid username or password` | 密码/验证码错误或过期 | 重新获取验证码 |
| `captcha_token get failed` | 风控拦截 | 换 device_id 或等一段时间 |
| `PikpakException: username and password or encoded_token is required` | 未传凭证 | 至少传 username+password 或 encoded_token |

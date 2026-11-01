# 实际使用示例：JAV 自动下载智能体

完整的 PikPak API 集成示例：`/opt/data/jav_agent.py`

该脚本展示了：
1. `PikPakApi.from_dict()` — 从缓存 token 恢复会话
2. `client.path_to_id('/Inbox-JAV')` — 获取文件夹 ID
3. `client.offline_download(magnet_url, parent_id=folder_id)` — 添加磁链离线下载
4. `client.to_dict()` — 保存登录状态到文件

## Token 持久化模式

```python
# 首次登录（一次性的）
client = PikPakApi(username=phone, password=password, device_id='my_device')
await client.login()
json.dump(client.to_dict(), open('/path/to/token.json', 'w'))

# 后续使用
state = json.load(open('/path/to/token.json'))
client = PikPakApi.from_dict(state)
# access_token 和 refresh_token 已包含在 state 中
# 如果 access_token 过期，库会自动用 refresh_token 刷新
```

## 关键路径

```
/opt/data/.pikpak_token.json  — 持久化登录状态（含 refresh_token 自动续期）
```

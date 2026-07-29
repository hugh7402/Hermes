# 微信文档入库管道

## 工作流

1. **用户发文件** → 通过微信发文档附件给 Hermes
2. **Hermes 自动缓存** → Gateway 下载并保存到 `cache/documents/`
3. **我收到提示** → 工具系统通知我用户发了文件
4. **实时处理** → 我手动运行 `weixin_ingest.py`
5. **入库完成** → 笔记存入 `01-WeiXin/`，缓存保留在原处

## 脚本位置

```bash
/opt/data/scripts/weixin_ingest.py
```

## 手动运行

```bash
cd /opt/data && python3 scripts/weixin_ingest.py
```

## 文件缓存路径

```
/opt/data/cache/documents/doc_{uuid12}_{原文件名}.ext
```

## 处理过的文件记录

```
/opt/data/Obsidian Vault/Obsidian Vault/.ingested_weixin
```

每行一个 MD5 哈希值。

## 用户偏好（重要）

- **不清缓存**：用户明确要求保留缓存文件，理由是：
  - 万一入库失败可以重试
  - Hermes gateway 本身有 24 小时自动清理机制
  - 文件体积不大，不占空间
- **不设定时任务**：用户要求收到文件后**当场处理**，不等定时
- **不自动删除**：脚本中不要有 `safe_remove()` 之类的清理逻辑

## 常见坑

- **note_enhance.py 的 VAULT 硬编码**：增强微信笔记时必须传**绝对路径**
  ```python
  # ✅ 正确写法
  subprocess.run(['python3', '/opt/data/note_enhance.py', absolute_path], timeout=300)
  ```
- **缓存目录可能为空**：用户第一次发文件前目录存在但空。脚本正常返回 `📭 缓存目录无文档文件`
- **去重日志独立**：`.ingested_weixin` 与 concepts 的 `.ingested` 隔离，互不影响
- **文件名带中文**：wx 文件中文名会被保留在 uuid 后缀中，无需额外处理

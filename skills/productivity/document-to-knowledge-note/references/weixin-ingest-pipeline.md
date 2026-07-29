# 微信实时文档入库管道

## 概要

用户通过微信发送文档文件（docx/pdf/pptx/xls/txt）→ Hermes 自动缓存 → 脚本手动触发 → 入库 + 增强

## 触发方式

- **手动触发**：收到文件后运行 `python3 /opt/data/scripts/weixin_ingest.py`
- 无定时任务（已取消 cron job `9651ca02e14c`）

## 数据流

```
微信文件 → Hermes 缓存（/opt/data/cache/documents/）
         → doc_{uuid12}_{原文件名}.ext
         → weixin_ingest.py
         → 格式转换（同 ingest_docs.py 的转换逻辑）
         → note_enhance.py 增强
         → 01-WeiXin/{标题}.md
```

## 关键配置

| 项目 | 值 |
|------|-----|
| 缓存目录 | `/opt/data/cache/documents/` |
| 目标目录 | `/opt/data/Obsidian Vault/Obsidian Vault/01-WeiXin/` |
| 去重日志 | `/opt/data/Obsidian Vault/Obsidian Vault/.ingested_weixin` |
| 每次最多 | 20 篇（MAX_PER_RUN） |

## 与 WebChat 管道的区别

| 维度 | WebChat 管道 | 微信管道 |
|------|-------------|---------|
| 触发 | cron 定时 9:00 | 手动实时 |
| 数据源 | WebChat BackUp/文档/ | cache/documents/ |
| 目标 | concepts/ | 01-WeiXin/ |
| 缓存清理 | 不清除 | 不清除（保留供重试） |
| 去重文件 | .ingested | .ingested_weixin（独立） |
| 支持格式 | docx/pdf/pptx/xls | 同上 + txt/md |
| 增强 | note_enhance.py | note_enhance.py |

## note_enhance.py 兼容性

`note_enhance.py` 的 `main()` 函数已支持**绝对路径参数**（`Path(f).is_absolute()` 检测）。因此 weixin_ingest.py 可以直接传 `out_path` 的绝对路径，无需切 `cwd`。

## 注意事项

- 缓存文件处理完不删除，Hermes gateway 会在 24h 后自动清理旧缓存文件（`cleanup_document_cache()`）
- 用户只会发文件到 01-WeiXin/ 目录，不会手动编辑
- 本管道和思源同步都调用 note_enhance.py 增强，但 note_enhance 的 `get_all_notes()` 只搜当前笔记所在目录找关联，所以跨目录关联发现不会发生

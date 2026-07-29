# 微信实时文档入库管道

## 概述

用户通过微信发送的文档文件 → Hermes 自动缓存 → 实时处理入库。

## 数据流

```
微信消息（附件文件）
    ↓ Hermes Weixin Gateway 自动下载
/opt/data/cache/documents/doc_{uuid12}_{原文件名}.ext
    ↓ 手动触发（我收到文件后立即运行）
weixin_ingest.py
    ├── 识别文件格式（docx/pdf/pptx/xls/txt/md）
    ├── 转换为 Markdown（同 ingest_docs.py 的转换逻辑）
    ├── 调用 note_enhance.py 增强（传入绝对路径）
    ├── 写入 01-WeiXin/ 目录
    ├── MD5 去重（独立记录 .ingested_weixin）
    └── 缓存文件保留（不清除，供重试和留底）
```

## 脚本

- **路径**：`/opt/data/scripts/weixin_ingest.py`
- **去重记录**：`/opt/data/Obsidian Vault/Obsidian Vault/.ingested_weixin`
- **目标目录**：`/opt/data/Obsidian Vault/Obsidian Vault/01-WeiXin/`

## 与 WebChat 管道差异

| 项目 | WebChat 文档 | 微信实时文档 |
|------|-------------|-------------|
| 触发 | cron 9:00 | **手动即时触发** |
| 缓存 | 不清除 | **保留**（不清除） |
| 目标 | concepts/ | 01-WeiXin/ |
| 去重 | `.ingested` | `.ingested_weixin`（独立） |
| 格式 | docx/pdf/pptx/xls | 同上 + txt/md |

## 知识库位置

`01-WeiXin/` 是知识库三来源之一（concepts/ + 01-WeiXin/ + 00-INBOX/），三者同等参与：
- ✅ note_enhance 增强（YAML frontmatter）
- ✅ 跨目录关联发现（get_all_notes 搜索全部三个文件夹）
- ✅ 检索

## note_enhance.py 绝对路径支持

2026-06-23 修改：`note_enhance.py` 的 `main()` 函数现在支持绝对路径参数（之前只接受 `concepts/` 目录下的文件名）。

```python
# 之前：只接受相对文件名，拼接 VAULT 路径
files = [Path(VAULT) / f for f in args]

# 现在：自动检测绝对/相对路径
for f in args:
    p = Path(f)
    if p.is_absolute():
        files.append(p)
    else:
        files.append(Path(VAULT) / f)
```

## 缓存保留策略

用户明确要求：处理完的微信缓存文件**不要删除**。原因是：
1. Hermes gateway 自有 24h 缓存清理机制
2. 万一入库失败可重新处理
3. 留作原始文件备份

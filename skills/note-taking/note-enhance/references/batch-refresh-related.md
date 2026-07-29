# 批量刷新关联发现

当 `get_all_notes()` 的搜索范围变更后（如新增文件夹、跨目录搜索），已有笔记的 `related` 字段仍按旧范围生成，需要批量刷新。

## 脚本

`/opt/data/refresh_related.py`

## 功能

- 遍历 `concepts/` + `01-WeiXin/` + `00-INBOX/` 所有 `.md` 文件
- 对每篇笔记：**只重新生成 `related` 字段**，不动已有的 `summary` 和 `tags`
- 调用 `note_enhance.py` 的 `get_all_notes()` 和 `discover_related()` 函数
- 每篇间隔 0.5s 防止 API 限流

## 运行方式

```bash
cd /opt/data && python3 refresh_related.py
```

速度约每篇 1.2s，600 篇约需 12-15 分钟。

## 注意事项

- 需要 `note_enhance.py` 在同一目录下（import 依赖）
- 会修改原有文件的 `related` 字段，但保留 `title/date/source/tags/summary` 不变
- 每篇单独调用 API，可能产生约 600 次 API 请求
- 建议后台运行：`nohup python3 refresh_related.py &`

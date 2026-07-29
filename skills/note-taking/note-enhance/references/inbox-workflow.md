# INBOX 自动入库工作流

用户在日常 Obsidian 中新建笔记到 `00-INBOX/`，不经过 WebChat BackUp 文档转换流程，直接增强入库。

## 工作流

```
手动笔记   → 00-INBOX/xxx.md → (cron每天11:00) inbox_scan.py → note_enhance → concepts/xxx.md
思源笔记   → .sy 提取         → (cron每天17:00) siyuan_sync.py → note_enhance → 00-INBOX/doc_id.md (留在原地)
```

## 00-INBOX 双用途

| 用途 | 笔记类型 | 处理时间 | 目标 |
|------|---------|---------|------|
| 手动笔记 | 无 YAML frontmatter | 11:00 | concepts/ |
| 思源笔记 | 已增强（有 YAML） | 17:00 | 00-INBOX/（原地） |

**隔离机制**：`inbox_scan.py` 跳过 `startswith('---')` 的文件，所以思源笔记不会被 11:00 cron 搬走。

## 完整管线调度（四条 cron）

| 时间 | 任务 | 说明 |
|------|------|------|
| 09:00 | 文档入库 | 扫描 WebChat BackUp，转 Markdown + OCR |
| 11:00 | INBOX 增强 | 扫描 INBOX 中无 YAML 的笔记 → concepts |
| 17:00 | 思源入库 | 提取 .sy → 增强 → 00-INBOX |
| 每月1号 09:00 | 知识库巡检 | 断链检测、孤页检查 |

## inbox_scan.py 逻辑

```
1. glob 00-INBOX/*.md
2. 跳过已有 YAML frontmatter 的（思源笔记）
3. for each raw note:
   a. 复制到 concepts/__tmp_{name}
   b. 调用 note_enhance.py __tmp_{name}
   c. 移动到 concepts/{name}
   d. 删除 00-INBOX 源文件
4. 更新 index.md 和 log.md
```

## siyuan_sync.py 逻辑

```
1. 扫描 /opt/data/INBOX_FILES/workspace/data/ 中的 .sy 文件
2. 跳过帮助文档（60+ 篇关键词过滤）
3. 解析 .sy JSON 树 → Markdown
4. 文件名 = 思源 doc_id（英文）
5. → 00-INBOX/{doc_id}.md
6. 复制到 concepts/__tmp_{doc_id}.md（note_enhance 路径限制）
7. 调用 note_enhance.py
8. 增强后搬回 00-INBOX/
9. 更新 index.md 和 log.md
```

## 与文档入库的区别

| | 文档入库 | INBOX 入库 | 思源入库 |
|------|------|------|------|
| 来源 | WebChat BackUp | 手动 Markdown | 思源 .sy 数据 |
| 格式 | docx/pdf/pptx/xls | 已是 Markdown | .sy JSON → Markdown |
| 需要 OCR | 扫描件 PDF 需要 | 不需要 | 不需要 |
| 调度 | 每天 9:00 | 每天 11:00 | 每天 17:00 |
| 目标 | concepts/ | concepts/ | 00-INBOX/ |

## 常见问题

- **note_enhance 超时**：API 偶尔响应慢，`subprocess.run` 的 timeout 设为 300s
- **INBOX 残留**：如果 note_enhance 失败，笔记留在 INBOX 下次重试
- **思源增强失败**：已增强的留在 INBOX，下次 cron 用 `.siyuan_extracted` 去重跳过
- **note_enhance 路径限制**：硬编码 concepts/ 目录，非 concepts 笔记需先 copy 到 concepts 临时处理再搬回

---
name: obsidian
description: Read, search, create, and edit notes in the Obsidian vault.
platforms: [linux, macos, windows]
---

# Obsidian Vault

Use this skill for filesystem-first Obsidian vault work: reading notes, listing notes, searching note files, creating notes, appending content, and adding wikilinks.

## Vault path

已知 vault 路径：`/opt/data/Obsidian Vault/Obsidian Vault/`（双重嵌套，笔记在 `concepts/` 子目录）。

File tools do not expand shell variables. Do not pass paths containing `$OBSIDIAN_VAULT_PATH` to `read_file`, `write_file`, `patch`, or `search_files`; resolve the vault path first and pass a concrete absolute path.

## Read a note

Use `read_file` with the resolved absolute path to the note. Prefer this over `cat` because it provides line numbers and pagination.

## List notes

Use `search_files` with `target: "files"` and the resolved vault path. Prefer this over `find` or `ls`.

- To list all markdown notes, use `pattern: "*.md"` under the vault path.
- To list a subfolder, search under that subfolder's absolute path.

## Search

Use `search_files` for both filename and content searches. Prefer this over `grep`, `find`, or `ls`.

- For filenames, use `search_files` with `target: "files"` and a filename `pattern`.
- For note contents, use `search_files` with `target: "content"`, the content regex as `pattern`, and `file_glob: "*.md"` when you want to restrict matches to markdown notes.

## Create a note

Use `write_file` with the resolved absolute path and the full markdown content. Prefer this over shell heredocs or `echo` because it avoids shell quoting issues and returns structured results.

## Append to a note

Prefer a native file-tool workflow when it is not awkward:

- Read the target note with `read_file`.
- Use `patch` for an anchored append when there is stable context, such as adding a section after an existing heading or appending before a known trailing block.
- Use `write_file` when rewriting the whole note is clearer than constructing a fragile patch.

For an anchored append with `patch`, replace the anchor with the anchor plus the new content.

For a simple append with no stable context, `terminal` is acceptable if it is the clearest safe option.

## Targeted edits

Use `patch` for focused note changes when the current content gives you stable context. Prefer this over shell text rewriting.

## Wikilinks

Obsidian links notes with `[[Note Name]]` syntax. When creating notes, use these to link related content.

## 知识库存储结构

本 vault 使用 LLM Wiki 三层结构（详见 `llm-wiki` skill），当前有三个来源：

```
vault/
├── SCHEMA.md       # 规范定义
├── index.md        # 内容目录
├── log.md          # 操作日志
├── raw/            # 原始文档（不可变）
├── concepts/       # WebChat 文档（615篇）
├── 00-INBOX/       # 思源笔记（3篇）
├── 01-WeiXin/      # 微信实时文档（1篇）
├── entities/       # 实体页
├── comparisons/    # 对比分析
├── queries/        # 查询归档
└── .ingested*      # 去重哈希记录
```

## 三条入库管道

| 管道 | 触发 | 来源 | 目标 | 脚本 |
|------|------|------|------|------|
| WebChat 文档 | 每天 09:00（cron） | `/opt/data/WebChat BackUp/文档/` | concepts/ | `ingest_docs.py` |
| 思源笔记同步 | 每天 17:00（cron） | `/opt/data/INBOX_FILES/`（NAS） | 00-INBOX/ | `siyuan_sync.py` |
| 微信实时文档 | **即时**（手动触发） | `/opt/data/cache/documents/` | 01-WeiXin/ | `weixin_ingest.py` |

详见 `document-to-knowledge-note` 和 `note-enhance` 技能。

## PDF OCR

扫描件 PDF（pymupdf 提取 < 50 字符）自动调用 SiliconFlow Qwen3-VL-8B API OCR。
脚本：`/opt/data/pdf_ocr.py`（无限页数，~3 秒/页）。
注意：EasyOCR 本地 CPU 方案 ~77 秒/页（慢 25 倍），不用于批量处理。

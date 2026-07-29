# 断链修复后处理 — 剩余无效链接

## 场景

`fix_links_v2.py` 跑完后仍剩下约 40-50 处断链（匹配率 ~92%），
这些指向**真正不存在的页面**，无法通过 title→slug 映射自动修复。

## 分类处理策略

### 高引用（≥ 3 篇）→ 创建占位笔记

```python
# 逻辑示例
for target, count in broken.most_common():
    if count >= 3:
        create_placeholder_note(target)
```

典型例子：`[[项目概述-广西]]` 被 16 篇笔记引用 → 创建占位笔记让 wikilink 不再断链。

占位笔记内容：
```
---
title: "项目概述-广西"
date: "2026/07/01"
source: "知识库运维"
tags: [待分类]
summary: ["待补充摘要"]
related: []
---
# 项目概述-广西
> 此笔记由知识库自动创建（16 篇其他笔记引用此页面）。
```

### 低引用（1-2 篇）→ 移除 `[[]]` 保留纯文字

```python
# [[Obsidian]] → Obsidian（去掉链接只留文字）
# [[项目表]] → 项目表
c = re.sub(r'\[\[(target)\]\]', r'\1', content)
```

典型例子：`[[Obsidian]]`、`[[Logseq]]`、`[[思源笔记用户指南]]` 等外部引用，
保留文字让可读性不受影响。

### 不处理的断链特征

- 文件名含乱码字符（如 `[[D23<j*J\\BC...]]`）
- 是软件/工具名引用而非缺失笔记
- 指向外部文档的 wikilink（如思源笔记用户指南）

## 脚本

`/opt/data/skills/productivity/knowledge-base-maintenance/scripts/fix_remaining_links.py`

```bash
cd /opt/data && uv run --with pyyaml python3 skills/.../scripts/fix_remaining_links.py
```

自动完成：分析→高引用建笔记→低引用移除链接。

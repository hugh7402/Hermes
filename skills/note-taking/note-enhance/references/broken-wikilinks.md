# 关联链接断链：标题 vs Slug 不匹配

## 问题

`note_enhance.py` 使用百炼 GLM-5.1 生成 `related` 字段时，wikilink 引用的是**笔记的完整标题**：

```yaml
related:
  - "[[什么是算力银行、算力超市和Token工厂？]]"
```

但 Obsidian 按**文件名 slug** 匹配 wikilink，实际文件名为：

```
算力银行-算力超市-Token工厂.md
```

标题 `什么是算力银行、算力超市和Token工厂？` ≠ slug `算力银行-算力超市-Token工厂` → 断链。

## 规模

实测 533 篇笔记中，511 处 related wikilinks 存在此问题（96% 的关联链接不可用）。

## 修复

`scripts/fix_links.py` 执行以下步骤：

1. 扫描所有笔记，建立 `标题 → slug` 映射表
2. 逐篇读取 `related` 字段中的 wikilink
3. 多级匹配：精确标题 → slug化对齐 → 子串包含
4. 将 `[[标题]]` 替换为 `[[slug]]`
5. 保留 `#heading` 锚点部分

## 修复效果

| 指标 | 修复前 | 修复后 |
|------|--------|--------|
| 断链 | 511 | 21（↓96%） |
| 修改文件 | — | 325 篇 |

剩余 21 处断链指向真正不存在的笔记（未被入库的文档），需手动处理。

## 前置条件

需要 pyyaml：`uv run --with pyyaml python3 fix_links.py`

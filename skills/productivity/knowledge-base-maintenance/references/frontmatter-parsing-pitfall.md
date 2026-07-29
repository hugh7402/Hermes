# Frontmatter 解析陷阱：`---` 在 wikilink 中

## 问题

`lint_vault.py` 原使用 `c.find('---', 3)` 定位 frontmatter 结束位置。
当 frontmatter 的 `related` 字段包含含 `---` 的 wikilink 时（如 `[[产品已形成---数智公司产品认定申报书...]]`），
`str.find()` 会误抓到 wikilink 内部的 `---` 作为 frontmatter 结束标记。

## 后果

- 约 57 篇正常笔记被误报为"缺少 Frontmatter"
- 误报率约占 vault 的 9%
- 前几个版本的巡检报告一直显示"57 篇无 Frontmatter"，导致误以为需要修复

## 修复

改用**按行匹配**，只认行首等于 `---` 的行：

```python
# ✅ 正确做法
lines = content.split('\n')
for i in range(1, len(lines)):
    if lines[i].rstrip() == '---':  # 只匹配整行都是 --- 的行
        fm_text = '\n'.join(lines[1:i])
        break

# ❌ 错误做法
end = content.find('---', 3)  # 会匹配到 [[产品已形成---数智公司...]] 内部的 ---
fm_text = content[3:end]
```

## 影响范围

修复后：
- `lint_vault.py`：`parse_frontmatter()` 函数
- 所有依赖 frontmatter 解析的自动化脚本

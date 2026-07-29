---
name: self-improvement
description: >
  Captures learnings, errors, and corrections to enable continuous improvement.
  Use when: (1) A command or operation fails unexpectedly, (2) User corrects Hermes,
  (3) User requests a capability that doesn't exist, (4) An external API or tool fails,
  (5) Hermes realizes its knowledge is outdated, (6) A better approach is discovered
  for a recurring task.
version: 3.0.21
author: pskoett + Hermes adaptation
tags: [self-improvement, learning, error-tracking, correction]
---

# Self-Improvement Skill

Log learnings and errors to markdown files for continuous improvement.

## Quick Reference

| 场景 | 操作 |
|------|------|
| 命令/操作失败 | 记录到 `.learnings/ERRORS.md` |
| 用户纠正 | 记录到 `.learnings/LEARNINGS.md`（correction） |
| 用户需要不存在的能力 | 记录到 `.learnings/FEATURE_REQUESTS.md` |
| API/外部工具失败 | 记录到 `.learnings/ERRORS.md` |
| 知识过时 | 记录到 `.learnings/LEARNINGS.md`（knowledge_gap） |
| 发现更好的方法 | 记录到 `.learnings/LEARNINGS.md`（best_practice） |

## 初始化

```bash
mkdir -p .learnings
[ -f .learnings/LEARNINGS.md ] || printf "# Learnings\n\nCorrections, insights, and knowledge gaps.\n\n---\n" > .learnings/LEARNINGS.md
[ -f .learnings/ERRORS.md ] || printf "# Errors\n\nCommand failures and integration errors.\n\n---\n" > .learnings/ERRORS.md
[ -f .learnings/FEATURE_REQUESTS.md ] || printf "# Feature Requests\n\nCapabilities requested by the user.\n\n---\n" > .learnings/FEATURE_REQUESTS.md
```

## 脚本

通过终端调用：
- `activator.sh` — 设置学习日志系统
- `error-detector.sh` — 检测错误模式
- `extract-skill.sh` — 从日志提取可复用的技能模板

详见 `scripts/` 目录。
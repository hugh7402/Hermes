---
name: humanize-ppt
description: >-
  AST-based presentation outline director for human-centered PPT workflows.
  Generates structured outlines (Audience-State-Transfer), per-page visual decisions,
  and production briefs for downstream rendering skills. After rendering, runs
  a 3-round "presentation checkup" (演讲体检).
version: 1.0.0
author: LearnPrompt
---

# Humanize PPT

AI 驱动的 PPT 大纲生成工具。接收原始材料（笔记、文档、链接、旧 PPT），
生成**观众状态转移（AST）大纲**，每页决定配图/图表/视频策略，产出生产简报。

## 路径

- 主脚本: `/opt/data/humanize-ppt/scripts/humanize_ppt_v2.py`
- 入口: `cd /opt/data/humanize-ppt && python3 humanize_ppt_v2.py <args>`

## 使用方法

### 生成大纲和生产简报
```bash
cd /opt/data/humanize-ppt
python3 humanize_ppt_v2.py --input <主题或文件> --lang <zh/en>
```

### 输出
- `outline/` — AST 大纲（每页作用 + 内容）
- `brief/` — 生产简报（供下游渲染 skill 消费）
- `qa/` — 演讲体检报告

### 下游渲染
大纲生成后可用以下渲染器之一：

| 渲染器 | 输出 | 场景 |
|:------|:----|:----|
| **frontend-slides** | HTML 幻灯片 | 快速预览/分享 |
| **ppt-master** | 原生 .pptx | 最终交付/继续编辑 |

- frontend-slides: `/opt/data/frontend-slides/` — 渲染 HTML
- ppt-master: `/opt/data/ppt-master-repo/ppt-master-main/` — 渲染真实 .pptx（需加载 ppt-agent skill 了解完整流程）

## 要求
- Python 3.10+
- 纯 Python 标准库（无外部依赖）

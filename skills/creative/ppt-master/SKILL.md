---
name: ppt-master
description: >-
  原生 .pptx 生成引擎 — 从源文档生成真实可编辑的 PowerPoint 文件（DrawingML 形状）。
  使用技能视图加载完整工作流。当用户要求"做PPT"、"生成PPT"或"ppt-master"时触发。
version: 2.11.0
source_repo: /opt/data/ppt-master-repo/ppt-master-main
---

# PPT Master — 原生 PPTX 生成引擎

> ⭐ 33,546 GitHub Stars | MIT License | hugohe3/ppt-master

## 概述

PPT Master 是一个完整的 SVG→PPTX 管线，能将源文档（PDF/DOCX/Markdown/URL）转换为原生可编辑的 .pptx 文件。每个文本框、形状、图表都是真实的 DrawingML 对象，可在 PowerPoint 中直接点编辑。

**核心管线**: 源文档 → 项目初始化 → 设计规范 → 图片获取 → SVG 逐页生成 → 质量检查 → 后处理 → 导出 PPTX

## 关键文件

ppt-master 仓库已安装在 `/opt/data/ppt-master-repo/ppt-master-main/`

| 路径 | 用途 |
|:----|:-----|
| `skills/ppt-master/SKILL.md` | **完整工作流**（719行）— 使用前必须加载 |
| `scripts/svg_to_pptx.py` | SVG → PPTX 导出核心脚本 |
| `scripts/project_manager.py` | 项目初始化和源文件管理 |
| `scripts/finalize_svg.py` | SVG 后处理（图标嵌入/图片裁剪/圆角转路径） |
| `scripts/svg_quality_checker.py` | SVG 质量检查 |
| `templates/layouts/` | 布局模板库 |
| `templates/brands/` | 品牌预设库 |
| `references/` | 设计规范和约束文档 |

## 触发条件

当用户说"做PPT"、"生成PPT"、"制作演示文稿"、"创建幻灯片"且期望输出为 .pptx 文件时加载此技能。

## 与 ppt-agent 的关系

`ppt-agent` 是高层智能体，负责：
1. 需求确认 + 知识库检索
2. humanize-ppt 生成大纲
3. 用户审核大纲
4. **加载本技能执行渲染阶段**（替代旧的 frontend-slides）

当 ppt-agent 进入渲染阶段时，应加载 `ppt-master` 技能并遵循其 `skills/ppt-master/SKILL.md` 管线。

## 脚本路径速查

所有路径相对于仓库根目录 `/opt/data/ppt-master-repo/ppt-master-main/`：

```bash
SKILL_DIR=/opt/data/ppt-master-repo/ppt-master-main/skills/ppt-master
SCRIPTS_DIR=${SKILL_DIR}/scripts
```

| 操作 | 命令 |
|:----|:-----|
| 项目初始化 | `python3 ${SCRIPTS_DIR}/project_manager.py init <name> --format ppt169` |
| PDF 转 Markdown | `python3 ${SCRIPTS_DIR}/source_to_md/pdf_to_md.py <file>` |
| DOCX 转 Markdown | `python3 ${SCRIPTS_DIR}/source_to_md/doc_to_md.py <file>` |
| 导入源文件 | `python3 ${SCRIPTS_DIR}/project_manager.py import-sources <project> <files> --move` |
| SVG 质量检查 | `python3 ${SCRIPTS_DIR}/svg_quality_checker.py <project>` |
| 拆分备注 | `python3 ${SCRIPTS_DIR}/total_md_split.py <project>` |
| SVG 后处理 | `python3 ${SCRIPTS_DIR}/finalize_svg.py <project>` |
| 导出 PPTX | `python3 ${SCRIPTS_DIR}/svg_to_pptx.py <project>` |
| 图片 AI 生成 | `python3 ${SCRIPTS_DIR}/image_gen.py --manifest <project>` |
| 图片搜索 | `python3 ${SCRIPTS_DIR}/image_search.py <query>` |
| 启动预览 | `python3 ${SCRIPTS_DIR}/svg_editor/server.py <project> --live --daemon` |

## 已知陷阱

1. **SVG 必须由主智能体手写** — 不允许用脚本批量生成 SVG（会丢失跨页视觉一致性）
2. **严禁跨阶段打包** — Strategist 阶段不能预写 Executor 的 SVG 代码
3. **每页前必须重读 spec_lock.md** — 确保颜色/字体/图标来自规范文件，而非上下文记忆
4. **图片禁止直接读取** — 所有图片信息来自 `analyze_images.py` 输出，不能直接 open 图片文件
5. **依赖已安装** — python-pptx、Pillow、PyMuPDF、svglib、reportlab 等核心依赖已就绪
6. **模型要求高** — 生成 SVG 质量与模型能力相关，建议使用强文生图能力的模型

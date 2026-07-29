---
name: ppt-agent
description: "一站式 PPT 编写智能体：搜索知识库 → humanize-ppt 生成大纲 → 用户审核大纲 → ppt-master 渲染原生 .pptx。主模型 DeepSeek-V4-Pro（硅基流动），备用 qwen-3.7-max（百炼）。"
version: 2.1.0
author: Emma
created_by: agent
tags: [PPT, 幻灯片, 演示, 大纲]
trigger: 当用户说"编辑PPT"、"编写PPT"、"生成PPT"、"做个PPT"、"做个演示文稿"、"帮我做个关于"、"PPT 制作"、"制作幻灯片"时加载本skill
metadata:
  agent:
    tags: [PPT, 幻灯片, 演示, 大纲, humanize-ppt, ppt-master, 审核流程, 原生PPTX]
    usage_count: 0
requires-skills:
  humanize-ppt: "用于生成 AST 大纲和生产简报"
  ppt-master: "用于渲染原生可编辑的 .pptx 文件"
  obsidian: "用于检索知识库素材"
---
# PPT 编写智能体 (PPT Agent v2)

一站式 PPT 生成工具。输入主题和要求后，自动完成：  
1. 检索 Obsidian 知识库获取素材  
2. 用 humanize-ppt 生成大纲  
3. **你来审核大纲，提修改意见**  
4. 大纲确认后，用 **ppt-master** 管线渲染出原生可编辑的 **.pptx 文件**

> 🆕 **v2.0 更新**：后端从 frontend-slides（HTML 幻灯片）替换为 ppt-master（生成真实 .pptx，每个形状都可在 PowerPoint 中编辑）

## 触发条件

用户说以下内容时加载此技能：
- "写个PPT" / "做个PPT"
- "帮我做个关于...的PPT"
- "生成PPT" / "PPT 制作"
- "做个演示文稿"

## 模型配置

- **主模型**: deepseek-ai/DeepSeek-V4-Pro（硅基流动平台，2.5折优惠）  
  - API: https://api.siliconflow.cn/v1/chat/completions  
  - Key: SILICONFLOW_API_KEY（.env 中）  
  - ⚠️ 生成大纲时需 max_tokens ≥ 8000  
- **备用模型**: qwen-3.7-max（百炼平台）  
  - API: https://dashscope.aliyuncs.com/compatible-mode/v1  
  - Key: BAILIAN_API_KEY（.env 中）  

## 工作流程（6步）

### 第1步：需求确认
与用户确认 PPT 的主题、受众、页数要求、语言（中文/英文）。

### 第2步：知识库检索
搜索 Obsidian 知识库：
- `concepts/` — WebChat 文档（580+ 篇）
- `00-INBOX/` — 思源笔记
- `01-WeiXin/` — 微信文档

使用 `search_files` 按关键词搜索，取最相关的笔记整理素材。

### 第3步：编写源素材文件
将检索到的素材整理成 markdown 文件，保存在：  
`/opt/data/OutPut Box/ppt-YYYYMMDD-HHMM/source.md`  
包含：主题概述、关键信息、数据、引用资料等。

### 第4步：生成大纲预览（humanize-ppt）
用 humanize-ppt 的 `--preview-outline` 模式生成大纲预览：

```bash
cd /opt/data/humanize-ppt
python3 humanize_ppt_v2.py \
  --source /opt/data/OutPut\ Box/ppt-YYYYMMDD-HHMM/source.md \
  --out /opt/data/OutPut\ Box/ppt-YYYYMMDD-HHMM/outline \
  --title "PPT标题" \
  --renderer ppt-master \
  --lang zh \
  --preview-outline
```

### ⭐ 第5步：用户审核大纲（关键环节）
将生成的大纲内容**完整呈现给用户**，包括每页标题和核心要点。

**等待用户反馈**：
- 用户提出修改意见（增加/删减/调整顺序/修改内容）
- 根据意见修改 source.md
- 达成一致后进入第6步

### 第6步：ppt-master 渲染管线
大纲确认后，用 **ppt-master** 管线替代旧的 frontend-slides：

#### 6.1 加载渲染引擎
加载 `ppt-master` 技能，读取完整的 SKILL.md 工作流：
```
skill_view(name="ppt-master")
```

PPT Master 仓库路径：  
`/opt/data/ppt-master-repo/ppt-master-main/`  
Skill 路径：`skills/ppt-master/SKILL.md`

#### 6.2 项目初始化
```bash
SKILL_DIR=/opt/data/ppt-master-repo/ppt-master-main/skills/ppt-master

# 创建项目（16:9 格式）
python3 ${SKILL_DIR}/scripts/project_manager.py init ppt-YYYYMMDD-HHMM --format ppt169

# 导入源素材
python3 ${SKILL_DIR}/scripts/project_manager.py import-sources \
  /opt/data/ppt-master-repo/ppt-master-main/projects/ppt-YYYYMMDD-HHMM \
  /opt/data/OutPut\ Box/ppt-YYYYMMDD-HHMM/source.md \
  --move
```

#### 6.3 Strategist 阶段（设计规范）
- 读取 strategic.md 参考文档
- 呈现「八项确认」给用户：画布格式/页数/受众/风格目标/配色/图标/字体/图片方案
- ⛔ **等待用户确认**后方可继续

#### 6.4 Executor 阶段（SVG 生成）
- 启动实时预览（`svg_editor/server.py --live --daemon`）
- 严格遵循 SKILL.md 规则：逐页手写 SVG，每页前重读 spec_lock.md
- 生成所有页面到 `svg_output/`
- 运行质量检查 `svg_quality_checker.py`

#### 6.5 后处理与导出
```bash
# 拆分演讲备注
python3 ${SKILL_DIR}/scripts/total_md_split.py <project_path>

# SVG 后处理
python3 ${SKILL_DIR}/scripts/finalize_svg.py <project_path>

# 导出原生 .pptx
python3 ${SKILL_DIR}/scripts/svg_to_pptx.py <project_path>
```

输出路径：`exports/<project_name>_<timestamp>.pptx`

### 第7步：输出交付
- 文件路径发送给用户
- 推送微信通知 "PPT 已生成：xxx"
- 可选择通过微信直接发送文件：`MEDIA:/opt/data/ppt-master-repo/ppt-master-main/exports/<project_name>_<timestamp>.pptx`

## 知识库路径

- Vault: `/opt/data/Obsidian Vault/Obsidian Vault/`
- 搜索目录: `concepts/`, `00-INBOX/`, `01-WeiXin/`
- 工具路径:
  - humanize-ppt: `/opt/data/humanize-ppt/`
  - ppt-master 仓库: `/opt/data/ppt-master-repo/ppt-master-main/`
  - 输出目录: `/opt/data/OutPut Box/`

## 用户交互原则

1. **每步都要有输出** — 执行完每一步（检索、大纲、渲染）都要向用户报告结果
2. **大纲审核不跳过** — 必须等用户确认后才能继续到渲染步骤
3. **修改循环** — 用户提修改意见后，回到第4步重新生成大纲预览
4. **设计规范确认不跳过** — ppt-master 的「八项确认」必须等待用户确认
5. **耐心等待** — 审核环节不催促

## 已知陷阱

1. **max_tokens 不足** — DeepSeek-V4-Pro 生成大纲需要 ≥ 8000 tokens
2. **humanize-ppt 需要 markdown 源文件** — 不能直接传主题字符串，必须先准备素材文件
3. **ppt-master 是串行管线** — 严格遵守 SKILL.md 的执行顺序，严禁跳步
4. **SVG 必须手写** — 不允许用 Python 脚本批量生成 SVG 页面
5. **图片不能直接打开** — 所有图片信息从 `analyze_images.py` 获取
6. **渲染阶段耗时长** — 10-15 页的 PPT 可能需要多次迭代，注意 timeout 设置

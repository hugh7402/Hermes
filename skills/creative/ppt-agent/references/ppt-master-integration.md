# PPT Master 集成指南

> 用于 ppt-agent 第8步B：使用 hugohe3/ppt-master（⭐33,546）渲染原生 .pptx 文件

## 路径

```
主目录: /opt/data/ppt-master-repo/ppt-master-main/
SKILL.md: /opt/data/ppt-master-repo/ppt-master-main/skills/ppt-master/SKILL.md
脚本:    /opt/data/ppt-master-repo/ppt-master-main/skills/ppt-master/scripts/
模板:    /opt/data/ppt-master-repo/ppt-master-main/skills/ppt-master/templates/
工作流:  /opt/data/ppt-master-repo/ppt-master-main/skills/ppt-master/workflows/
依赖:    /opt/data/ppt-master-repo/ppt-master-main/requirements.txt
```

## 核心管线

```
源文档 → 创建项目 → [模板选择] → Strategist（8项确认）→ [图片生成] 
→ Executor（逐页 SVG）→ 质量检查 → 后处理 → 导出 .pptx
```

## 启动流程

### 1. 准备源素材

ppt-agent 第1-3步已有 source.md 文件，可直接作为 ppt-master 的输入。

### 2. 创建项目

进入 ppt-master 目录，在 `projects/` 下创建新项目：

```bash
cd /opt/data/ppt-master-repo/ppt-master-main
mkdir -p projects/ppt-YYYYMMDD-HHMM/sources
cp /opt/data/OutPut\ Box/ppt-YYYYMMDD-HHMM/source.md projects/ppt-YYYYMMDD-HHMM/sources/
```

### 3. 读取 SKILL.md 并按管线执行

```bash
# 读取核心工作流
cat skills/ppt-master/SKILL.md
```

严格按 SKILL.md 的步骤串行执行，不得跳过/捆绑阶段。

### 4. Strategist 阶段（需用户确认）

- 读取源素材
- 确认 Eight Confirmations（设计规范 8 项确认）：
  1. 模板选择（预留/自由设计/自定义）
  2. 画布格式（PPT 16:9 / 小红书 / 微信等）
  3. 页数范围
  4. 配色方案
  5. 字体选择
  6. 图片策略（AI 生成 / 网页搜索 / 用户提供）
  7. 是否需要图片
  8. 其他偏好
- **必须等用户确认后才能进入 Executor 阶段**

### 5. Executor 阶段（SVG 生成）

- 逐页生成 SVG（串行，不得批处理）
- 每页生成前必须 `read_file <project>/spec_lock.md` 确保颜色/字体一致
- 每页 SVG 由主会话直接生成（不可委派子智能体）
- 生成完成后自动启动 live-preview（如果可用）

### 6. 后处理和导出

```bash
cd /opt/data/ppt-master-repo/ppt-master-main
python3 skills/ppt-master/scripts/svg_to_pptx.py \
  --input projects/ppt-YYYYMMDD-HHMM/svg_output/ \
  --output exports/ppt-YYYYMMDD-HHMM.pptx
```

### 7. 交付

```bash
cp exports/ppt-YYYYMMDD-HHMM.pptx /opt/data/OutPut\ Box/ppt-YYYYMMDD-HHMM/
```

## 专用工作流速查

| 场景 | 工作流文件 | 说明 |
|:----|:----------|:-----|
| 有现有模板 .pptx 要填内容 | `template-fill-pptx.md` | 直接编辑 PPTX，不进 SVG 管线 |
| 美化现有 PPT（保持内容） | `beautify-pptx.md` | 1:1 页数对应，只改布局 |
| 断点续传（新会话继续生成） | `resume-execute.md` | 进入 Phase B（SVG 生成），跳过 Phase A |
| 先审规范再生成 | `refine-spec.md` | 优化设计规范后继续 |
| 给 PPT 加语音旁白 | `generate-audio.md` | edge-tts 生成逐页音频 |
| 大屏直播预览 | `live-preview.md` | 实时查看 SVG 效果 |
| 品牌规范萃取 | `create-brand.md` | 从已有的品牌素材提炼品牌规范 |
| 视觉自检 | `visual-review.md` | 逐页视觉回看（仅用户要求时执行） |

## 设计模板速查

ppt-master 内置了多种设计风格（在 `skills/ppt-master/templates/` 下）：

- **Glassmorphism** — 玻璃态，半透明图层+渐变，适合 SaaS/科技
- **Swiss Grid** — 瑞士网格，严格模块化布局，适合正式报告
- **Editorial** — 杂志风格，摄影+排版网格，适合品牌展示
- **Data Dashboard** — Bloomberg 风格数据看板，深色主题
- **Memphis Pop** — 孟菲斯风格，明亮色块+几何图案
- **Risograph Zine** — 活版印刷风，双色+手工感

## 模型注意事项

- 主模型 DeepSeek-V4-Pro 可以运行完整管线，但 SVG 设计精细度比 Claude Opus 差一档
- 如果用户要求"高质量设计"/"精致的 PPT"，建议临时切换模型到 Claude
- **不要在 ppt-master 的 SVG 生成阶段切换模型到推理模型**（glm-5.2 等），推理模型不适合 SVG 生成

## 已安装依赖

以下核心依赖已安装（2026-06-28）：

| 包 | 版本 | 用途 |
|:---|:---:|:----|
| python-pptx | 1.0.2 | PPTX 导出（核心） |
| Pillow | 已装 | 图片处理 |
| PyMuPDF | 已装 | PDF 转 Markdown |
| requests | 已装 | HTTP 请求 |
| beautifulsoup4 | 4.15.0 | HTML 解析 |

可选依赖（未安装，按需）：
- edge-tts → 语音旁白
- cairosvg → Office 兼容模式 PNG 回退
- openpyxl → Excel 转 Markdown

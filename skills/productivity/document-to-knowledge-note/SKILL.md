---
name: document-to-knowledge-note
description: Convert office documents (DOCX/PDF/PPTX/XLS) into structured Markdown knowledge notes for Obsidian vault.
version: 1.3.0
---

# Document → Knowledge Note

将办公文档（Word/PDF/PPT/Excel）提取并转化为结构化 Markdown 知识笔记，存入 Obsidian 知识库。

## 自动化流水线（已就绪）

本 skill 已有四条完整的自动化流水线：

### 管道①：WebChat 文档入库（定时 8:00）
```bash
python3 /opt/data/ingest_docs.py
```
- 扫描 `/opt/data/WebChat BackUp/文档/` 及其子目录
- 入库到 `concepts/`
- 每天 8:00 自动（cron `c3e92b82c93a`，每批7个）
- Agent 模式运行（绕过 no_agent 120s 硬超时限制）

### 管道②：思源笔记同步（定时 0:00）\n```bash\npython3 /opt/data/siyuan_sync.py\n```\n- 从 NAS `/opt/data/INBOX_FILES/workspace/data/` 提取 `.sy` 文件\n- 自动转写 `NodeAudio` 语音节点（SenseVoiceSmall API）\n- 入库到 `00-INBOX/`\n- 每天 0:00 自动（cron `5652f5032fe5`）

### 管道③：微信实时文档入库（即时触发）
```bash
python3 /opt/data/scripts/weixin_ingest.py
```
- 用户通过微信发送的文档文件，Hermes 自动缓存到 `/opt/data/cache/documents/`
- **手动触发**（无定时任务）：我收到文件后立即处理
- **入库到 `01-WeiXin/`，不是 concepts/** — 微信直接发送的文件归微信目录，WebChat 备份文档才归 concepts/
- 处理完后**保留缓存文件**（以便失败重试，不清除）
- 独立去重记录：`.ingested_weixin`（与 `.ingested` 分开）

#### ⚠️ 关键陷阱：同一文档双来源（微信 vs 在线文档）

这是最容易犯的错误：
1. 用户先发了一个腾讯文档链接 → 我导出 PDF 走 OCR → 入库到 **concepts/**
2. 用户接着微信发送同一文档的原生 docx 版 → 应该入库到 **01-WeiXin/**
3. ❌ **之前的错误做法**：直接在 concepts/ 覆盖，只改内容不移动位置
4. ✅ **正确做法**：docx 版写入 **01-WeiXin/**，同时从 concepts/ **删除旧版**，更新 `.ingested` hash，重新增强，更新 index.md 中的目录计数

**为什么必须移动而不是覆盖**：concepts/ 对应 WebChat BackUp 自动备份管道，01-WeiXin/ 对应微信实时发送管道。保持来源对应关系才能支持后续去重和审计。

### 管道④：在线文档入库（手动触发）

用户发来的在线文档链接（腾讯文档等），通过 `curl` 导出 API 下载为 PDF → **必须走 OCR 流程**（腾讯文档导出 PDF 是 Canvas 渲染的扫描件，pymupdf 直接提取几乎无文字）。

详见 `references/online-docs-ingest.md`。

### 管道⑤：数据资产文件合集批量入库（定时 6/7/12/13/20 整点）
```bash
python3 /opt/data/scripts/batch_ingest_assets.py
```
- 扫描 `/opt/data/WebChat BackUp/文档/数据资产文件合集/` 及其 16 个子文件夹
- 支持 PDF/DOCX，MD5 去重，OCR 备用
- 每批 7 个文件（Agent 模式运行，无 120s 超时限制），每天 35 个
- 非高峰时段运行（避开 DeepSeek 9-12/14-18 价格翻倍）
- cron `4abd713f8db6`

### 统一增强流程

四条管道入库后都会调用 `note_enhance.py`：
1. 扫描目录中的文档文件
2. 按格式调用对应转换库（docx→python-docx, pdf→pymupdf, pptx→python-pptx, xls→xlrd+openpyxl）
3. 写入 concepts/
4. 调用 `note_enhance.py` 生成规范化 YAML frontmatter（摘要5条×、标签10个、关联[[wikilink]]）
5. MD5 去重，已处理文档自动跳过
6. 每次增强超时 **300s**

**模型选择**：增强调用 `note_enhance.py`，当前使用 DeepSeek 官方 `deepseek-v4-flash`（原名 `deepseek-chat` 别名，0.43s/篇，¥0.005/篇）。详见 `note-enhance` skill。

### Cron 通知策略

cron 任务默认用 agent 模式运行。**cron prompt 中不应包含 SILENT 规则**——否则无新文档时任务虽然正常完成（status: ok），但用户收不到任何通知，会误以为任务没跑。改为：无论是否有新内容，都用中文输出简短执行报告（含执行时间、新入库数量、总笔记数、状态）。

### ⏰ Cron 调度规则（DeepSeek 高峰时段规避）

**DeepSeek 在以下时段价格翻倍**：每日 9:00-12:00、14:00-18:00（北京时间）。

所有 cron 定时任务**必须**安排在非高峰时段：
| 窗口 | 推荐用途 |
|:---:|:---------|
| 0:00-8:59 | 凌晨/早间批量作业（首选） |
| 12:00-13:59 | 午休窗口 |
| 18:00-23:59 | 晚间窗口 |

**规则**：
1. 新增 cron 时优先选非高峰时段
2. 同一时段避免两个 cron 同时启动（防止 DeepSeek 并发限制导致 Broken pipe）
3. 认知负担小的均匀分布优先（如 6/7/12/13/20 比散落在每个整点好记）
4. 所有已有 cron 已按此规则安排，见 `memory` 中的当前 cron 列表

## 工作流

### Step 1: 确定 Vault 路径
```bash
ls -d /opt/data/Obsidian* 2>/dev/null
```
若 vault 路径无写权限，回退到 `/opt/data/知识笔记/`。

### Step 2: 提取各类型文档

| 文件类型 | 工具 | 命令模板 |
|---------|------|---------|
| `.docx` | `python-docx` | `uv run --with python-docx python3 -c "..."` |
| `.pdf` | `pymupdf` | `uv run --with pymupdf python3 -c "..."` |
| `.pptx` | `python-pptx` | `uv run --with python-pptx python3 -c "..."` |
| `.xlsx` | `openpyxl` | `uv run --with openpyxl python3 -c "..."` |
| `.xls` | `xlrd` (fallback) | 旧格式，先试 openpyxl，失败再用 xlrd |

### Step 3: 在线文档处理

1. 判断文档类型（腾讯文档/docs.qq.com 最常用）
2. 用 `curl` 导出 API 下载 PDF：`https://docs.qq.com/doc/{DOC_ID}?download=1&format=pdf`
3. 检查 PDF 文字量：pymupdf 提取 < 50 字 → 走 OCR
4. OCR 提取 → 写入 concepts/

**版本对比**：如果先导出了 OCR PDF 版入库（后几页可能大面积乱码），当用户后续通过微信发送了同一份文档的原生 docx 版：\n1. 提取两种版本全部文字，对比有效字符数\n2. 确定**哪个来源**：docx 是微信发来的 → 写入 **`01-WeiXin/`**（而不是 concepts/ 原地覆盖）\n3. 从 concepts/ **删除**旧 OCR 版（避免重复），更新 `.ingested` hash 记录（旧 PDF hash → 新 docx hash）\n4. 重新运行 `note_enhance.py` 刷新 frontmatter，更新 index.md 中的目录计数\n5. 用户明确指定以哪个版本为准时，遵从其指示

### Step 4: 写入 Obsidian Vault

```bash
write_file path="/opt/data/Obsidian Vault/Obsidian Vault/concepts/<笔记名>.md"
```

## 用户工作规范（必遵守）

1. **出错立即汇报**：遇到错误（超时、路径问题、API 失败等），立即向用户报告错误详情和原因，等待用户指示是否调整方案。不默默跳过、不自行替换方案。
2. **任务结束出总结报告**：所有自动化任务执行完毕后出具完整总结报告，包含：成功/失败数量、耗时、配置变更、剩余待办事项。报告需自包含，让用户一眼看清结果。

## 注意事项

- 中文文件名需在 `ingest_docs.py` 内用 glob 定位，避免终端 shell 引号问题
- `python-docx` 安装在 `/opt/hermes/.venv/bin/python3`，非系统 python3
- **OCR 页数限制已解除**：`MAX_OCR_PAGES=99999`（原 30）。超大扫描件用 `batch_ocr_remaining.py` 手动分批（30页/批，断点续传），详见 `ocr-and-documents` skill
- **XLSX 样式兼容性**：某些政府/企业报送的 .xlsx 文件含旧版样式定义，openpyxl 可能报 `TypeError: expected Fill`。此时用 `zipfile` 直接解析内部 XML 替代。详见 `references/xlsx-stylesheet-incompatibility.md`
- **WeChat 实时管道缓存保留**：处理完后不清除缓存文件
- **PaddleOCR 对培训照片可能输出乱码**，需人工检查 OCR 质量
- **在线文档导出 PDF 需要走 OCR，且质量不可靠**：优先向用户索要原生 docx 版本

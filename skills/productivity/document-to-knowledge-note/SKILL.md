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
3. 检查 PDF 是否扫描件 — **不能只看文字量**，用 PDF 结构探测（见下方"扫描件判定"陷阱）
4. OCR 提取 → 写入 concepts/

**版本对比**：如果先导出了 OCR PDF 版入库（后几页可能大面积乱码），当用户后续通过微信发送了同一份文档的原生 docx 版：\n1. 提取两种版本全部文字，对比有效字符数\n2. 确定**哪个来源**：docx 是微信发来的 → 写入 **`01-WeiXin/`**（而不是 concepts/ 原地覆盖）\n3. 从 concepts/ **删除**旧 OCR 版（避免重复），更新 `.ingested` hash 记录（旧 PDF hash → 新 docx hash）\n4. 重新运行 `note_enhance.py` 刷新 frontmatter，更新 index.md 中的目录计数\n5. 用户明确指定以哪个版本为准时，遵从其指示

### Step 4: 写入 Obsidian Vault

```bash
write_file path="/opt/data/Obsidian Vault/Obsidian Vault/concepts/<笔记名>.md"
```

## ⚠️ 扫描件判定陷阱（2026-08-01 重大事故）

**症状**：某 PDF 提取出 567 字（封面通知文字），旧逻辑 `len(text) < 50` 判为"文字版"跳过 OCR → **27 页正文（扫描图片）一个字都没入库**，笔记只有标题+摘要，正文全丢。

**全库排查结果**：472 个 PDF 中 364 个是扫描件（无文字层/图文混合），**252 个已入库笔记是空壳**（对应 md <3KB，只有 frontmatter 标题，正文丢失）。数据资产/可信数据空间/数字政府白皮书等重量级文档全部中招。

**根因**：`ingest_docs.py` 旧版用 `if not text or len(text) < 50: OCR` 判断。很多扫描 PDF 有少量文字层（封面、通知、结尾），提取出几百字就绕过了 OCR 分支。

**修复**：`ingest_docs.py` 新增 `_pdf_probe()`（PyMuPDF 探测 pages/text_chars/img_pages/text_pages）+ `_needs_ocr()` 结构判定，触发 OCR 的条件（任一）：
- 文字量 < 50
- 页数 >= 3 且总文字 < 800（即使提取出几百字，正文大概率是图）
- 有图片页且 文字页占比 < 50%
- 文件 >= 32MB 且文字 < 2000（大扫描报告全文）

**批量体检脚本**：`/opt/data/scan_pdfs.py` — 全库扫描 PDF，输出 CSV 报告并标注 SUSPECT/EMPTY。复检命令：`cd /opt/data && uv run --with pymupdf python3 scan_pdfs.py`。判定标准：`pages>=3 and (text<800 or img_pages>0 and text_pages/pages<0.5)`。

**回填空壳**：252 个空壳 md 需逐个重新 OCR，覆盖写回。用 `/tmp/pdf_scan_report.csv` 的 SUSPECT 列表驱动批量重跑。

**⚠️ 空壳判定阈值（2026-08-01 修正）**：不能只用绝对大小 `md > 3KB` 判"已完整"——62 页扫描件只提取出 3.8KB 文字层照样是空壳（封面+通知文字）。正确判定：`md >= 3000B 且 md >= pages * 150`（每页不足 150B 即为空壳）。实测按此修正后空壳数从 252 升到 264。

**批量回填脚本 v2（本地 RapidOCR 版）**：`/opt/data/re_ocr_shells.py` — 读 `/tmp/pdf_scan_report.csv` → 对 SUSPECT 且判定为空壳的逐个 OCR 并覆盖写回。**必须用 ocr_venv 的 python 运行**（RapidOCR + pymupdf 都装在那里，不能用 `uv run --with pymupdf`），支持多进程并行、断点续跑：
```bash
cd /opt/data && /opt/data/ocr_venv/bin/python3 re_ocr_shells.py --only "20260731_上海市数据局"   # 单文档重跑
cd /opt/data && /opt/data/ocr_venv/bin/python3 re_ocr_shells.py --workers 4                      # 全量 4 进程并行
cd /opt/data && /opt/data/ocr_venv/bin/python3 re_ocr_shells.py --workers 4 --limit 50           # 先跑 50 个
```
- `--workers N`：并行 worker 数（i3-N305 8 核实测 4 个最优，每个 ~50% CPU）
- 断点续跑：已完成文件记录在 `/tmp/re_ocr_done.json`，中断后重跑自动跳过；脚本内还会按相对阈值 SKIP 已完整的
- 单页 43-67s（dpi=150）；dpi 降到 100 提速不明显（瓶颈在模型推理不在图片大小）
- ⚠️ 旧版 `re_ocr_shells.py` 的 `ocr_pdf()` 是 SiliconFlow API 版（实测 2026-08-01 约 60% 请求 read timeout，27 页跑 18 分钟，251 个文档要 30-40 小时）——v2 已改本地 RapidOCR，全量回填预计 5-8 小时。

### 🚨 OOM 事故与混合架构（2026-08-02 重大教训）

**事故**：`re_ocr_shells.py --workers 4` 跑全量 364 个 SUSPECT 时，在 15GB 内存机器上处理 1000+ 页大文件（《2024数据政策宝典》1019页、《数据资产政策法规汇编》780页等），**4 worker 同时渲染大 PDF 撑爆内存**，进程池子进程被系统 OOM kill，279 个文件全部报 `A process in the process pool was terminated abruptly`（只成功 17 个）。断点只记 OK，所以失败的全都会重跑。

**修复 = 本地/云端混合分工**（两个脚本同时跑，互不重复）：

| 引擎 | 负责文件 | 脚本 | 速度 |
|:---:|:---|:---|:---|
| 本地 RapidOCR | **<50 页**小文件 | `re_ocr_shells.py --workers 2` | ~50s/页 |
| 云端 PaddleOCR-VL-1.5 | **≥50 页**大文件 | `re_ocr_cloud.py --workers 2` | **~10s/页（快5倍）** |

- `re_ocr_shells.py` 已加过滤 `int(r[1]) < 50`（只跑小文件）；`re_ocr_cloud.py` 是新建的云端版，加过滤 `int(r[1]) >= 50`（只跑大文件）。两脚本独立断点（`/tmp/re_ocr_done.json` + `/tmp/re_ocr_cloud_done.json`），互不覆盖。
- **关键：两个脚本不能同时跑同一批文件**——都从同一 CSV 读 SUSPECT 列表，不加页数分工过滤会重复处理并互相覆盖 md。

**云端 PaddleOCR-VL-1.5 实测（2026-08-02，推翻旧的"read timeout 60%"结论）**：
- 单页 ~10s（含 100dpi 渲染 + base64 传输 + API 推理），比本地快 5 倍
- 走代理 `http://127.0.0.1:10808` + 每请求重试 3 次（间隔 5s）后稳定可用，不再 60% timeout
- **base64 传图必须用 Python urllib 读文件**，不能 curl 命令行内嵌 base64（`Argument list too long`）
- 调用：POST `https://api.siliconflow.cn/v1/chat/completions`，model=`PaddlePaddle/PaddleOCR-VL-1.5`，image_url 用 `data:image/png;base64,...`，max_tokens=2000

**DPI 实测（2026-08-02，修正"dpi 降到 100 提速不明显"）**：云端模型 100/120/150dpi 识别字数相当（3775/3604/3682），**100dpi 最快且图片体积减半**（传输更快）。两个脚本的 `get_pixmap(dpi=150)` 均已改 `dpi=100`——对正文识别无影响，大文件还省内存（降低 OOM 风险）。

**SUSPECT 数量 251 vs 364 的解释**：364 是 `scan_pdfs.py` 全量重扫的 SUSPECT 数（判定标准宽：文字页占比 <50% 就算）。251 是之前手动统计的空壳数。**逻辑正确**：SUSPECT ≠ 全部重跑，`process_one` 里 md 已完整（`>=3000B 且 >= pages*150`）的会 SKIP，只有真空壳才 OCR。

### 🔄 OCR 引擎选型（2026-08-02 更新，混合并行）

| 优先级 | 引擎 | 说明 |
|:---:|:---|:---|
| 1️⃣ | **本地 RapidOCR** | `/opt/data/ocr_venv`（rapidocr_onnxruntime）。CPU 单页 5-50s，完全离线/免费/无超时。**负责 <50 页小文件**。安装：`uv pip install --python /opt/data/ocr_venv/bin/python3 rapidocr_onnxruntime pymupdf`。用法：页 `get_pixmap(dpi=100)` 存 png → `RapidOCR()(png)` → 按行拼 text |
| 2️⃣ | 云端 PaddleOCR-VL-1.5（SiliconFlow） | **负责 ≥50 页大文件**（与本地并行，见上方混合架构）。实测 ~10s/页（100dpi + base64 + 代理 127.0.0.1:10808 + 重试3次），比本地快 5 倍。2026-08-01 的"60% read timeout"结论已过时——走代理+重试后稳定。脚本 `re_ocr_cloud.py` |

**规则：批量 OCR 默认本地+云端混合并行（小文件本地、大文件云端），避免 4 workers 全本地 OOM，也不要只开 API 单跑（无代理+重试会 timeout）。**

**验证**：入库后抽查 md 大小——扫描件对应的 md 通常应 >3KB；<1.5KB 的基本是空壳。可用 `stat -c %s` 批量检查。



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
- **扫描件判定与空壳回填**：详见 `references/scanned-pdf-detection-and-backfill.md`（含 `_needs_ocr` 逻辑、`scan_pdfs.py` 体检脚本、264 空壳回填流程）。回填脚本已升级为本地 RapidOCR 版（ocr_venv 运行、多进程、相对阈值判定），见上方"批量回填脚本 v2"

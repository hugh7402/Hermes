---
name: knowledge-base-maintenance
description: "知识库健康运维：断链修复、巡检报告、RSS政策监控入库。覆盖 Obsidian vault 的日常维护和自动化。"
version: 1.1.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [knowledge-base, obsidian, maintenance, vault-health, wikilinks]
    category: productivity
---

# 知识库运维

覆盖 Obsidian 知识库的日常维护、健康巡检和自动化入库。

## 适用场景

- 知识库健康检查（断链、孤立页面、frontmatter 完整性）
- 批量修复 Wikilink 断链
- 政策/行业 RSS 监控自动入库
- **微信文档自动入库**（用户微信发送文件 → Markdown → AI 增强 → 入库到 01-WeiXin/）

## 工具脚本

### 健康巡检

```bash
uv run --with pyyaml python3 /opt/data/lint_vault.py
```

检查维度：
- **断链**：`[[wikilink]]` 指向不存在的页面（🔴 高优先级）
- **Frontmatter 缺失**：无 YAML frontmatter（🔴 高优先级）
- **孤立页面**：零入链的笔记（🟡 中）
- **标签/摘要覆盖**：是否达标（10 标签 + 5 条摘要）

Vault 路径：`/opt/data/Obsidian Vault/Obsidian Vault/`

> ⚠️ `lint_vault.py` 的 `parse_frontmatter` 已改用按行匹配 `---` 结束标记。
> 原 `find('---', 3)` 会误匹配 wikilink 内的 `---`（如 `[[产品已形成---数智公司...]]`），
> 导致 50+ 篇正常笔记被误报为"缺少 Frontmatter"。
> 见 `references/frontmatter-parsing-pitfall.md`。

### 断链修复（推荐 v2 — 内嵌脚本）

```bash
# 推荐 v2 — 纯文本替换，零 YAML 损伤
cd /opt/data && uv run python3 skills/productivity/knowledge-base-maintenance/scripts/fix_links_v2.py
```

原理：建立 title→slug 映射表，直接对 frontmatter 原文做 `[[标题]]` → `[[slug]]` 文本替换，**不经过 yaml.safe_load / yaml.dump**。

**断链根因**：`note_enhance.py` 生成 related 时用的是笔记标题（如 `[[什么是算力银行？]]`），但实际文件名是 slug（`算力银行-算力超市-Token工厂.md`）。Obsidian 按文件名匹配 wikilink，导致不匹配。

**修复率**：实测 442/482（92%），剩余 40 处指向真正不存在的笔记（如 `[[Obsidian]]`、`[[项目概述-广西]]`），需手动处理。

> ⚠️ **不要用老版 `fix_links.py`**：`yaml.safe_load` 将 YAML 中的 `[[标题]]` 解析为嵌套列表 `[['标题']]`，再用 `yaml.dump` 重写 frontmatter 后格式彻底变形，断链不减反增。永远用 v2 的纯文本替换方案。

### 断链修复后处理 — 剩余无效链接

v2 修复后仍有约 40-50 处断链指向**真实不存在的页面**（软件名、外部文档、缺失笔记）。

```bash
cd /opt/data && uv run --with pyyaml python3 skills/productivity/knowledge-base-maintenance/scripts/fix_remaining_links.py
```

策略：
- **高引用（≥3篇）** → 创建占位笔记（如 `[[项目概述-广西]]` 被 16 篇引用）
- **低引用（1-2篇）** → 移除 `[[]]` 保留纯文字（如 `[[Obsidian]]`、`[[Logseq]]`）

详见 `references/remaining-links-strategy.md`。

### 批量 note_enhance 处理未标记笔记

当概念库有大量缺 tags/summary 的新入库笔记时：

```bash
# 自动扫描并处理所有无标签笔记
cd /opt/data && uv run --with pyyaml python3 skills/productivity/knowledge-base-maintenance/scripts/batch_enhance.py
```

⚠️ 文件路径含空格时不能用 `$(cat list)` 传参，必须用 Python subprocess 逐批传递。脚本内已处理好此问题。
详见 `references/batch-note-enhance.md`。

### RSS 政策监控

```bash
uv run --with feedparser --with requests python3 /opt/data/rss_monitor.py
```

当前可用源（中国政府网站大多无 RSS）：
- 新华网-时政：`http://www.xinhuanet.com/politics/news_politics.xml`
- InfoQ-中文：`https://www.infoq.cn/feed`

流程：RSS 抓取 → 全文爬取 → Markdown 保存 → `note_enhance.py` 增强

### 微信文档实时入库

见 `references/weixin-ingest-pipeline.md` 获取完整实作细节。

### 云存储文档入库（PikPak / WebDAV）

当文档存放在 PikPak、NextCloud 等 WebDAV 存储上时，先下载再入库：

```bash
# 下载文件到本地
/tmp/rclone copy "pikpak:/项目资料/方案.docx" /opt/data/cache/documents/ -P

# 然后走标准入库流程
cd /opt/data && python3 ingest_docs.py
```

或 Python 直接操作：
```python
from webdav3.client import Client
c = Client({'webdav_hostname':'http://dav.example.com:80',
            'webdav_login':'user','webdav_password':'pass'})
c.download('/项目资料/方案.docx', '/opt/data/cache/documents/方案.docx')
```

详见 `webdav-storage` skill。

## Cron 作业配置

当前知识库共有 **3 个入库管道 + 1 个巡检**：

| job_id | 任务 | 来源目录 | 目标目录 | 频率 | 模式 |
|--------|------|----------|----------|------|------|
| c3e92b82c93a | 文档入库（WebChat） | `WebChat BackUp/文档/` | `concepts/` | 每天 8:00 | Agent（每批7个） |
| 5652f5032fe5 | 思源笔记同步入库 | NAS `INBOX_FILES/` | `00-INBOX/` | 每天 17:00 | **Agent** |
| f1e56e8511d3 | 知识库巡检 | — | — | 每月 1 号 9:00 | no_agent |
| 4abd713f8db6 | 数据资产文件合集入库 | `WebChat BackUp/文档/数据资产文件合集/` | `concepts/` | 每天 7/9/11/15/17 点 | Agent（每批7个） |

> **数据资产文件合集**：2026-07-01 新增 cron，每次处理 7 个文件（扫描件为主，每文件最长 10 分钟 OCR），5 个时间槽（7/9/11/15/17 点）均匀分配。每个 cron slot 都跑 agent 模式（不用 no_agent，因 120s 硬超时限制），脚本自带 600s subprocess timeout。每天合计 35 个文件，目标 2026-07-11 前清完。详见 `references/ocr-heavy-batch-ingest.md`。

> 注：微信文档管道（01-WeiXin/）无定时任务，收到文件后实时处理。

### 模式选择：no_agent vs Agent

| 维度 | no_agent | Agent |
|------|----------|-------|
| Token 消耗 | 0 | 少量（deepseek-chat ≈ ¥0.0005/次） |
| 超时限制 | **120s 硬限制**（调度器固定，不可配置） | 无（Agent 用 terminal 工具跑脚本，脚本内部 timeout 生效） |
| 适合 | 脚本 ≤ 120s 能完成，无需 LLM | 脚本可能 > 120s（OCR 大 PDF、批量转换），或需 LLM 汇总结果 |
| 脚本位置 | 必须放 `$HERMES_HOME/scripts/`（真实文件，不能用符号链接） | 不限制，prompt 里写全路径 |

**关键坑**：no_agent 的 120s 超时是调度器硬限制。脚本再快的任务也可能因为一次慢文件（83 页扫描件 OCR）被打爆。如果任务稳定超时，果断切 Agent 模式。

### Agent 模式 cron 的写法

```yaml
# 不设 script，用 prompt 说明要做什么
cronjob:
  schedule: "0 9 * * *"
  prompt: "运行 cd /opt/data && python3 ingest_docs.py，循环执行直到无新文档，无论是否有新文档都用中文输出简短执行报告"
  # 注意：no_agent 必须是 false（默认）
```

### 微信文档实时入库

**原理**：用户在微信端向 Hermes 发送文件附件 → Hermes gateway 自动下载并缓存到 `cache/documents/`（文件名格式 `doc_{uuid12}_{原文件名}.ext`） → **我在对话中实时运行** `weixin_ingest.py` → 转换 Markdown → note_enhance 增强 → 入库到 `01-WeiXin/` → **缓存文件保留不删除**（防止入库失败需要重试，且 Hermes gateway 自带24小时清理机制）。

**脚本**：`/opt/data/scripts/weixin_ingest.py`

**关键逻辑**：
- 使用独立的 hash 日志 `$VAULT/.ingested_weixin` 去重（与 concepts/ 的 `.ingested` 隔离）
- 处理完成后**保留缓存文件不删除**（用户明确要求）
- 调用 `note_enhance.py` 时**传绝对路径**（note_enhance 已支持，见下面说明）
- 支持格式：docx, pdf, pptx, xls/xlsx, txt, md（同 concepts/ 管道）
- 每次最多处理 `MAX_PER_RUN = 20` 个文件

**微信文件缓存路径**：`$HERMES_HOME/cache/documents/`（本环境为 `/opt/data/cache/documents/`）

**与 concepts/ 管道的区别**：

| 维度 | concepts 管道 | 01-WeiXin 管道 |
|------|-------------|---------------|
| 来源 | `WebChat BackUp/文档/`（微信自动备份目录） | `cache/documents/`（实时聊天附件缓存） |
| 处理方式 | 保留原始文件（备份目录不动） | **保留缓存文件不删除** |
| 去重日志 | `.ingested` | `.ingested_weixin` |
| 触发方式 | 定时 9:00 cron | **实时**（我收到文件当场处理） |

Agent 模式会消耗少量 token 来驱动 terminal 调用，但脚本内部自己控制 timeout，300s/400s 的 subprocess timeout 不会被截断。

### 批次限制与均匀分配

`ingest_docs.py` 每次最多处理 7 个文件（`MAX_PER_RUN = 7`），避免单个执行被慢文件（OCR、加密 PDF）拖垮超时。

`batch_ingest_assets.py` 每次处理 7 个文件（`PER_RUN = 7`），由 cron 均匀分配到 7/9/11/15/17 五个时间档。

**均匀分配原则**：当有多个 cron 槽位处理同类任务时，不要一个槽位处理 20 个而其他槽位只处理 3 个。每批数量应保持一致，避免单次执行时间过长导致超时或用户抱怨等待。修正：将所有槽位的每批文件数统一为同一个值。

实现方式：
```python
MAX_PER_RUN = 7  # 统一每批数量
unprocessed = [f for f in docs if not is_already_processed(str(f))]
for f in unprocessed[:MAX_PER_RUN]:
    ...
```

### 扫描件 PDF 大批量入库

当 `WebChat BackUp/文档/` 下新增大量扫描件 PDF（如 314 文件中 78% 为扫描件）：

1. 先**快速扫描**区分文本型 vs 扫描件（参考 `references/ocr-heavy-batch-ingest.md`）
2. 文本型批量入库，每次 20 个
3. 扫描件分批处理（每批 3~5 个，较长超时）
4. 超大扫描件自动跳过（hash 写入 `.ingested`）

详见 `references/ocr-heavy-batch-ingest.md`、`references/large-batch-ingest-pattern.md`。

## 常见陷阱

- **🚨 yaml.safe_load + yaml.dump 破坏 wikilink 格式**：不要用 `yaml.safe_load` 解析含 `[[wikilink]]` 的 frontmatter。YAML 将 `[[标题]]` 视为嵌套列表 `[['标题']]`，dump 后变成 `- ['标题']`。修复 v2（scripts/fix_links_v2.py）用纯文本 regex 替换避免此问题。
- **巡检脚本显示断链数字偏高**：lint_vault.py 在用 `yaml.safe_load` 解析时的显示层问题，不影响文件。
- **修复脚本修改大量文件**：`fix_links.py` 会重写所有含 related 字段的笔记。跑之前确保没有未提交的修改。
- **政府网站无标准 RSS**：国家数据局、民政部、发改委等官网均无 RSS 输出。新华网是目前唯一可靠的政策 RSS 源。如需覆盖特定部委，考虑网页爬取方案。
- **no_agent cron 脚本依赖**：Python 依赖（pyyaml、feedparser 等）未全局安装时，用 shell 包装脚本通过 `uv run --with <pkg>` 解决。脚本放 `/opt/data/scripts/`，**必须是真实文件**不能用符号链接（调度器会解析到外部路径并拦截）。
- **OCR 超大 PDF 跳过策略**：`MAX_OCR_PAGES` 已从 30 改为 99999（取消页数限制）。但 >80 页的扫描件 PDF（如培训照片、案例集 >300 页，200 页蓝皮书）会在 400s subprocess timeout 内未完成全部 OCR。这些文件**直接跳过**（hash 写入 `.ingested`），不做截断入库。手动手动处理方案：单独跑 `python3 pdf_ocr.py <path>` 并加更长 timeout，或分段 OCR。
- **symlink 陷阱**：`ln -sf` 创建的链接在 cron 沙箱中会被解析到真实路径，若超出 `/opt/data/scripts/` 范围则被拦截。用 `cp` 复制真实文件。
- **WeChat 限流误报**：`last_status: "error"` 可能只是微信发送被 iLink rate limited，脚本本身成功执行了。看 `agent.log` 中 `Job 'X': delivered to weixin` 确认脚本跑完；看 `errors.log` 中 `iLink sendmessage rate limited` 确认是发送层的问题。不要因为 status=error 就重跑脚本。
- **Agent 模式 cron 的 SILENT 陷阱**：不要在 cron prompt 里写类似"无新文档时输出 `[SILENT]` 以静默"的规则。即使无新内容，用户也需要知道任务正常执行了（执行时间、状态、无新文档确认）。否则用户会以为任务没跑。正确做法：**无论是否有新内容，都输出简短的中文执行报告**（包含执行时间、新入库数量、总数、状态）。
- **📛 多 cron slot 的分配不均衡**：同一类任务的多个 cron 槽位，每批文件数应保持一致。一个槽位塞 20 个文件而其他槽位只跑 3 个，会导致单个槽位执行时间过长（尤其 OCR 密集型任务），用户会认为分配不合理。修正：计算剩余文件数 ÷ 槽位数，每个槽位承担相同的文件数。
- **加密 PDF 拖垮批处理**：pymupdf 的 `len(doc)` 对加密 PDF 返回正确页数，但 `doc[i]` 抛 `ValueError("document closed or encrypted")`。单文件崩溃会导致整个 cron 超时。OCR 脚本（`pdf_ocr.py`）必须用 try/except 逐页防御。
- **微信文档缓存可能为空**：如果用户从未通过微信发送过文件附件，`cache/documents/` 目录存在但为空。脚本正常退出返回 `📭 缓存目录无文档文件`。这不是错误。
- **note_enhance.py 的 VAULT 硬编码**：`note_enhance.py` 的 `VAULT` 变量固定为 `concepts/` 目录。当微信入库脚本需要增强 `01-WeiXin/` 中的笔记时，必须传**绝对路径**给 note_enhance。note_enhance 的 main() 已支持绝对路径参数（`if p.is_absolute(): files.append(p)`）。调用示例如下而非使用 cwd：
- **⚠️ summary 字段含 ASCII 双引号导致 YAML 解析失败**：`build_frontmatter()` 用 `f'  - "{s}"'` 包装摘要条目，若 `s` 中本身含 ASCII `"`（如中文引用的标题 `"数据二十条"`），YAML 会将内容中的 `"` 误判为标量结束符，抛出 `while scanning a quoted scalar` 解析错误。修复：确认 YAML 格式后再写入，或改用单引号 `f'  - ''{s}'''`（注意单引号内不支持转义）或 YAML 块标量。受影响文件需重建 frontmatter。
- **📛 文件名特殊字符（中文括号、空格）截断 shell 命令**：`$(cat list)`, `xargs`, 和 shell glob 展开会按空格/括号分词。例如 `【三件套】技术架构.md` 会被拆成 `[三件套]技术架构.md`。**必须用** Python `subprocess.run([...] + batch)` 逐批传参数列表，避免 shell 分词。`scripts/batch_enhance.py` 已内嵌此处理。`ingest_docs.py` 的 `Path(BACKUP_DIR).glob('**/*')` 不受影响（纯 Python glob）。\n- **📛 空 PDF 文件导致 pymupdf EmptyFileError**：零字节的 .pdf 文件（如文件名相同但带有 `-1` 后缀的重复副本）会使 `fitz.open()` 抛出 `EmptyFileError`，直接中断批处理。在 `convert_to_markdown()` 的 `try/except` 中应检查文件大小 `os.path.getsize() > 0` 后跳过并记录 hash，避免重复尝试。
  ```python
  subprocess.run(['python3', '/opt/data/note_enhance.py', absolute_path], timeout=300)
  ```

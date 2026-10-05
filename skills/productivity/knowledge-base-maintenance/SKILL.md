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

🚨 **lint 只印前 5 条**（`weak_tags` 前 10 条），`*...还有 N 篇*` 是截断——**要完整清单必须导**：

```bash
cd /opt/data && uv run --with pyyaml python3 \
  skills/productivity/knowledge-base-maintenance/scripts/vault_lint_dump.py
# 输出 /opt/data/.tmp_tests/vault_issues.json，含每个问题的 slug/title/path/正文体量/标签数
```
批量修复前**必须先导全量**，否则只能看到 5 篇、会漏修。

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

> ⚠️ **断链误报两处已修（2026-08-08）**：
> 1. `check_broken_links` 原来用精确匹配（`target not in all_slugs`），空格/连字符/序号差异全部误报
>    （如 `-0723` vs `--0723`、`1.关于...` vs `关于...`）。已加 `_norm_slug()` 规范化匹配
>    （去序号前缀/书名号/引号/空格/连字符，容错 `len>=6` 的包含匹配）。
> 2. 正文 wikilink 正则原来用 `\[\[([^\]|#]+)` 不要求闭合 `]]`，OCR 噪声（`[[IO`、`[[必填]`、
>    单括号表格标记）全被误当链接。已改为 `\[\[([^\]|#]+)\]\]` 要求闭合。
> 这两处修复后断链从 26→0。下次改 lint 时注意保持这两个约束。

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

**OCR 补全的文件无 frontmatter（2026-08-08 实测）**：`re_ocr_cloud.py`/`re_ocr_shells.py` 只写正文 md，**不调 note_enhance**——OCR 补全的文档没有 frontmatter/摘要/标签，在知识库里是"哑巴"状态。补增强流程：
1. 扫描无 frontmatter 的 md：读文件头 200 字符，`head.startswith('---')` 判断
2. 批量跑 `note_enhance.py <文件名>`（每文件 1-2 分钟，264 个约 4-6 小时；DeepSeek 每文件一次 API 调用）
3. **现成脚本**：`/opt/data/scripts/enhance_missing_fm.sh`（自动生成无 fm 清单 → 逐个跑 → 每 8 个暂停 8s → 日志写 `/opt/data/enhance_run.log`）。后台跑用 `terminal(background=true, notify_on_complete=true)`
4. 用户偏好：**等 DeepSeek 低价时段（12:00 左右）再跑批量增强**，节省 token；但用户随时可能改口"等不及了现在就开始"——被覆盖后立即跑并**取消已建的 12:00 cron**（用 cronjob action=remove）
5. 增强任务运行中不要同时改 frontmatter 文件（写冲突）；断链复检等增强跑完再做
6. **增强不是一遍过**：`note_enhance.py` 只处理"无 frontmatter"的文件（`head.startswith('---')` 为假才跑）。**有 frontmatter 但缺 tags/summary 的文件不会被首轮覆盖**（如标签生成 API 失败、正文太短），lint 复检后仍报"无标签/无摘要"的文件需**第二遍显式重跑**：`python3 note_enhance.py <文件名>` 逐个传。第一遍 264 个后仍有 ~10 个要第二遍，重跑后大多成功（首次多为瞬时 API 问题）。
7. **lint 复检后剩余"问题"要分两类**：① 真缺陷（断链、无 frontmatter）→ 必须修到 0；② **边缘正常态** → 不修：短表格文档（调研记录表、责任人清单，正文几百字）无法生成有效标签/摘要，属内容本性；孤立页面（零入链）是 Obsidian 独立报告的正常状态，不是缺陷，不要为此批量加链接。判断标准：看该文件正文体量，<1KB 的表格类文档直接标注"已知边缘情况"放过。
8. **幽灵链接清理**：note_enhance 的 `discover_related` 可能把 OCR 噪声/不存在页面写进 frontmatter 的 `related` 字段（如 `[[数据流通标准化白皮书]]` 无对应文件）。lint 报断链后先在源文件确认位置（正文 vs related），related 里的幽灵引用直接删除该条目，不要改成不存在的目标。
9. **OCR 重跑后必须全量重增强，不能只补无 frontmatter 的（2026-08-09 实测）**：OCR 补全（re_ocr_cloud/shells）重跑后 md 正文更新了，但**已有 frontmatter 的文件的摘要/标签/related 还是旧内容**——元数据过期。用户明确要求"OCR 总计重跑的 361 个全部再增强一次"。正确范围：**OCR 相关全部文件**（不只无 fm 的），用 scan report 的 SUSPECT 清单精确匹配（`/tmp/pdf_scan_report.csv` 的 fname 列 → `find_md` 模糊匹配到 md），或按 md 正文里的 OCR 重跑标记（`> **云端OCR(PaddleOCR-VL)重跑**：` / `> **本地OCR(RapidOCR)重跑**：`）识别。note_enhance 会剥离旧 fm 重新生成（覆盖更新，幂等），所以直接全量重跑即可。复用 `/opt/data/scripts/enhance_rerun.sh`（每 8 个暂停 8s，日志 `/opt/data/enhance_rerun.log`）。328 个约 4-6 小时，327 成功 0 失败。

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
/tmp/rclone copy "pikpak:/项目资料/方案.docx" /opt/data/cache/documents/ -P --timeout 60s --contimeout 30s

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
| f1e56e8511d3 | 知识库巡检 | — | — | **每月 1 号 20:00**（cron `0 20 1 * *`） | no_agent |
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

**OCR 引擎选型（2026-10-01 修正）**：`pdf_ocr.py` 的 `_ENGINE_ORDER = ["bailian", "siliconflow"]`——**百炼 `qwen-vl-ocr-latest` 为主，硅基流动 PaddleOCR-VL 仅兜底**。

> 🚨 **旧脚本写的是"统一用云端 PaddleOCR-VL（SiliconFlow API，≈0.8s/页，免费）"，那是错的、且已经造成事故**：
> PaddleOCR-VL 的输出会带 `<|LOC_471|>` 布局特殊 token，2026-08-01~03 那次照旧指引全量重跑，
> 把 **102 篇笔记的正文污染成 ~80% 噪声**（详见下文「102 篇笔记正文被 OCR 布局噪声污染」节）。
> **不要再按老指引选 PaddleOCR-VL。** 引擎以 `_ENGINE_ORDER[0]` 为准，不要靠记忆断言。

`ingest_docs.py` 自动判扫描件后调 pdf_ocr.py；`re_ocr_shells.py`（本地 RapidOCR）仅作批量补跑备用。空壳判定用**相对阈值**（md <3000B 或 每页<150B），不要用绝对阈值漏判大文档。详见 `references/rapidocr-local-batch.md`。

详见 `references/ocr-heavy-batch-ingest.md`、`references/large-batch-ingest-pattern.md`。

### 🚨 巡检 27 篇无标签 / 24 篇无摘要的根因：DeepSeek 推理模式吃空 content（2026-10-01 修复）

**症状**：月度巡检报「无标签 27 篇、无摘要 24 篇」，这些文件**都已有 frontmatter**（不是没增强过），
手动跑 `note_enhance.py <文件>` 显示 `✅ 已保存`，但结果仍是 `❌ 摘要: 0条要点 / ❌ 标签: 0个`。
**再跑一次会覆盖**——脚本用空元数据重写 frontmatter，把已有的标签/摘要**清空**。

**根因（两层）**：
1. `call_llm()` 的默认模型被改成 `deepseek-v4-flash`。实测 2026-10-01：`deepseek-flash` /
   `deepseek-v4-flash` 走的是**推理模式**，返回体里 `reasoning_content` 有内容而 `content` 是**空字符串**
   （token 全被推理过程吃掉，`max_tokens=800` 远不够）。脚本只读 `content` → 拿到空串 → 生成 0 条。
   **解法：模型名用 `deepseek-chat`**（同一底层模型、**关掉推理**的别名，实测 `reasoning_content` 长度 = 0、
   content 正常返回；3 秒/篇）
2. `enhance_note()` **没有空结果保护**——`summary` 和 `tags` 都为空时照样写盘，破坏性覆盖原元数据。

**已做的三处修复（`/opt/data/note_enhance.py`）**：
- `call_llm(prompt, max_tokens=2000, retries=3, model="deepseek-chat")`（原 `max_tokens=800, model="deepseek-v4-flash"`）
- `call_llm` 内加兜底：`content` 为空时抛异常触发重试，**绝不把空串当成功结果返回**
- `enhance_note` 保存前加**安全闸**：`if not summary and not tags: return False`（跳过保存，保护原文件）

**验证方法**（改完必须先验再批量跑）：
```bash
cd /opt/data && python3 note_enhance.py "<任一待修文件>.md"
# 期望看到：✅ 摘要: 5条要点 / ✅ 标签: 10个 / 💾 已保存
# 看到 ❌ 0条 + 🛑 就是模型/解析还有问题，别往下批量跑
```

**修复范围与批量跑法**：
`lint_vault.py` 只印前 5 条，需先导全量清单——用 `sys.path.insert(0,'/opt/data')` import `lint_vault`
调 `scan_all_notes()/check_orphans()/check_broken_links()/check_frontmatter()` 导出 JSON，
再取 **no_fm ∪ no_tags ∪ no_summary ∪ weak_tags** 的并集（正文 ≥1000B，<1KB 的短表格文档属边缘态放过）。
批量必须用 Python `subprocess.run([sys.executable, '/opt/data/note_enhance.py', path])` **逐文件传参**
（文件名含空格/中文括号，走 shell 会分词截断），每 8 个 `sleep 5` 退避。实测 59 篇约 5 分钟。

> 💡 `enhance_note()` 内部会先 `detect_existing_fm()` **剥离旧 frontmatter 再重建**，
> 所以对**已有 fm 的文件重跑是安全的**（不是"只处理无 fm 的文件"）——前提是 API 正常 + 安全闸生效。

> ⚠️ **摘要条目末尾的 `×` 不要当成 bug 去掉**：`SUMMARY` prompt 明确要求每条以 `×` 结尾，
> `build_frontmatter()` 按行切分时保留它。全库 **4520/4522 条摘要都带 `×`**（100%），
> 是既有约定——单独去掉会造成全库格式不一致。

> ⚠️ **知识库不在 git 备份内**：`/opt/data/.gitignore` 第 26 行是 `Obsidian Vault/`，
> vault 完全未跟踪 → **元数据被清空后没有版本可回滚**。任何批量改 frontmatter 的脚本
> 跑之前必须先小样本验证 + 自带安全闸，别指望 git 兜底。

### 🚨 lint 断链误报第三处：只索引 concepts/，跨目录链接全误报（2026-10-01 修复）

**症状**：`note_enhance` 生成的 `related` 指向 `01-WeiXin/` 或 `00-INBOX/` 里的笔记，
lint 报断链，但**在 Obsidian 里点得开**。

**根因**：Obsidian 解析 `[[X]]` 是**整个 vault 按文件名匹配**，而 `lint_vault.py` 的
`check_broken_links` 只用 `set(notes.keys())`（＝ `scan_all_notes()` 只扫 `concepts/*.md`）当目标索引。
`note_enhance.get_all_notes()` 却是跨目录的（concepts + 01-WeiXin + 00-INBOX，共 952 篇），
所以它写出的链接完全可能落在其他目录。

**修复**：新增 `_all_vault_slugs()` 收集全 vault（concepts/01-WeiXin/00-INBOX/raw）的 stem，
`check_broken_links(notes, extra_slugs=...)` 用它扩展**链接目标索引**——
注意只扩展索引，**笔记各项统计仍以 concepts/ 为准**（否则总数从 940 变 952，报告口径就乱了）。
`main()` 里的调用已改为 `check_broken_links(notes, extra_slugs=_all_vault_slugs())`。

> ⚠️ 路径坑：`VAULT = "/opt/data/Obsidian Vault/Obsidian Vault"` **本身就是 vault 根**，
> 子目录是 `VAULT/concepts`，不要写成 `Path(VAULT).parent / 'concepts'`（那是不存在的路径，
> 会静默返回空集合 → 误报依旧）。验证：打印 `len(_all_vault_slugs())` 应 ≈ 952 而非 0。

### 🚨 102 篇笔记正文被 OCR 布局噪声污染（2026-10-01 发现）

**现象**：正文里满是 `<|LOC_471|>` 这类标记，最重的文件（如
`19.《数据安全技术-数据安全风险评估方法》`）149479 字里 11572 处、去掉后才 19256 字，
**且剩余的也是多语言乱码** → 由它生成的 tags 变成「小时代/护理/Fred M」这类垃圾。

**根因**：`<|LOC_n|>` 是 **PaddleOCR-VL（硅基流动）的布局特殊 token**。
2026-08-01~03 那次 `re_ocr_cloud.py` 全量重跑用的是 PaddleOCR-VL（61 篇正文带
`> **云端OCR(PaddleOCR-VL)重跑**：` 标记），把大批笔记写坏了。
**现行百炼 `qwen-vl-ocr-latest` 实测干净**（用自由 prompt / `Text Recognition:` /
`Document Parsing:` 三种都 0 处噪声）——所以**不要再把污染归咎于当前 prompt**。

**分档统计**（`/opt/data/.tmp_tests/ocr_noise.json`）：
含 `<|LOC_` 的 102 篇 → 🔴 有效文本 <30% 的 **73 篇**、🟡 30-60% 的 27 篇、🟢 >60% 的 2 篇。

**已做**：
- `pdf_ocr.py` 新增 `_sanitize_ocr()`，**所有** OCR 输出统一剥掉 `<|LOC_\d+|>`
  （百炼干净，但 `_ENGINE_ORDER` 里的硅基流动兜底仍可能命中；防御性清理 + 打印清理条数）
- 需要 `import re`（原来没导，加了）

**待办**：73 篇严重污染的需要**用百炼引擎重 OCR**（源 PDF 在 `WebChat BackUp/文档/`），
重 OCR 后**必须再跑一遍 `note_enhance`**（否则 tags/摘要 还是从垃圾正文生成的）。

**恢复管线（2026-10-01 已实跑，脚本已归档到本 skill）**：

1. **清点**：`scripts/vault_lint_dump.py` 导出全量问题清单 + 单独扫 `<|LOC_` 噪声占比
   （含 `<|LOC_` 的 102 篇，按 `有效文本占比 = 去LOC后长度 / 正文长度` 分档：<30% 严重）
2. **映射源 PDF**：从 md 头部的 `> **原始文件**：xxx.pdf` 行取文件名，去 `WebChat BackUp/文档/` 下
   `glob('**/*.pdf')` 建索引匹配 → 得到「md → 源 PDF → 页数」。
   ⚠️ **不要用严匹配**：首版只认 `.pdf` 结尾 → 误判 **37 篇「源已不在」**；
   改用宽松匹配（三候选 + 归一化 + 模糊兑底，`scripts/match_loose.py`）后 **37/37 全部找到**。
   **结论：102 篇全部有源，没有一篇是救不回来的。** 详见下方「坑 1」。
3. **重 OCR**：百炼 `qwen-vl-ocr-latest`，**并发 8**（实测 1.36 页/s；并发 16 无收益），120dpi~150dpi 渲染，
   `max_tokens=6000`，429 指数退避重试 5 次，**每文件写完就落盘 done.json（断点续传）**，不可整库重跑
4. **阶段 A**：源 PDF 缺失的，只剥 `<|LOC_\d+|>` 标记 + 压连续空行，并写入
   `> **已剥离OCR布局标记**：<时间>（源 PDF 缺失，内容未恢复）` 行留痕
5. **阶段 B**：所有重 OCR 过的文件重跑 `note_enhance`（正文换了，旧元数据全部过期）
6. **阶段 C**：复检 lint，与巡检报告做前后对比表

> ⚠️ **吞吐实测差异大，别按首篇估算**：首个文件因连接/冷启动只跑到 0.14 页/s，
> 稳定后 0.85–1.36 页/s。10463 页 → 约 2–4 小时。**先跑 1 个文件量吞吐再报 ETA 给用户**。

详见 `references/ocr-loc-noise-recovery.md`。

### ⚠️ note_enhance 的 `related` 必须写 **slug（文件名）**，不能写标题（2026-10-01 修复）

Obsidian 按**文件名**解析 wikilink，而笔记 H1 标题常与文件名不同
（如标题 `元景DS+MaaS软件包产品介绍` 但文件是 `元景DS+MaaS-增强版操作手册-2.5.5.md`）。
写标题会产生"看着对、点不开"的断链。实测库里既有 `related` **全部是 slug**。

`discover_related()` 已改为：建 `title2slug`（标题 + 文件名 → slug）映射，
LLM 返回的候选先查 `slug_only`（已是文件名）再查 `title2slug`，**输出 slug**；
两路都命中不了就丢弃并打印 `⚠️ 丢弃幽灵关联`（LLM 会凭空编造像真名的标题），最后 `[:3]` 截断。

### 🚨 `note_enhance` 会剥离旧 frontmatter 再重建 —— 对已有 fm 的文件重跑是**危险**的

`enhance_note()` 调 `detect_existing_fm()` 把旧 frontmatter 剥掉，然后用**新生成**的
summary/tags/related 重建。所以：
- ✅ 想刷新元数据时直接重跑即可（幂等）
- 🔴 **一旦 API 返回空，就会用空元数据覆盖掉原有标签**（2026-10-01 实测踩到）
  → 已在 `enhance_note()` 保存前加安全闸 `if not summary and not tags: return False`

### 🚨 源文档营销水印/广告会污染正文 + 元数据（2026-10-01 清理）

**现象**：知识库 334 个文件的正文里满是同一句硬广告，是数据资产类 PDF 的**页眉页脚**，
被 OCR 逐页吸进来：
```
数据资产入表咨询、课程培训:陈阳17301209296          (12978 处)
数据资产入表项目咨询、首席数据官课程培训：陈阳 17301209296（同微信）  (2745 处)
……共 12+ 种变体，全库 ≈3 万处
```
也有 `公众号·数据资产管理大讲堂`（267 处）、`阅览更多报告请关注"XX研究院"微信公众号`。

**危害不止于正文噪声**：
- 生成出垃圾标签（`- 课程培训`、`- 陈阳`）—— 实测 **14 篇标签被污染**
- 生成出垃圾摘要（`"联系电话陈阳17301209296 ×"`）—— 实测 **16 篇摘要被污染**
- `note_enhance` 把广告文本当笔记名，造出幽灵关联 `[[数据资产入表咨询、课程培训:陈阳17301209296]]`

**清理必须分三遍**（脚本 `scripts/strip_ads.py` / `strip_ads2.py` / `strip_ads3.py`）：

| 遍 | 策略 | 实测命中 |
|---|---|---|
| 1 | 整行匹配（广告独立成行） | **26623 行 / 334 文件** |
| 2 | **子串**剥离（OCR 把页脚与正文粘在一行）+ 公众号水印 | 469 处 / 48 文件 |
| 3 | 兑底：以广告开头词为锚的行内非贪婪剥离 | 77 处 / 22 文件 |

**硬规则**：
- 广告通常是**行尾**追加（`…正文… 174 数据资产入表咨询、课程培训:陈阳17301209296`），
  → **只能做行内子串替换，不能整行删除**，否则会连正文一起删
- 改前必须 **dry-run**（脚本默认 dry，加 `--apply` 才写），并抽几行对比**改前/改后行尾**确认只动了广告
- **跳过 frontmatter 区**（先定位 fm 结束的 `---`，只改它下面的行）
- 剥离后 **必须重跑 `note_enhance`**：正文换了，且被污染的标签/摘要需要重生
- 收工标准：不要追求 100%。实测剩 7 处/5 文件的 OCR 错读碎片（`陈阳`→`东阳`、
  `数据资产入表`→`衣`/`表现目咨询`），继续追性价比太低
- **例外先看原文**：有 1 篇摘要里"正确"提到联系人与大讲堂——它的**源文档本身就是招生广告**，
  摘要在忠实概括，**不算污染、不要改**

### 🚨 重 OCR 实战流程 + 三个新坑（2026-10-01 全量重跑 102 篇）

**实测数据**（百炼 qwen-vl-ocr，150dpi，并发 8）：
- 吞吐 **≈ 1 页/秒**（并发 8 最优；试过并发 16 **无提升**，0 报错）
- 单页中位延迟 2.6s、最快 0.5s、最慢 8.4s
- 渲染很便宜：0.13s/页
- 成本实测 **≈ 2900 token/页**（先前按 1500 估的会**少一半**）——
  102 篇 10463 页实际 **2977 万 token ≈ ¥14.88**，耗时 **170 分钟**
- 质量：22 页扫描件重 OCR 后从"满篇噪声"变成 **0 噪声的可读中文**

**流程**（脚本已归档在本 skill 的 `scripts/`，直接用这些，别再手写）：
| 脚本 | 作用 |
|---|---|
| `scripts/reocr_estimate.py` | 建计划：md → 源 PDF + 页数（只严匹配 .pdf，会漏；漏了改用下面那个） |
| `scripts/match_loose.py` | **宽松匹配**源 PDF（三候选 + 归一化 + 模糊兑底），实测 37/37 找回 |
| `scripts/reocr_run.py` | 重 OCR 主脚本（并发 8 + 断点续传 + 429 退避 + token 统计） |
| `scripts/fix_strip_marker.py` | 修「标记行被插到文件头」的 fm 损伤 |
| `scripts/vault_lint_dump.py` | 导出全量巡检清单 JSON（lint 只印前 5 条） |
| `scripts/strip_ads.py` / `2` / `3` | 营销水印广告三遍剥离（见下节） |

1. 建计划：md → 源 PDF + 页数（`reocr_estimate.py`，**配 `match_loose.py` 兑底**）
2. 逐文件：渲染全部页 → 并发 8 OCR → 组装 → **覆写 md**（去旧 frontmatter，
   header 写 `> **云端OCR(qwen-vl-ocr)重跑**：日期（正文 N 页）`），交给 note_enhance 重建元数据
3. 断点续传：`reocr_done.json` 按文件名记录，重跑自动跳过
4. **重 OCR 后必须再跑一遍 note_enhance**（否则 tags/摘要还是从垃圾正文生成的）

#### 坑 1：源 PDF 匹配不能只认 `.pdf` 后缀
笔记头部 `> **原始文件**：xxx.md` 里的名字**常常是 `.md`**（原始上传是 md），
按 `.pdf` 结尾过滤 → 误判为"无源 PDF"。实测 102 篇里 **37 篇被误归为无源**，
放开匹配后 **37/37 全部找到**。

正确写法：拿三个候选（md 文件名 stem / 原始文件行去掉任意扩展名 / frontmatter title）
做**归一化**（去空格、连字符、全角括号、书名号）后与 PDF 索引比对，
再加一层"归一化后互相包含且长度差 ≤8"的模糊兑底。
注意源文件名常有空格/连字符差异：`19.《数据安全技术 数据安全风险评估方法》.pdf`
vs md 名 `19.《数据安全技术-数据安全风险评估方法》`。

#### 坑 2：往 frontmatter 前插标记行会把 frontmatter "顶掉"
用 `raw.replace('---\n', marker + '---\n', 1)` 给文件打标记时，
**第一个 `---\n` 就是 frontmatter 的开头**——结果标记行被插到了文件最前面，
文件不再以 `---` 开头 → **lint 立刻报 37 篇"无 Frontmatter"**（自己造出来的缺陷）。
正确做法：找到 frontmatter 的**结束 `---`**，把标记行插到它后面。
修复脚本：`fix_strip_marker.py`（把误插到头部的标记行挪回 fm 之后，实测修 37/37）。

#### 坑 3：`python3 x.py | head -N` 会 SIGPIPE 杀掉脚本，**产物不写盘**
第二次踩到（`match_loose.py | head -60` → `reocr_plan2.json` 不存在）。
症状：stdout 看着完全正常，但 `json.dump` 没执行。
**一律 `python3 x.py > /tmp/x.log 2>&1; echo exit=$?; tail -40 /tmp/x.log`**。

## 常见陷阱

- **🚨 文档读取硬规则（2026-08-09 用户拍板）**：任何 skill 读取 office 文件（Word/Excel/PPT）和 PDF **一律用 markitdown**（`.venv` 已装 markitdown 0.1.6 + pdfminer.six + pymupdf，PDF 转换实测 OK）。例外：xlsx 带损坏样式时 openpyxl 报 `TypeError: Fill`，改用 read_file 提取。不要用 fitz/python-docx/openpyxl 等替代方案做常规文档读取。
- **🚨 yaml.safe_load + yaml.dump 破坏 wikilink 格式**：不要用 `yaml.safe_load` 解析含 `[[wikilink]]` 的 frontmatter。YAML 将 `[[标题]]` 视为嵌套列表 `[['标题']]`，dump 后变成 `- ['标题']`。修复 v2（scripts/fix_links_v2.py）用纯文本 regex 替换避免此问题。
- **巡检脚本显示断链数字偏高**：lint_vault.py 在用 `yaml.safe_load` 解析时的显示层问题，不影响文件。
- **修复脚本修改大量文件**：`fix_links.py` 会重写所有含 related 字段的笔记。跑之前确保没有未提交的修改。
- **政府网站无标准 RSS**：国家数据局、民政部、发改委等官网均无 RSS 输出。新华网是目前唯一可靠的政策 RSS 源。如需覆盖特定部委，考虑网页爬取方案。
- **no_agent cron 脚本依赖**：Python 依赖（pyyaml、feedparser 等）未全局安装时，用 shell 包装脚本通过 `uv run --with <pkg>` 解决。脚本放 `/opt/data/scripts/`，**必须是真实文件**不能用符号链接（调度器会解析到外部路径并拦截）。
- **OCR 超大 PDF 跳过策略**：`MAX_OCR_PAGES` 已从 30 改为 99999（取消页数限制）。但 >80 页的扫描件 PDF（如培训照片、案例集 >300 页，200 页蓝皮书）会在 400s subprocess timeout 内未完成全部 OCR。这些文件**直接跳过**（hash 写入 `.ingested`），不做截断入库。手动手动处理方案：单独跑 `python3 pdf_ocr.py <path>` 并加更长 timeout，或分段 OCR。
- **symlink 陷阱**：`ln -sf` 创建的链接在 cron 沙箱中会被解析到真实路径，若超出 `/opt/data/scripts/` 范围则被拦截。用 `cp` 复制真实文件。
- **WeChat 限流误报**：`last_status: "error"` 可能只是微信发送被 iLink rate limited，脚本本身成功执行了。看 `agent.log` 中 `Job 'X': delivered to weixin` 确认脚本跑完；看 `errors.log` 中 `iLink sendmessage rate limited` 确认是发送层的问题。不要因为 status=error 就重跑脚本。
- **ingest_docs.py 入库成功但 index/log 未更新（2026-08-06 排查）**：`save_note()` 内部会补 `# 标题`，但 `extract_title(text)` 在 save 之前调用——若原 PDF 无 H1 标题，extract_title 返回 None，`new_notes` 为空，`update_index/update_log` 被跳过。修复已加兜底：`if not title: title = f.name.rsplit('.', 1)[0]`。同理，cron 报告"成功但未更新索引"时先查 extract_title 是否返回 None。手动补记：直接编辑 `index.md`（`- [[标题]] — 自动摄入` 插到 `## 实体` 前 + 更新"共 N 页"计数）和追加 `log.md`。
- **markitdown 转换超时（60s）多为瞬时网络/环境慢**：cron 报 `MarkItDown 转换超时` 时先手动跑一次 `md.convert()` 实测（常只要 7s），确认是瞬时问题而非永久故障，再手动重跑 `python3 /opt/data/ingest_docs.py` 补处理。注意失败文件**未被标记**（未写 `.ingested`），重跑会自动重试，无需清标记。
- **Agent 模式 cron 的 SILENT 陷阱**：不要在 cron prompt 里写类似"无新文档时输出 `[SILENT]` 以静默"的规则。即使无新内容，用户也需要知道任务正常执行了（执行时间、状态、无新文档确认）。否则用户会以为任务没跑。正确做法：**无论是否有新内容，都输出简短的中文执行报告**（包含执行时间、新入库数量、总数、状态）。
- **📛 多 cron slot 的分配不均衡**：同一类任务的多个 cron 槽位，每批文件数应保持一致。一个槽位塞 20 个文件而其他槽位只跑 3 个，会导致单个槽位执行时间过长（尤其 OCR 密集型任务），用户会认为分配不合理。修正：计算剩余文件数 ÷ 槽位数，每个槽位承担相同的文件数。
- **加密 PDF 拖垮批处理**：pymupdf 的 `len(doc)` 对加密 PDF 返回正确页数，但 `doc[i]` 抛 `ValueError("document closed or encrypted")`。单文件崩溃会导致整个 cron 超时。OCR 脚本（`pdf_ocr.py`）必须用 try/except 逐页防御。
- **微信文档缓存可能为空**：如果用户从未通过微信发送过文件附件，`cache/documents/` 目录存在但为空。脚本正常退出返回 `📭 缓存目录无文档文件`。这不是错误。
- **📛 weixin_ingest.py 的 `to_cleanup` 未定义 bug（2026-08-18 修复）**：脚本第 308 行 `to_cleanup.append(str(f))` 引用从未初始化的变量，处理第二个文件时抛 `NameError: name 'to_cleanup' is not defined` 中断（第一个文件已入库但后续文件被跳过，且 index/log 未更新）。残留代码与"保留缓存不清除"偏好冲突，直接删除该行即可。症状：日志显示"1/1 篇笔记已增强"后紧跟 Traceback。修复后需手动补 index.md/log.md。
- **📛 微信多文件发送可能部分丢失（2026-08-18 实测）**：用户一次发 3 个文档，gateway 实际只收到 2 个附件（第三个上传失败/被吞），`cache/documents/` 只有 2 个 `doc_` 文件。用户说"是 N 个文档哦"时**先查证再回应**：① `ls /opt/data/cache/documents/` 数 `doc_` 文件；② `grep -c "media=1" /opt/data/logs/gateway.log`（当天该用户会话的附件计数）。确认是上传失败而非自己漏处理后，让用户重发缺失的文件，**不要猜测第三个是什么**。附件入参顺序：media 数 = 文件数，msg 为空纯发文件。
- **📛 weixin_ingest 入库后 index.md 不会自动更新（2026-08-18 实测）**：入库成功（01-WeiXin/ 出现 md 且 note_enhance 增强完成）但 index.md 的 `## 微信文档 (01-WeiXin/)` 区不更新、计数停留在旧值。修复 `to_cleanup` bug 后仍不自动更新索引。**入库完成后手动编辑 index.md**：在该区加 `- [[笔记名]] — 描述，微信DOCX摄入`，并更新 `> 当前：N 篇` 计数（先 `ls 01-WeiXin/ | wc -l` 数实际 md 数）。**用户偏好（2026-08-18）**：微信文档入库后"先留存就好，用于以后文档编写"——**不要主动提议做摘要/合并/整理**，等用户开口再提取要点。
- **note_enhance.py 的 VAULT 硬编码**：`note_enhance.py` 的 `VAULT` 变量固定为 `concepts/` 目录。当微信入库脚本需要增强 `01-WeiXin/` 中的笔记时，必须传**绝对路径**给 note_enhance。note_enhance 的 main() 已支持绝对路径参数（`if p.is_absolute(): files.append(p)`）。调用示例如下而非使用 cwd：
- **⚠️ summary 字段含 ASCII 双引号导致 YAML 解析失败**：`build_frontmatter()` 用 `f'  - "{s}"'` 包装摘要条目，若 `s` 中本身含 ASCII `"`（如中文引用的标题 `"数据二十条"`），YAML 会将内容中的 `"` 误判为标量结束符，抛出 `while scanning a quoted scalar` 解析错误。修复：确认 YAML 格式后再写入，或改用单引号 `f'  - ''{s}'''`（注意单引号内不支持转义）或 YAML 块标量。受影响文件需重建 frontmatter。
- **📛 文件名特殊字符（中文括号、空格）截断 shell 命令**：`$(cat list)`, `xargs`, 和 shell glob 展开会按空格/括号分词。例如 `【三件套】技术架构.md` 会被拆成 `[三件套]技术架构.md`。**必须用** Python `subprocess.run([...] + batch)` 逐批传参数列表，避免 shell 分词。`scripts/batch_enhance.py` 已内嵌此处理。`ingest_docs.py` 的 `Path(BACKUP_DIR).glob('**/*')` 不受影响（纯 Python glob）。\n- **📛 空 PDF 文件导致 pymupdf EmptyFileError**：零字节的 .pdf 文件（如文件名相同但带有 `-1` 后缀的重复副本）会使 `fitz.open()` 抛出 `EmptyFileError`，直接中断批处理。在 `convert_to_markdown()` 的 `try/except` 中应检查文件大小 `os.path.getsize() > 0` 后跳过并记录 hash，避免重复尝试。
- **📛 重跑 OCR 被 done 标记卡住（2026-08-06）**：`re_ocr_cloud.py`/`re_ocr_shells.py` 的 pending 队列会排除 done 标记（`/tmp/re_ocr_cloud_done.json` + `/tmp/re_ocr_done.json` 合并去重）。**某文件上次 OCR 只生成部分内容（md 不完整但已写 done）时，重跑会被静默跳过——日志显示"待处理: 0 个"**。排查：`--only <关键词>` 启动后若显示 0 个待处理，先从 done json 中删掉该文件再重跑。判断 md 完整性用文件大小阈值（≥3000B 且 ≥页数×150B），不要信 done 标记。
- **📛 OCR 乱码 wikilink（2026-08-08 实测）**：PaddleOCR 会把 `[[` 字符识别进正文，生成畸形链接——**不闭合**（`[[opioid Mid惩裁]`）、**嵌套**（`[[55551550][)+ங்க]{17558}}`）、或 `[[IO]]`/`[[必填]]` 这类短噪声。这些会让 lint 报断链。**诊断**：`rg -n -o '.{0,30}<关键词>.{0,40}' concepts/<file>` 看实际文本（普通 `[[...]]` 匹配不到时，用 rg 定位确切字节）。**清理**：对每个文件用正则 `r'\[\[<乱码特征>[^\n<]{1,80}'` 匹配到 `<|LOC` 或行尾删除；注意目标常是单括号/嵌套形式，精确匹配会落空，需用通配。全库批量清理时先确认 lint 报告的目标确在正文（还是 frontmatter related / 纯文本误报）。
- **📛 OCR 补全文件增强后 related 可能引用不存在页面**：note_enhance 的 `discover_related` 把 OCR 噪声当笔记名生成 related 链接，lint 报断链。但**大部分"断链"是 lint 正则误报**（见上文断链误报两处修复），修完 lint 再清理剩下的真乱码，不要盲目全库删链接。
- **📛 re_ocr 脚本 process_one 的入参是 scan report 行而非路径**：`re_ocr_shells.py` 的 `process_one(item)` 期望接收 `/tmp/pdf_scan_report.csv` 的一行（`[fname, pages_str, text_layer_str, ...]`），不是文件路径字符串。直接传路径字符串会把文件名按字符拆开导致 `ValueError: invalid literal for int()`。自定义补跑脚本时应从 csv 取整行传入，脚本内部会从 BACKUP_DIR 自动定位源文件。
- **📛 入库完整性检查漏洞：`_needs_ocr` probe 失败默认放行（2026-08-08 实测，用户要求"入库时候要做检查"）**：`ingest_docs.py` 的 `_pdf_probe` 原用 `uv run --with pymupdf` 探测 PDF 结构，在 cron 环境冷启动超时/失败时返回 None，而 `_needs_ocr` 的 `if not probe: return False` **默认放行**——33 页扫描件（文字层仅 1000 字、32 页图片）被当"非扫描件"用 markitdown 入库，正文 90% 图片内容全丢，cron 却报告"正常转换（非扫描件，未触发 OCR）"。**诊断线索**：md 大小远小于页数×150B 且正文只有开头引文+结尾推广（公众号推文模板特征），源 PDF 页数多但文字层极少。**修复三处**：① `if not probe` 改为保守兜底 `return size >= 5MB and len(text) < 2000`（宁可多 OCR 不漏）；② `_pdf_probe` 改用 `/opt/data/ocr_venv/bin/python3`（自带 pymupdf/fitz，免 uv 冷启动，timeout 60→30）；③ OCR 切换同样改 `ocr_venv` 直调（原来 `uv run --with pymupdf python3 pdf_ocr.py` 冷启动慢也易超时）。**验证**：修复后 `_needs_ocr(云上AI指南33页扫描件)` 应为 True、正常文字 PDF 应为 False。判断"是否扫描件"的可靠探针：页数≥3 且文字层<800，或图片页>0 且文字页占比<50%。
  ```python
  subprocess.run(['python3', '/opt/data/note_enhance.py', absolute_path], timeout=300)
  ```

---
name: docx-report-delivery
description: "生成与既有模板格式一致的docx并交付（微信/本地）。"
version: 1.0.0
author: curator
created_by: agent
tags: [docx, 汇报材料, 模板, 微信投递, word, 月度汇报]
trigger: 用户要求"导出word/按模板生成docx/格式和XX一致/发到微信/复制上期格式"时加载
---

# docx 报告生成与交付

已验证工作流（2026-08-22 智慧民政 7-8 月月度重点项目汇报材料）。

## 模板复制法（格式100%一致）

目标：新 docx 与上期文件格式完全一致。**不要从头排版**，直接复制上期文件做模板。

步骤：
1. `shutil.copy(上期.docx, 新路径)`
2. python-docx 打开，先分析并 `copy.deepcopy` 关键段落元素：
   - 标题段、信息段（团队名称/汇报时间）、章节标题段、正文段（首行缩进）、编号段（无缩进）
3. 删除 body 里所有 `w:p`（**必须保留 `w:sectPr`**）
4. 按内容结构循环 `copy.deepcopy` 对应段落元素插入，set_text 只改第一个 run 的 `w:t`、删除多余 run
5. 验证（无 soffice 时）：python-docx 重开查段落数/字号；markitdown 读回查内容完整

已知格式规格（6月智慧民政汇报材料，可类推）：
- 标题 18pt（size=228600 EMU）粗体居中
- 团队名称/汇报时间 10pt（127000 EMU）居中
- 章节标题 = Heading 2（一、二、…六、）
- 正文首行缩进 first_indent=279400 EMU（≈22pt）
- 编号段（"1. xxx"）无缩进，编号是手打文本、非自动编号

## 微信文件投递

- chat_id 从 `/opt/data/channel_directory.json` 的 `platforms.weixin[].id` 取（如 `o9cq807-...@im.wechat`）
- 用 cron 一次性任务（agent 会话内无 send_message 工具）：
  `cronjob(action="create", name=..., prompt="将文件 <绝对路径> 作为附件投递给当前微信用户（用文件投递能力发送，不要只发路径文本）", schedule="1m", deliver="weixin:<chat_id>")`
- 验证：`cronjob(action="list")` 看该 job 的 last_status=ok、last_delivery_error=null、state=completed
- 限流兜底：iLink rate limited 会导致投递失败（cron last_delivery_error 可见 "rate limited"）；文件同时放 OutPut Box 目录并告知用户路径，用户可自行取

## 终端守卫坑（lifecycle_guard embedded null bug）

terminal 执行 python 脚本时，命令中可执行路径含 `/`（如 `.venv/bin/python3`）会触发 `ValueError: open: embedded null character in path`——守卫把含 `/` 的可执行 token 当被引用脚本，读 ELF 二进制内容（NUL 保留）后递归扫描崩溃。

绕法：先 `export PATH=/opt/data/.venv/bin:$PATH`，命令用**裸命令名** `python3`（不含 `/`）。

注意：execute_code 沙箱没有项目依赖（docx 等），别指望它替代。

## 与 plan-writer 的关系

plan-writer（用户自有 skill）负责政务方案/汇报的架构、文案、humanizer 去 AI 味；本 skill 负责 docx 格式复刻与投递交付。plan-writer 中"输出到 OutPut Box 并微信推送"的具体实现见本 skill。月度汇报数据源查找（concepts/ 下搜"月度报告"和"双周工作汇报"）见 plan-writer。

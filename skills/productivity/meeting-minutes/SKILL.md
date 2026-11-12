---
name: meeting-minutes
description: "Use when 用户发来会议录音/视频要整理成纪要。ASR转写→豆包式四段结构→入库。"
version: 1.0.0
author: 邵雷 / Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [会议纪要, ASR, 语音转写, 豆包, 思源, Obsidian, 政务]
    trigger: [会议纪要, 录音, 纪要, 转写, 会议录音, 语音转文字, minutes, 会后整理]
    related_skills: [meeting-action-items, note-enhance]
    requires-skills: [image-ocr]
---

# 会议纪要（中文）

用户把会议录音/视频丢过来，产出可直接入库的 Obsidian 纪要。

## When to Use / 触发场景

- 「这是会议录音，整理成纪要」
- 微信直接发来 mp3/m4a/amr/wav 等音频或会议视频
- 「把这个录音转成文字」

不适用于：只有文字笔记要做成任务清单 → 用 `meeting-action-items`。

## 铁律

1. **不许编**。转写里没有的人名、数字、时限、结论一律不写。听不清的写 `【听不清】`，没提到的字段留空。
2. **不许把提议当决策**。会上只是「可以考虑」「回头看看」的，放进「待定」不放「关键决策」。
3. **不许编发言人身份**。ASR 只给「说话人1/2」时不猜他是不是厅长、处长、某某总。
4. **保密优先**。会议录音可能涉密，**只准用境内服务**（百炼）。禁止把音频送给 Google/Gemini 等境外 API。

## ASR 通道

### 实测横评（2026-11，212 字中文政务文本 / 17 个专有名词 / 每个模型跑 3 次）

| 模型 | 调用方式 | 相似度 | 最差 | 专名 | 耗时 | 稳定 | 结论 |
|---|---|---|---|---|---|---|---|
| **`qwen3.8-omni-flash`** | OpenAI 兼容 | **1.0000** | 1.0000 | **17/17** | 4.4s | ✅ | ✅ **默认用这个** |
| `qwen3.5-omni-flash` | OpenAI 兼容 | 0.9991 | 0.9974 | 17/17 | 0.9s | ⚠️ 会飘 | 备选 |
| `qwen3-asr-flash` | OpenAI 兼容 | 0.9896 | 0.9896 | 15/17 | 1.3s | ✅ | 快，但「秦务员」常错 |
| `fun-asr-flash-2026-06-15` + 热词 | 顶层 `format`+`vocabulary` | 0.9819 | 0.9819 | 16/17 | 1.9s | ✅ | 快且可加热词，次选 |
| `fun-asr-flash-2026-06-15` 无热词 | 顶层 `format` | 0.9699 | 0.9664 | 14/17 | 2.2s | ⚠️ | 不要单独用 |
| `fun-asr` / `qwen3-asr-flash-filetrans` | 异步 HTTP | — | — | — | — | — | ❌ 只认公网 HTTPS，`oss://` 报 `REQUEST_INVALID_FILE_URL_VALUE` |
| `qwen-audio-3.0-asr-flash` | OpenAI 兼容 | — | — | — | — | — | ❌ 试过四种格式均报 `format is empty`，用不了 |

**结论：固定用 `qwen3.8-omni-flash`。** 它是唯一 3 次全对且零波动的。
62 分钟会议约 9 分钟转完、不到一毛钱。

**模型换代或额度开关变动后，跑 `scripts/asr_bench.py` 重测，不要手写测试。**
默认用内置政务文本合成音频（天然有标准答案），跑 3 次看稳定性；
要贴近实战就 `--audio <真会议片段> --ref <标准答案.txt>`。
**判据是先看「最差一次」而不是平均值**——生成式单次全对不代表可靠，
`qwen3.5-omni-flash` 就出现过一次 0.9974 的抖动，平均值看不出来。

热词确实有效（`fun-asr-flash` 加顶层 `vocabulary` 后命中 14→16、相似 0.9699→0.9819），
但加上热词仍不如 omni 不加。所以**正规会议录音优先 omni**；确实需要快时用
`fun-asr-flash` + 顶层热词。

### 三个容易踩的格式坑

调用结构各不相同，搞错就是 `format is empty` 或 `UNSUPPORTED_FORMAT`：

```python
# ① omni 类：data URI + input_audio.format
{'model': 'qwen3.8-omni-flash', 'modalities': ['text'], 'stream': False,
 'messages': [{'role': 'user', 'content': [
     {'type': 'text', 'text': prompt},
     {'type': 'input_audio', 'input_audio': {'data': f'data:audio/mpeg;base64,{b64}', 'format': 'mp3'}}]}]}

# ② qwen3-asr-flash：data URI，但绝对不要带 format 字段
{'model': 'qwen3-asr-flash', 'stream': False,
 'messages': [{'role': 'user', 'content': [
     {'type': 'input_audio', 'input_audio': {'data': f'data:audio/mpeg;base64,{b64}'}}]}]}

# ③ fun-asr-flash：format 和 vocabulary 都放请求顶层，data 用 data URI 且 input_audio 里不带 format
{'model': 'fun-asr-flash-2026-06-15', 'stream': False, 'format': 'mp3',
 'vocabulary': {'秦务员': 4, '民政通': 4},
 'messages': [{'role': 'user', 'content': [
     {'type': 'input_audio', 'input_audio': {'data': f'data:audio/mpeg;base64,{b64}'}}]}]}
```

热词权重 1-5，推荐 4，过高会拖累其他词。放在 `asr_options.vocabulary` 里**不生效**，必须放顶层。

### 排查顺序

报 `AllocationQuota.FreeTierOnly` 时，先用 `qwen-plus` 探一下账号付费能力：
它能正常返回 token 用量，就说明账号没欠费、没认证问题，是那一个模型自己的开关，
**直接换模型即可，不要让用户去翻控制台**（曾让用户白查半天，实际是模型级开关）。

```bash
/opt/data/.venv/bin/python3 scripts/transcribe_omni.py "$AUDIO" \
  --out /tmp/transcript.json --chunk 600 \
  --terms "专有名词1,专有名词2,..."
```

- 默认切 600 秒。62 分钟音频 → 7 段 → 约 9 分钟跑完，不到一毛钱。
- **专有名词表必须传**：omni 不支持热词参数，只能写进 prompt，不传就会出现
  「秦务员→勤务员」这类同音错字。
- 空/碎片段（<1 秒）必须剔除，否则 API 报 `InvalidParameter: The audio is empty`。

### 🚨 重复循环检测（必做）

omni 是生成式模型，遇到嘈杂片段会陷入重复循环，输出几十遍
「这个时间，这个时间，这个时间……」或「一块九，一块九，一块九……」。

转写完**必须逐段扫一遍**：把每段按标点切句，统计最高频句占比和最长连续重复。
判据：**最高频句占比 >25% 或连续重复 ≥5 次 → 该段作废重跑**。

重跑办法：只切出这一段，改为 150 秒小段重跑，prompt 里加一句
「绝对不要重复同一句话。听不清的地方留空，不要用重复的词填充」，
再对输出做连续重复句去重。

正常段的最高频句占比都在 3–6%（都是「对」「对吧」「啊」这类口语词），很好分辨。

### 备选：百炼专用 ASR（额度开通后更优）

| 模型 | 时长上限 | 说话人分离 | 热词 |
|---|---|---|---|
| `fun-asr` | 12h / 2GB | ✅ | ✅ |
| `qwen3-asr-flash-filetrans` | 12h / 2GB | ❌ | ❌ |
| `qwen3-asr-flash` | 5min / 10MB | ❌ | ❌ |

`fun-asr` 需先申请 OSS 上传凭证再提交异步任务，脚本 `scripts/asr_bailian.py` 已实现。
约 ¥0.29/小时。**动手前先把预估费用告诉用户。**

## 流程

### 1. 拿到音频

微信发来的文件落在 `/opt/data/cache/documents/`。先确认：

```bash
ffprobe -v error -show_entries format=duration,size -of default=nw=1 "$F"
```

时长超 12 小时或 2GB 就先切分（`ffmpeg -f segment`）。

### 2. 转写

```bash
/opt/data/.venv/bin/python3 scripts/asr_bailian.py "$AUDIO" --out /tmp/asr.json --diarization
```

输出 JSON 含分段文本、时间戳、说话人（若开启）。
**转写失败不要瞎猜内容**，原样报告错误。

### 3. 生成纪要

用 DeepSeek 官方 `deepseek-chat`（非推理，快且够用）。先算清 token：
3 小时会议转写约 3-5 万字 ≈ 5-8 万 token 输入。分段喂，不要一次全塞。

按 `references/template.md` 的结构生成。**章节标题用原文，不要自创。**

### 4. 元数据

- `tags`：10 个关键词，专有名词优先（系统名、机构名、项目名）
- `summary`：5 条，每条一句话，**结尾带 ` ×`**（用户笔记插件的标记）
- `related`：用 `[[ ]]` 链到相关笔记，找不到就留空数组，不要硬编

### 5. 入库

写进 `/opt/data/Obsidian Vault/Obsidian Vault/00-INBOX/`。

**文件名按用户现有习惯带项目前缀**：`<项目名>-<会议主题>纪要-<YYYYMMDD>.md`
（如 `四川省数字政府项目-一张图与地图数据采购讨论会纪要-20261109.md`）。
不要用日期当标题，也不要直接叫「XX会议纪要」而不带项目名。

**必须补 `related` 双向链接**：先去 `00-INBOX` 和 `concepts/` 搜同项目、同主题的旧纪要，
挑 2-3 篇相关的写进 `related`，并在对应旧文件里加一条反链。
同一主题的一系列会议（如空间地理库 → 一张图采购）串起来才看得出脉络。

### 6. 交付

微信推送一份 Markdown 摘要（不要全文），附入库路径。

## 两种正文形态

用户的纪要库里两种都有，按会议类型选：

**A. 豆包式（默认，适合沟通交流/对接会）**

```markdown
## 总结
（一段话交代谁和谁、谈什么、定了什么方向）

## 智能章节
00:00
> 本章节是……（一段时间的内容概述）

08:22
> 本章节围绕……

## 关键决策
1. <决策内容>：<待明确事项>：<讨论过程谁说了什么>：<判断依据>：<后续推进>

## 金句时刻
「原话直引」
—— 为什么重要
```

**B. 政务式（适合工作部署会/培训/汇报会）**

```markdown
一、<大节标题>
1. <条目>
2. <条目>

二、<大节标题>
1. <条目>
注意事项：a…… b…… c……
```

判断：会上有明确分工/部署/培训讲解 → 用 B；多方交流、探讨方案、谈合作 → 用 A。

## 常见坑

- **`auto` 模式实测会误判**：一场公安侧与中心侧谈采购的对接讨论会，曾被判成「部署会」
  而用了政务式。判定规则已写死：对接会/交流会/讨论会/座谈会/需求对接一律豆包式，
  只有任务分解、责任分工、时限、培训才算政务式，**判断不了默认豆包式**。
  但用户指定结构时以用户为准，不要自作主张。
- **生成后必须自己逐条核对格式**，不能直接交给用户：H1 标题在不在、tags 是不是正好 10 个、
  summary 是不是 5 条且都带 ` ×`、金句有没有「——」点题行。模型经常漏其中一两项。
- **转写同名重复**：豆包导出的纪要在入库转换时会每段重复 2-3 遍（嵌套列表炸开）。生成的纪要自己写干净，别复制这种脏数据。
- **`关键决策` 字段名丢失**：豆包原稿有「决策内容/依据/讨论」等字段名，转换后变成空的 `​​：`。自己生成时字段名要写全。
- **会议日期 ≠ 笔记文件 date**：用户旧笔记的 frontmatter date 有过写成 `2026/06/22` 的错值。用会议实际日期。
- **不要把 `原始文件` 那行写死**：`> **原始文件**：xxx.md` 是笔记录入时加的，不是纪要内容。

## 验收

- [ ] 每条决策/待办都能在转写里找到原话依据
- [ ] 没编人名、数字、时限
- [ ] tags 10 个、summary 5 条且带 ` ×`
- [ ] 已入库且路径可访问
- [ ] 音视频、转写 JSON 临时文件已清理（除非用户要留）

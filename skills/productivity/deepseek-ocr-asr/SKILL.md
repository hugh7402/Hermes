---
name: deepseek-ocr-asr
description: Use when 要把文档/图片转文字或把录音转写。DeepSeek OCR/ASR 接口。
version: 1.0.0
author: Hermes Agent
tags: [ocr, asr, 语音识别, 转写, 文档识别, deepseek, 会议纪要]
trigger: OCR|识别文字|扫描件|图片转文字|录音转写|语音识别|音频转文字|会议转写
requires-skills: []
metadata:
  hermes:
    tags: [ocr, asr, deepseek]
    related_skills: [meeting-minutes]
---

# DeepSeek OCR 与语音识别

## When to Use

- 用户发来 PDF / Word / PPT / 图片，要提里面的文字
- 用户发来会议录音、语音，要转成文字做纪要
- 手里有扫描件、截图，需要可检索文本

## 两个接口的共同点

- 同一个 Key（`/opt/data/.env` 的 `DEEPSEEK_API_KEY`），`multipart/form-data` 传 `file`
- 端点：`/v1/tools/ocr`、`/v1/tools/asr`
- **文件不存 Files API、不交给对话模型**，纯工具调用

---

## OCR（1.5 元/千页）

脚本：`/opt/data/.tmp_tests/ds_ocr.py`

```bash
python3 ds_ocr.py 文件.pdf              # 纯文本（快）
python3 ds_ocr.py 文件.pdf --layout     # 带坐标
python3 ds_ocr.py 文件.pdf --out x.json # 存 JSON
```

```python
from ds_ocr import ocr, plain_text
d = ocr('文件.pdf')            # layout=True 出坐标
print(d['page_count'], d['usage'])
print(plain_text(d))
```

### 选哪个 purpose

| purpose | 行为 | 何时用 |
|---|---|---|
| `text_recognition` | 不含图片的 Word/PPT 直接提取文字，其它逐页识别 | 只要文字、要最快 |
| `rich_layout_recognition` | 所有文件逐页识别，保留 `<｜ref｜><｜box｜>` 和坐标 | 要定位/裁图/还原版面 |

坐标 `[[x1,y1,x2,y2]]`，原点左上，按页宽高归一化到 **0-1000**。
实际像素 = 坐标 × 页面尺寸 ÷ 1000。

### 实测数据

- 8 页文字型 PDF：**4.6 秒**（text 模式）/ 10.6 秒（layout 模式）
- 输出直接是带 markdown 标题和粗体的干净正文，**不用后处理清理**
- 封面等纯图片页会返回 **0 字符**，属正常，不是失败

### 🚨 必查 finish_reason

内容密集的页（实测一个 25,204 字符的页）会返回 `finish_reason: length`，
**该页文本不完整**。ds_ocr.py 会把被截断的页码打印出来。
遇到这种情况：把这几页单独拆出来、或降低单页信息量后重跑。

### 硬限制

- 文件 ≤ **100 MiB**、≤ **1000 页**
- 上传 120 秒内完成、中途停顿不超 30 秒
- 从开始上传算总时长 **180 秒**——是硬上限，大文档可能识别不完
- 🚨 识别开始后状态码已是 200，**失败会在 body 里返 error 对象**，必须自己检查 `'error' in d`
- 账号同时最多 15 个识别

---

## ASR 语音识别（0.39 元/小时，限时 5 折）

脚本：`/opt/data/.tmp_tests/ds_asr.py`

```bash
python3 ds_asr.py 会议.mp3                    # 自动切片，输出带时间窗全文
python3 ds_asr.py 会议.mp3 --out t.txt --workers 6
```

```python
from ds_asr import transcribe
txt = transcribe('会议.mp3', workers=4)
```

### 🚨 为什么必须自己切片

| 限制 | 值 |
|---|---|
| 单次时长 | **120 秒**（硬上限） |
| 单文件 | **8 MiB** |
| 格式 | **16 位 PCM WAV 或 Ogg Opus**（MP3 直接传会 400） |
| 采样率 | 8000/16000/22050/24000/32000/44100/48000 Hz |
| 声道 | 单/双声道，**双声道只识别左声道** |  

所以固定用 ffmpeg 转 **16kHz 单声道 16bit PCM**，按 **110 秒**切片
（16k×2B×110s ≈ 3.4MiB，稳稳低于 8MiB）。`ds_asr.py` 已内置。

### 其它要点

- **没有语种参数**，自动识别；支持中/粤/英/日/韩/德/法/西/葡/意/俄/阿/印地/印尼/越/泰/土/马/菲/波/匈
- **不返回句子级时间戳**，只能精确到 110 秒切片窗口。要更细的段属只能把切片改小
- 账号同时最多 **50 个请求**，所以切片可以放心并发（`--workers`，默认 4）
- 计费按音频时长，精确到秒，**每秒都算钱但很便宜**：一小时 0.39 元
- 切点会把一句话从中间截断，同一个话题可能跨两段；做纪要时要把相邻段连起来读

### 实测数据

- 120 秒音频：**3.8 秒**返回，509 字
- 4 分钟会议切 3 段并发：三段全部成功，切口对得上
- 中文会议口语识别质量好，但**同音字会错**（实测「边部」变「边牧」、「点签」变「电气」）。
  做正式纪要前要把专有名词对一遍，别直接粘进文档

---

## 与旧方案的选择

### 🚨 会议转写：仍用百炼 `qwen3.8-omni-flash`，不用 DeepSeek ASR

同一段 120 秒真实会议录音（大屏改版讨论会，多人抢话）实测：

| | 百炼 qwen3.8-omni-flash | DeepSeek ASR |
|---|---|---|
| 价格 | **~0.05 元/小时**（audio 7 token/秒） | 0.39 元/小时（**贵 8 倍**） |
| 耗时 | 13-14 秒 / 120s | 3.8 秒 / 120s |
| 字数 | **547 字** | 509 字 |
| 切段 | **600 秒**（切口少） | 120 秒（切口多） |
| 专有名词提示 | ✅ 支持（写进 prompt） | ❌ 不支持 |
| 关键术语 | **「数据编目」对 8 次** | 错成「边框 / 边部」 |

字符相似度仅 **67%**，且差异不在细节而在**核心术语**：
这段会讲的是数据编目，百炼听对了 8 次，DeepSeek 一次没对。
术语错了整段纪要就废了，这是致命伤，不是风格差异。

**结论：正式会议录音一律用百炼 omni。** DeepSeek ASR 只在百炼欠费/额度锁住时当备用通道，
或用于短音频、不涉专业术语的普通语音。

### 文档 OCR：优先 DeepSeek

这条反过来——1.5 元/千页、8 页 4.6 秒、直出干净正文，比百炼 qwen-vl-ocr 划算且快。
百炼仍可用于需要更强版面理解或 DeepSeek 失败的兼容。

### 子幕时间轴

**不要拿这两个做需要字幕时间轴的场景**（ASR 不返句子级时间戳），
那种要走 `ai-subtitle-pipeline`。

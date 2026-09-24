---
name: ai-subtitle-pipeline
description: Use when 视频无中文字幕：ASR转写+AI翻译+内嵌。
tags: [字幕, 无字幕, srt, asr, whisper, 语音转写, 翻译字幕, b站下载, bilibili, yt-dlp, 意大利语, 内嵌字幕]
trigger: 用户要下载的片子全网没有中文字幕、需要生成字幕、B站视频下载、yt-dlp、外挂/内嵌字幕、srt 制作
requires-skills: [movie-download]
---

# AI 字幕管线（无字幕视频 → 内嵌中文）

## 何时用
- 下载的片子**全网无中文字幕**（小众纪录片、DAZN/流媒体独家、无发行片）
- B站/YouTube 视频下载（含字幕核查）
- 需要把字幕**内嵌**进 mp4

## 实测基线（2026-09-16 AC米兰《我们在一起很好》）
输入：B站 1080p AV1 二手片源（93.5 分钟意大利语），全网无字幕（BT无源、YouTube只有片段、B站CC字幕列表空）。
结果：全自动生成 1319 条中文字幕并内嵌，端到端约 15 分钟。

---

## 第一步：先确认"真的没字幕"（别信标题）

⚠️ **B站标题写"机翻中文字幕"可能是假的**——必须三查：

```bash
# 1) yt-dlp 看字幕轨（未登录也能看 danmaku 之外的）
yt-dlp --list-subs "https://www.bilibili.com/video/BVxxxx"
# 2) B站 API 查 CC 字幕（aid/cid 从 yt-dlp 输出里捞）
curl -s -A "Mozilla/5.0" -H "Referer: https://www.bilibili.com/" \
  "https://api.bilibili.com/x/player/v2?aid=<aid>&cid=<cid>" | python3 -c "import sys,json;print(json.load(sys.stdin)['data']['subtitle'])"
# subtitle.subtitles == [] → 无任何 CC 字幕
# 3) 抽帧 OCR 查硬字幕（多抽几个点，覆盖全片）
for t in 300 600 1200 1800 2400 3000 3600 4200 4800 5400; do
  ffmpeg -ss $t -i "$VIDEO" -frames:v 1 -q:v 3 -y /tmp/frames/f_$t.jpg 2>/dev/null
done
# OCR（本地 rapidocr_onnxruntime，注意包名不是 rapidocr）
/opt/data/ocr_venv/bin/python3 -c "
from rapidocr_onnxruntime import RapidOCR
import glob
engine = RapidOCR()
for p in sorted(glob.glob('/tmp/frames/*.jpg')):
    res, _ = engine(p)
    print(p, [r[1] for r in r[0]] if r[0] else '(无文字)')
"
```
只出现球衣名/台标/水印 → 确认无字幕，进入管线。

---

## 第二步：ASR 转写（SiliconFlow）

❗ **SiliconFlow 上只有 `Qwen/Qwen3-ASR-1.7B` 支持意大利语**（实测）：
| 模型 | 意大利语表现 |
|---|---|
| `Qwen/Qwen3-ASR-1.7B` | ✅ 准确 |
| `XingChenAGI/XingChenASR-V3.2` | ❌ 输出中英混杂乱码 |
| `FunAudioLLM/SenseVoiceSmall` | ❌ 不支持（zh/en/ja/ko/yue） |

**API 不支持时间戳**（`response_format=verbose_json` 返回空）→ 用**固定窗口 + 按字符比例分配时间轴**。

关键参数（实测最优）：
- 音频：`ffmpeg -vn -ac 1 -ar 16000 -c:a libmp3lame -b:a 48k`
- **窗口 20 秒**（281 段 / 93.5 分钟）→ 段内再按句切分，误差 1-3 秒，访谈类足够
- **并发 6 路**：281 段 **40 秒**跑完
- 必须**断点续传**（每 20 段落盘 JSON），失败段重试 3 次
- 不要用 `silencedetect` 切分（纪录片背景音不断，93 分钟只找到 47 处静音，切不开）

---

## 第三步：翻译 + SRT（DeepSeek）

- 模型 `deepseek-chat`（`deepseek-v4-flash`/`deepseek-flash` 这个名字调 API 返回**空**）
- 批量：**20 段/批**，并发 4 路，278 段 **28 秒**
- prompt 用 `response_format: {"type":"json_object"}`，输入输出都是 `{"<段号>": "文本"}`
- **人名要在 system prompt 里给对照表**（Maldini=马尔蒂尼、Inzaghi=因扎吉、Pirlo=皮尔洛、Nesta=内斯塔、Gattuso=加图索、Ancelotti=安切洛蒂、Shevchenko=舍甫琴科、Kaká=卡卡），否则译名混乱
- 提示词里补一句"原文识别有误就按上下文推测"（ASR 对多人抢话/背景音乐段会出错）

### SRT 生成的两个必须处理的坑

1. **时间戳溢出**：`f'{x%60:06.3f}'.replace('.',',')` 会产生 `00:31:60,000`（非法）。必须用毫秒整数进位：
```python
def ts(x):
    ms = int(round(x * 1000))
    return f'{ms//3600000:02d}:{ms%3600000//60000:02d}:{ms%60000//1000:02d},{ms%1000:03d}'
```
2. **单条过长**：>34 字的句子再按逗号/顿号切分（每片 ≤30 字），否则一屏堆满

---

## 第四步：内嵌（软字幕，秒级）

```bash
ffmpeg -i "$SRC.mp4" -i zh.srt \
  -map 0 -map 1 -c:v copy -c:a copy -c:s mov_text \
  -metadata:s:s:0 language=chi -metadata:s:s:0 title="简体中文" \
  -disposition:s:0 default -y out.mp4
```
93.5 分钟 1080p **2.6 秒**完成（视频流 copy）。验证：
```bash
ffprobe -v error -show_entries stream=index,codec_type,codec_name -of csv=p=0 out.mp4
# 期望看到 2,mov_text,subtitle
```

**兼容性权衡**（交付时要跟用户说清）：
- 软字幕（mov_text）+ AV1：电脑 VLC/PotPlayer/Chrome ✅、新手机 ✅、**老电视/部分播放器 ❌**
- 需要电视能看 → 只能**烧录硬字幕 + 转 H.264**（93 分钟 1080p 重编码，本机约 30-60 分钟，会吃满 CPU）
- 交付时同时给一份独立 srt 备份（放 `/opt/data/subtitles_backup/`，**不要**丢进 `Movie/` 污染目录）

---

## B站视频下载（yt-dlp）

环境里**默认没装** yt-dlp，先装：
```bash
uv pip install --python /opt/data/.venv/bin/python yt-dlp
```
```bash
yt-dlp -f "bv*[height<=1080]+ba/b[height<=1080]/b" \
  --merge-output-format mp4 --write-subs --sub-langs "all" --embed-subs \
  -o "输出路径/%(title)s.%(ext)s" "https://www.bilibili.com/video/BVxxxx"
```
- `--embed-subs` 报 `Invalid data found` + 目录里没有 srt → 说明**该视频本来就没字幕文件**，不是命令写错
- B站默认给 AV1（av01）——兼容性最差，想要 H.264 就指定 `-f "30080+ba"`（1080p avc1）或 `hev1`
- 弹幕会一起下（`.danmaku.xml`），不需要就删

---

## 完整脚本模板

两个脚本（都支持断点续传，可安全重跑）：
- ASR：抽音频 → 20s 切分 → 并发 6 路转写 → `asr.json`
- 翻译：读 `asr.json` → 20 段/批并发 4 路翻译 → `zh.json` → SRT

参考实现：`/opt/data/.tmp_tests/milan_asr.py`、`/opt/data/.tmp_tests/milan_translate.py`

**成本参考**：93.5 分钟音频，ASR 约 280 次调用 + 翻译 14 次调用，SiliconFlow/DeepSeek 合计**几毛到几块钱**。

### ⚠️ ASR 计费纠正（2026-09-21 DSOD-037 实测）

**SiliconFlow 的 Qwen3-ASR 按 `usage.type=duration` 计费（返回 `{"usage":{"type":"duration","seconds":5}}`），NOT 按 token**。且当前是**免费档**——DSOD-037 370 段转写费用 $0。

**翻译才是花钱的地方**：DeepSeek `deepseek-flash` 按 token 计（prompt_tokens 输入 / completion_tokens 输出），从 API `usage` 字段读 token 数，按价目表算（空闲 in 0.02 元/M、out 1-4 元/M）。DSOD-037 实测记录见各次运行日志尾部「成本计量」。

**multipart 字段名是 `file` 不是 `input`**（AC Milan 脚本验证 / DSOD-037 复测）——用 `input` 会 400。

**翻译模型用 `deepseek-flash`**（当前 DeepSeek API 列出的模型），`deepseek-chat` 是旧别名可能空路由；`-- 实测 models 列表只有 `deepseek-flash` 和 `deepseek-v4-pro`。`

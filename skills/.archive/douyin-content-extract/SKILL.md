---
name: douyin-content-extract
description: Use when 抖音链接要提取内容/口播稿/视频信息。解析直链+逐帧OCR还原字幕。
tags: [抖音, douyin, 短视频, 提取文案, 口播稿, 视频转文字, 去水印, 逐帧OCR, 测评视频, 视频信息提取]
trigger: 用户发 v.douyin.com 短链要求提取视频里的内容（品牌清单、价格、口播文案、测评信息），或需要把抖音/B站等短视频里的信息落成文本
---

# 抖音视频内容提取（短链 → 口播稿）

## 何时用
- 用户发抖音分享链接，要「视频里提到的XX产品/价格/清单」
- 需要还原视频口播稿做二次整理（比价、选型、写材料）

## 实测基线（2026-09-28 「大梨花吖」小物竿合集）
9分13秒竖屏视频，端到端约 6 分钟，OCR 成本 **¥0.0752 / 25.06万 token**。

---

## 第一步：短链解析

```bash
UA="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
curl -s -I -L --noproxy '*' -m 25 -A "$UA" "https://v.douyin.com/XXXX/" | grep -iE '^(HTTP|location)'
```
短链 302 到 `https://www.iesdouyin.com/share/video/<item_id>/?...` → 记下 **item_id**。

## 第二步：拿无水印直链（关键）

❌ **不要走这些死路**（实测全部失败）：
| 方式 | 结果 |
|---|---|
| 抓 `iesdouyin.com/share/video/<id>/` 页面 | JS 空壳，`_ROUTER_DATA` 只有 1.4KB，无视频地址 |
| `www.iesdouyin.com/web/api/v2/aweme/iteminfo/` | HTTP 200 但 **size=0** |
| `douyin.com/aweme/v1/web/aweme/detail/` | **403** `Blocked by ArgusSecurityPlugin Uifid Not Found` |
| `yt-dlp` | `ERROR: Fresh cookies (not necessarily logged in) are needed` |

✅ **可用：第三方解析服务**
```bash
curl -s --noproxy '*' -m 30 -A "$UA" \
  "https://api.xingzhige.com/API/douyin/?url=https://v.douyin.com/XXXX/" -o dy_parse.json
```
返回结构（2026-09 实测）：
- `.data.author.name` 作者名
- `.data.item.title` 文案/话题标签
- `.data.item.url` **无水印视频直链**（长度 600-700 字符，注意：很多打印脚本会因「长度>200 就跳过」把它过滤掉，要显式 dump JSON 全部字段）
- `.data.item.duration` / `size` / `width` / `height` / `codec`
- `.data.item.ury` 备用 m3u8/mp4

⚠️ `api.douyin.wtf` 已失效（404）。换服务时先用 `head -c 300` 看返回体确认。

下载：`curl -s --noproxy '*' -A "$UA" -e "https://www.douyin.com/" -L "$URL" -o rod.mp4`

## 第三步：抽帧

```bash
mkdir -p all && ffmpeg -v error -i rod.mp4 -vf fps=1 -q:v 2 all/f%04d.jpg -y
# 竖屏短剧/口播视频按 1fps 足够（字幕每句约 1-3 秒）
```

## 第四步：逐帧 OCR（本管线核心）

### 🚨 最大坑：prompt 决定返回文字还是坐标

`qwen-vl-ocr` 有官方任务关键字，**用错就返回 `x1,y1,x2,y2,90` 这样的坐标框而不是文字**：

| prompt | 返回 |
|---|---|
| `Text Recognition:` | ✅ **文字**（要这个） |
| `Text Detection:` | ❌ 坐标框 |
| `OCR this image. Output only the text you see, line by line, nothing else. If no text, output NONE.` | ❌ 实测返回坐标框 |
| `OCR this image. Output only the text you see, nothing else.` | ✅ 文字（但不稳定） |

**只用 `Text Recognition:`**。跑完先 `head` 看前 5 帧，若出现 `数字,数字,数字,数字,90` 形态立刻停掉改 prompt 重跑。

### 🧪 先抽 10 帧试跑，再跑全量（省一轮 242 秒）

全量 553 帧要 4 分钟，而「画面到底有没有字幕」只要 10 秒就能确认：

```bash
for t in 10 60 120 180 240 300 360 420 480 540; do
  ffmpeg -v error -ss $t -i rod.mp4 -frames:v 1 -q:v 2 -y frames/t$t.jpg 2>/dev/null
done
# 对这 10 帧跑一遍 OCR，先确认输出的是中文而不是 498,878,55,305,90 这样的坐标
```

- 抽出的都是**口播字幕** → 进入全量 OCR
- 抽出的只有贴纸/角标/水印 → **这部片子没烧录字幕，别浪费全量 OCR**，改走 ASR（`ai-subtitle-pipeline`）
- 若看到逗号分隔的 5 个数字 → prompt 用错了，改 `Text Recognition:` 重试

> 实测教训：首轮 prompt 写错了，553 帧全部返回坐标元组，**白跑 242 秒**。
> 10 帧试跑花不到 30 秒，能挡住这类全量浪费。

### 脚本要点
- 端点 `https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions`，model `qwen-vl-ocr-latest`
- **并发 6** 实测最优：553 帧 **242 秒**
- **必须断点续传**（每 20 帧落盘 JSON），失败重试 3 次
- 图片转 base64 内联，`data:image/jpeg;base64,{b}`

参考实现：`/opt/data/.tmp_tests/dy_ocr.py`（改 `OUT` 和 prompt 即可复用）

## 第五步：整理时间轴

按帧号→秒数排序 → 去掉 `NONE`/空 → **合并连续重复**（同一句字幕会连出好几帧）：
```python
if lines and lines[-1][1] == v:
    lines[-1][0].append(t)   # 同一句，追加时间戳
else:
    lines.append([[t], v])
```
输出 `[123s] 文本` 形式，人工读起来就是完整口播稿。

---

## 坑位表

| 坑 | 现象 | 解法 |
|---|---|---|
| OCR prompt 用错 | 返回坐标框不是文字 | 改 `Text Recognition:` |
| 打印长 URL 被过滤 | 找不到视频直链 | 显式 dump 全部字段，别写「长度>200 跳过」的过滤 |
| `python3 x.py \| head -N` | 脚本被 SIGPIPE 杀，**文件没写出** | 输出重定向到文件，不要接 head |
| 脚本路径放错层 | `can't open file '.../dy/dy_ocr.py'` | 确认 cwd 与文件实际目录一致 |
| `nohup ... &` | 被终端守卫拦下 | 用 `terminal(background=true, notify=true)` |
| 本地 rapidocr 精度不够 | 「直男」认成「查男」 | 用百炼 qwen-vl-ocr（贵但准，¥0.08/553帧可忽略） |
| OCR 常见误读 | 「杆子」→「杯子」、「蝉」→「禅」、「柳莺」→「柳荫」 | 品牌/型号名要交叉搜索验证，别直接采信 |

## 成本
百炼 qwen-vl-ocr ≈ 0.3 元/百万 token，单帧约 450 token → **1 秒视频约 ¥0.00014**。10 分钟视频约 ¥0.08。跑完必须汇报 token 数与费用（用户要求）。

---

## 下游衔接：口播稿 → 价格表/清单

提取出口播稿只是中点。用户真正要的往往是「视频里推荐的东西 + 价格」：

1. 从时间轴里拉出**品牌/型号**清单（人工对照原片校正错字，见上表）
2. 把**作者对各款的评价原话**一并留下——用户要的不只是名单，评价直接支撑「买哪个」的决策
3. 查价走 **`cn-shopping-links`** skill（京东价格对匿名访客掩码为 `¥4??`，真实价走 smzdm/淘宝索引）
4. 用户后续要求「按价格排序」时，**必须声明排序依据**（跨平台取最低可得实价 / 京东价 / 淘宝价）——
   总有一部分款拿不到确定价，不声明依据会被追问

完整案例（18 款鱼竿从头到尾、含错字纠正表）见 `references/xiaowugan-18-rods-2026-10.md`。

## 参考

- `references/xiaowugan-18-rods-2026-10.md` — 小物竿案例完整实录：解析元数据字段、
  553 帧 OCR 参数与成本、时间轴节选、OCR 错字纠正表、下游查价衔接

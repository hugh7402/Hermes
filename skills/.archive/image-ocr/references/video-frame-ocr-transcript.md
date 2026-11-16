# 视频逐帧 OCR → 还原口播稿（抖音实测，2026-10-01）

**任务形态**：用户丢来一条抖音/短视频链接，要求「把视频里提到的 N 个东西整理出来」
「列出视频里的清单」「视频讲了什么」。视频没有字幕文件可选，字幕是**烧录在画面里**的。

实测案例：「大梨花吖」小物竿测评（9 分 13 秒 / 553 秒 / 29.15MB / 576×768 hevc / 30fps），
任务是从视频里扒出 20+ 款鱼竿型号 → 再去电商查价列表。

---

## 第一步：拿到视频文件

### 抖音访问链（层层设卡，按序试，别在官方 API 上耗时间）

| 环节 | 实测结果 |
|---|---|
| ① 短链 `https://v.douyin.com/<code>/` | ✅ 302 → `https://www.iesdouyin.com/share/video/<item_id>/?...`，**item_id 就在 location 里** |
| ② 分享页 `iesdouyin.com/share/video/<id>/` | ⚠️ **JS 空壳**：HTTP 200 但正文 32KB，`_ROUTER_DATA` 只有 ~1.4KB（仅 ua/webId/query 等壳字段），**无视频地址** |
| ③ yt-dlp | ❌ `ERROR: [Douyin] <id>: Fresh cookies (not necessarily logged in) are needed` |
| ④ `douyin.com/aweme/v1/web/aweme/detail/` | ❌ 403 `Blocked by ArgusSecurityPlugin Uifid Not Found`（iesdouyin 同款接口同样 403）|
| ⑤ 旧接口 `/web/api/v2/aweme/iteminfo/` | ❌ HTTP 200 但 **size=0**（已下线）|
| ⑥ **第三方解析服务** | ✅ **唯一可行**，见下 |

### ✅ 可用：第三方解析服务拿无水印直链

```bash
UA="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
curl -s --noproxy '*' -m 30 -A "$UA" \
  "https://api.xingzhige.com/API/douyin/?url=https://v.douyin.com/<code>/" -o parse.json
```

返回 JSON 关键字段：

| 字段 | 内容 |
|---|---|
| `data.item.url` | ✅ **无水印视频直链**（约 680 字符，`v5-...douyinvod.com/...mp4`，带 `mime_type=video_mp4`）|
| `data.item.ury` | 另一条 CDN 地址（备用）|
| `data.item.title` | **完整文案**（含 `#话题标签`）——可直接交付给用户 |
| `data.author.name` / `short_id` | 作者名 / uid |
| `data.item.duration` / `size_str` / `quality` | 552.8 / 29.15MB / 540p |
| `data.stat.like` / `comment` / `collect` | 互动数据 |
| `data.item.cover` / `cover_gif` | 封面图 |

**坑**：dump JSON 时**不要写 `if len(s) < 200` 这类长度过滤**——视频直链是长字符串，会被过滤掉，
导致误以为「解析器没返回视频地址」。直接 `json.dumps(..., indent=1)` 原样看。

**换站兜底**：`api.douyin.wtf` 同款用法返回 404 `The requested resource does not exist`。
第三方站会失效，解析失败就换下一个，不要死磕。

### 下载视频

```bash
curl -s --noproxy '*' -m 120 -A "$UA" -e "https://www.douyin.com/" -L "<data.item.url>" -o v.mp4
# 实测 HTTP 200，29,154,469 字节 == size_str 报的 29.15MB，无水分
```

---

## 第二步：抽帧 + 批量 OCR

```bash
mkdir -p frames
ffmpeg -v error -i v.mp4 -vf fps=1 -q:v 2 frames/f%04d.jpg -y   # fps=1 → 第 N 帧 = 第 N 秒
```

并发 6 路调百炼 `qwen-vl-ocr-latest`，**prompt 只用裸 `Text Recognition:`**
（带修饰的 prompt 会翻成坐标模式，实测 553 帧全废，见 SKILL.md）。

**实测基线**：
- 553 帧 / 并发 6 → **199–242 秒**
- 消耗 **250,554 tokens ≈ ¥0.0752**（0.3 元/M）
- 断点续传：每 20 帧落盘 JSON，失败重试 3 次（脚本可安全重跑）

**字幕位置**：抖音竖屏字幕固定在底部 **85%–91% 高度**（实测 `y=652-700 / 768`）。
全帧 OCR 就能抓到，**不必裁切、不必降采样**。

---

## 第三步：拼时间轴 / 还原口播稿

```python
import json, re
d = json.load(open('ocr_text.json'))
items = sorted(((int(re.search(r'(\d+)', k).group(1)), v) for k, v in d.items()))
# 相邻帧文字相同 → 合并成一段，记 [起-止 s]
```

输出形态（553 帧 → **467 段带时间戳的口播稿**）：

```
[ 14s] 首先是campfish
[ 15s] 这个糖葫芦杆
[ 16s] 新手入门推荐糖葫芦杆
...
[480s] 一整套下来才100多
```

---

## 交付形态

1. **视频元信息**：作者、标题文案（含话题标签）、时长、发布日期 —— 从解析 JSON 直出，**不是 OCR**
2. **口播稿/清单**：OCR 还原的带时间戳文本，按视频顺序编号
3. **成本**：告知 token 数与估算费用（用户要求 AI 类工作必须精确计量并汇报）
4. **形近字纠正表**：把 OCR 误识别与正确写法对照列出（如 `北禾禅`→`北禾蝉`、`杯子`→`杆子`），
   并说明核对依据（淘宝/京东商品名）
5. 中间产物（`timeline.txt` / `ocr_text.json`）留在 `.tmp_tests/`，并在回复中给出路径

---

## 后台任务的判断纪律

- 后台脚本**输出重定向到日志文件**，别用 `| head -N` 截管道（SIGPIPE 会杀掉脚本，产物静默丢失）
- **不要用 `tail *.log` 判断进程状态**：日志是上一轮残留时会把旧报错显示给你，误判成「又失败了」。
  用 `process(action='poll', session_id='proc_xxx')` 看真实状态
- 脚本路径别写错目录（写的是 `A/x.py` 却 `cd A/dy` 跑 `x.py` → `No such file or directory`）

---
name: offline-web-bundle-inspection
title: 离线 Web 包 / 大屏演示包解析与截图
description: Use when 用户发来 zip 离线便携包/大屏驾驶舱/作战图，Mac 打不开，要解析内容并截图。
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [离线包, 驾驶舱, 大屏截图, printToPDF, 字体, 作战图]
    related_skills: [demo-launch-package, china-gov-ui-standards, xlsx]
---

# 离线 Web 包解析与截图

## When to Use

- 用户发来 ZIP，里面是「离线便携包 / 驾驶舱 / 作战图 / 演示大屏」，说 Mac 或本机打不开
- 需要把别人的大屏、看板、作战图**还原成可看的内容与截图**，再比对、出清单
- 拿到一份「页面 + Excel/JSON 快照」的交付包，要快速搞清它的数据骨架

不适用：包内只有静态图片/PDF（直接走 ocr / docx 类 skill），或用户要你**生产**一个新的演示包
（那是 `demo-launch-package`）。

## 1. 清点，先判断“为什么打不开”

用 Python `zipfile` 解开（环境常有 zipfile 无 `unzip` 二进制），别在压缩包预览里试运行：

```python
import zipfile, pathlib
from collections import Counter
out = pathlib.Path('/opt/data/.tmp_tests/<项目名>'); out.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(SRC) as z:
    info = z.infolist(); z.extractall(out)
rows = sorted(((p.stat().st_size, str(p.relative_to(out))) for p in out.rglob('*') if p.is_file()), reverse=True)
print(len(info), '条目'); print(Counter(pathlib.Path(n).suffix.lower() or '(无)' for _, n in rows))
for sz, n in rows[:20]: print(f'{sz/1024**2:8.2f}MB  {n}')
```

**看到这些就说明“不是文件坏了，是平台不对”，直接告诉用户，别当成损坏**：
`runtime/node.exe`、`*.exe`、`启动*.cmd`、`*.ps1` —— Windows 便携包自带 Node 运行时，Mac 跑不了 exe。

同时读掉说明文件（`便携离线包说明.txt` / `README.md` / `*.yaml`），里面通常写明有哪些页面、监听哪个端口、是否只读。

## 2. 找“真正的数据源”，不要只看页面

这类包的页面是壳，数据在两层：

- `原始表格/` 或 `data/`：**源头 Excel / JSON 快照**（最全，报表结构都在这里）
- `app/private/*.json`：页面实际读的快照

用 openpyxl 列工作表清单（`read_only=True, data_only=True`，不要整表加载），JSON 只看顶层结构和样例字段：

```python
from openpyxl import load_workbook
wb = load_workbook(p, read_only=True, data_only=True)
for ws in wb.worksheets: print(f'{ws.title} | {ws.max_row} 行 × {ws.max_column} 列')
```

**sheet 名 + 行数就是这套东西的骨架**，比截图信息量大得多（能直接看出：任务分几级、指标分几档、字典表有几张）。
大表打印前几行表头即可，不要 dump 全部数据进上下文。

## 3. 起本地静态服务（根目录要选对）

```bash
cd "<解压目录>/app" && /opt/data/.venv/bin/python3 -m http.server 18080 --bind 127.0.0.1   # background=true
```

页面用相对路径读 `../private/xxx.json`，所以**服务的根必须是 `app/`，不是 `app/public/`**；
否则页面能显示但各处报“数据未能载入”。原包里那些 Node 后端接口是拿不到的，看到某个面板空着先判定为“需要接口”，
**不要当成解析失败**，数据以第 2 步的表格为准。

## 4. 中文字体（否则截图全是豆腐块 □）

先查：`fc-list :lang=zh | wc -l` —— 为 0 就不要急着截图，装字体（用户级，无需 root）：

```bash
mkdir -p /opt/data/home/.fonts && cd /opt/data/home/.fonts
curl -sL --max-time 120 -o NotoSansCJKsc-Regular.otf \
  "https://cdn.jsdelivr.net/gh/notofonts/noto-cjk@main/Sans/SubsetOTF/SC/NotoSansSC-Regular.otf"
stat -c%s NotoSansCJKsc-Regular.otf        # 要求 >1MB，几百字节说明下到的是错误页
fc-cache -f /opt/data/home/.fonts && fc-list :lang=zh | wc -l
```

**装完必须把浏览器进程全杀掉重开** —— fontconfig 只在进程启动时读缓存，光重载页面还是豆腐块。
页面 `font-family` 常见写法是 `"Microsoft YaHei","Noto Sans SC",sans-serif`，装了 Noto Sans SC 就能命中。
装完先验一句 `fc-match -f '%{family}' 'Noto Sans SC'`（应回 Noto Sans SC，回 DejaVu 说明没生效）。

**还有一个漏网情况**：`fc-match sans-serif` 仍会解析到 DejaVu Sans（无中文）。页面只声明 `sans-serif` 而没有具体字体名时，
即使装了 Noto 也照样豆腐块——这时在 `~/.config/fontconfig/fonts.conf` 加一条 prefer，把 `sans-serif` 首选指向 Noto Sans SC，
`fc-cache -f` 后重启浏览器。文件里 `.ttf/.otf` 放 `~/.fonts`（用户级，无需 root）。

## 5. 截图取证：重页面用 printToPDF，不要硬截 PNG

单页 HTML 做到 10MB+ 时，`Page.captureScreenshot`（PNG 全页 / JPEG）会**等到 60s 超时**；
`Page.printToPDF` 又快又稳，再用 PyMuPDF 转 PNG：

```python
import base64
info = js("(() => ({h: document.documentElement.scrollHeight, txt: document.body.innerText.length}))()")
ph = min(max(info['h'] / 96.0 + 0.4, 7.0), 40.0)          # pt，按滚动高度算，别用默认 A4
r = cdp('Page.printToPDF', printBackground=True, paperWidth=16.0, paperHeight=ph,
        marginTop=0, marginBottom=0, marginLeft=0, marginRight=0)
open(out_pdf, 'wb').write(base64.b64decode(r['data']))    # <2KB 说明页面没加载，先查 page_info()
```

- **`paperHeight` 必须按 `scrollHeight/96` 算**，用默认纸张会把内容切到第 2 页，而第 1 页常常是空白（几十 KB）——
  转 PNG 后挑**体积大的那页**，那才是有内容的。
- 先用 `page_info()` 确认当前 tab 的 URL 不是 `about:blank`；每次导航后 `wait_for_load()` 再等 6–10s（这类页面首屏慢）。
- 转图用 `scripts/pdf_to_png.py`（`python3 scripts/pdf_to_png.py <pdf或目录> --dpi 140`）。
- 要贴给用户时一次 3–5 张，选**信息密度最高的**（总览/驾驶舱/主表），不要每页都发。

## 6. 取文字用 innerText，比看图准

`js("document.body.innerText")` 拿到的是页面真实文字，**比视觉模型识图准确、便宜得多**，也绕开字体/分辨率问题。
只有判断版式、图形、配色时才用 vision。两者结合：innerText 定性（有哪些模块、多少指标），vision 定量（版式关系、分区）。

🚨 **vision 对密集小字会“言之凿凿地错”，结构类结论一律回代码里核一遍再回话。** 实测两类误报：
一是**无中生有**——对着 28px 的周列报“2月22 之后直接跳到 3月7，缺 3月14”，实际周轴连续、间隔全是 7 天；
二是**同音/形近误读**——“数重”（供应商名）读成“数量”，“年化”被当成错别字。
所以凡是要说“缺了 / 错位 / 跳号 / 不一致”之前，先在 JS 或 Python 里把数拿出来：
`[...document.querySelectorAll('thead th')].map(t => t.textContent + '/' + t.colSpan)`、
`STATE.weeks.length`、相邻元素差值是否恒为 7 天、总数与分段之和是否相等。
**数字对得上 → 不下“缺失”结论；对不上 → 用代码的证据说话。**
vision 只用来判断它擅长的东西：版式拥挤、文字被裁切、颜色语义被误读、图例与图形不一致。

## 7. 交付形态：先给“清单”，不要直接开工

用户说“根据它做我们自己的 X”时，他要的是**输入清单**，不是马上出图。固定分三段给：

1. **它的骨架**：分几层模块、几个维度、任务分几级、指标落到什么粒度、靠哪些字典表自动汇总（字典表是自动算百分比的前提，最容易被忽略）。
2. **与我方的差异**：一张对照表（定位/时间轴/任务分解/指标/可视化/数据底座），并明确“不要在同一个图里混两件事”。
3. **生成我方版本的清单**：分「必须具备」「最好能有」「需要你拍板的技术形态」；每条都写**现状 + 缺口 + 谁来补**，缺的标“没有/待补”，绝不编数字。

## 坑

- **保密件一律本地解析**，不传网盘、不建 cron；读图会调用视觉模型，交付时明确说一句“文件未上传，仅识图调用了视觉模型”。
- **杀浏览器进程按 `argv[0]` 的 basename 精确匹配**（`chrome`/`chromium`/`headless_shell`），并跳过 `os.getpid()`。
  用「命令行里出现过某关键字」来筛 `/proc/*/cmdline` 一定会匹配到自己那条 `bash -c`，把自己 SIGKILL 掉（命令 exit `-9`，看起来像环境崩溃）。
- **不要相信包里的 `.cmd`/`.ps1` 说明当运行依据**，它们只对 Windows 成立；Linux 下直接走静态服务。
- 分页导出时 `.pdf` 体积 <2KB = 页面没起来，先修加载再谈内容。

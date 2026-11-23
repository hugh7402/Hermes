---
name: ppt
description: Use when 做/改中文PPT：选模板→路由场景→出原生可编辑 .pptx。
version: 1.1.0
author: Emma
created_by: agent
license: MIT
tags: [PPT, 幻灯片, 演示文稿, pptx, 美化, 重绘, 排版, 模板]
trigger: 当用户说“做PPT”“改PPT”“美化PPT”“重新排版”“用这个模板生成PPT”“单页设计”“出几页PPT”“把文档做成PPT”“做个演示文稿”时加载
metadata:
  hermes:
    tags: [PPT, 幻灯片, 演示文稿, pptx, 美化, 重绘, 排版, 模板]
    category: creative
---

# PPT（唯一入口）

做、改、美化中文 PPT 全部走本 skill。引擎是 **ppt-master**，仓库在
`/opt/data/ppt-master-repo/ppt-master-main/`（引擎完整工作流：`skills/ppt-master/SKILL.md`，719 行，需要细节时再读）。

> 🚨 **动手前先看这里的迭代纪律**：SVG 是单项最大开销。**先出文字版式稿**（分区/色块/配色/层级三五行）让用户点头再写 SVG；换设计方向前先确认，不要直接开工整份重写。预览图渲 1280–1400px 即可，别用 1600/1920；**不要每版都跑 vision**，小改动先用几何断言自验（越界/字宽折算/色板正则），只在交付前看一次图。改坐标、字号、颜色一律**字符串替换**，不整份重写。

## When to Use

- 「做PPT／出几页PPT／把这份文档做成PPT」——从材料生成
- 发来 `.pptx` 模板 ＋ 材料，说「用这个模板生成／填回去」——套模板生成
- 发来 `.pptx` 说「美化／重新排版／内容不动／不够好看」——beautify
- 成品要加备注、配音、自动播放、切换——native-enhance
- 只有主题没材料——先 topic-research

不适用：纯网页/HTML 的「幻灯片风格」页面（走 `baoyu-design` / `ui-prototype`）。

---

## 一、先选模板（不要默认用某个）

**先读模板库清单：`/opt/data/ppt-templates/` 目录下的 `REGISTRY.md`，把可选模板列给用户挑。**

- **自有模板**：`数智公司`（联通红＋微软雅黑，公司汇报默认候选）——规范见 `数智公司/TEMPLATE.md`
- **ppt-master 自带布局**：`government_blue`／`government_red`（政务）、`ai_ops`、`academic_defense`、`medical_university`、`psychology_attachment`、`pixel_retro`
- **品牌预设**：`中国电建`、`中汽研`、`anthropic`、`google`
- 用户没指定且是内部汇报 → 推荐 `数智公司`，但要问一句确认

新增自有模板：.pptx 放进 `/opt/data/ppt-templates/<ID>/` → 跑 `pptx_intake.py` → 写 `TEMPLATE.md` → REGISTRY 加一行。

---

## 二、按场景路由（确定性规则，不要问用户选哪个）

| 用户给了什么 | 管线 | 契约 |
|---|---|---|
| 源材料（PDF/DOCX/MD/URL）＋ 要 pptx | **A 主流程** | 逐页手写 SVG → 导出原生 DrawingML |
| raw `.pptx` 模板 ＋ 新材料 | **B 套模板** | 基于母版生成，或 `template-fill` 克隆源页改字；**不走 SVG** |
| 已有 `.pptx` ＋「美化／重排／内容别动」 | **C beautify** | 严格 1:1：页数、页序、**逐字冻结**，只重做版式 |
| 成品加备注/配音/自动播放/切换 | **D native-enhance** | 不动内容与版式 |
| 只有主题无材料 | `topic-research` → 再进 A | |
| 要改页数/合并/拆分/换故事线 | **A 主流程** | 动了页数就绝不是 beautify |

**唯一该反问的情形**：用户只说「把这份 PPT 做得专业点」。问一句：「保留原页数页序和每页文字，还是当素材重新组织成新故事？」保留→C，重构→A。

---

## 三、管线 A：从材料生成（主流程）

**A1 取内容** — 非 Markdown 先转：
```bash
S=/opt/data/ppt-master-repo/ppt-master-main/skills/ppt-master/scripts
python3 $S/source_to_md/pdf_to_md.py  <file>    # PDF
python3 $S/source_to_md/doc_to_md.py  <file>    # DOCX/EPUB/HTML/RST
python3 $S/source_to_md/excel_to_md.py <file>   # XLSX
python3 $S/source_to_md/ppt_to_md.py  <file>    # PPTX
python3 $S/source_to_md/web_to_md.py  <URL>     # 网页（需 curl_cffi）
```
只有主题没材料 → 先跑 `workflows/topic-research.md`。

**A2 大纲（用户审核点，不可跳）** —
```bash
cd /opt/data/humanize-ppt && python3 humanize_ppt_v2.py \
  --source <source.md> --out <outdir> --title "<标题>" \
  --renderer ppt-master --lang zh --preview-outline
```
把每页标题和要点完整呈现给用户，**等确认**后再渲染。用户提意见就改 source.md 重跑。

**A3 建工程 + 导源** —
```bash
python3 $S/project_manager.py init <name> --format ppt169
python3 $S/project_manager.py import-sources <proj> <files> --move
```

**A4 设计规范（八项确认，等用户点头）** — 画幅／页数／受众／风格／配色／图标／字体／图片方案。

**A5 逐页手写 SVG** → `<proj>/svg_output/slide_NN.svg`
> 🚨 SVG 必须主智能体手写，**禁止脚本批量生成**（会丢跨页一致性）。每页前重读 `spec_lock.md`。图片信息只从 `analyze_images.py` 输出取，不直接 open 图片。

**A6 质检 → 后处理 → 导出** —
```bash
python3 $S/svg_quality_checker.py <proj>
python3 $S/total_md_split.py     <proj>     # 演讲备注（有的话）
python3 $S/finalize_svg.py       <proj>     # 图标内嵌/圆角转路径
python3 $S/svg_to_pptx.py        <proj>     # 输出 exports/<name>_<ts>.pptx
```

**A7 导出后处理与校验（必做，不能省）** — `svg_to_pptx` 的产物有两处必须修，直接交付会踩：

```bash
python3 /opt/data/skills/creative/ppt/scripts/pptx_postfix.py \
    "<导出.pptx>" --font "Microsoft YaHei" --logo <品牌logo.png> \
    --palette E60012 A0000C F04A55 FBD5D8 FDF3F4 1A1A1A 595959 FFFFFF
```

它一次做完三件事，也可以 `--verify-only` 只校验：

| 要做 | 为什么 |
|---|---|
| **统一 latin/ea/cs 字体** | `svg_to_pptx` 把每个 run 的 latin 写成 **`Segoe UI`**。中文有 eastAsia 兑着看不出来，但数字/英文/页码会挂到 Segoe UI 上，**macOS 无此字体 → 掉字回退** |
| **补回品牌 logo** | SVG 管线不走母版，logo/装饰线/页码不在成品里，须 `add_picture` 补并提到 `spTree` 顶层 |
| **递归校验文本** | 导出会把相关形状压成 **GROUP**，只迭代 `slide.shapes` 顶层查不到组内文字，会误判成“文字丢了” |

交付前把全文打印出来逐一比对源文档，内容完整性用计数断言，不要凭印象说“都在”。

---

## 四、管线 B：套模板生成

| 情况 | 做法 |
|---|---|
| 模板**有正文占位符** | `workflows/template-fill-pptx.md`：克隆选中源页，OOXML 里直接改文字/表/图 |
| 模板**只有标题槽**（如数智公司） | 用 python-pptx 基于母版 `add_slide(layout)` 拿到品牌元素（红线条/logo/页码），正文自行排布形状 |
| 想要 SVG 自由设计 | `workflows/create-template.md` 先生成可复用模板包，再进 A |

先跑 intake 看清槽位再决定，**不要凭感觉**：
```bash
python3 $S/pptx_intake.py <tpl.pptx> -o <proj>/analysis
# → <stem>.identity.json（配色/字体/字号/实测用量）
# → <stem>.slide_library.json（每页 slots + 坐标）
# → source_profile.json
```

---

## 五、管线 C：美化现有 PPT（beautify）

严格 1:1：**文字逐字冻结**（不加/删/改/调序），只重做版式/层级/留白。
流程见 `workflows/beautify-pptx.md`（258 行）。要点：

```bash
python3 $S/beautify_identity.py <source.pptx>        # 读 canvas.aspect 定 format
python3 $S/project_manager.py init <name> --format ppt169
python3 $S/project_manager.py import-sources <proj> <source.pptx> --move
# 取冻结文本：sources/<stem>.md（import-sources 已跑 ppt_to_md，不要重复跑）
# 身份：analysis/<stem>.identity.json
# 图表数据：analysis/<stem>.slide_library.json
python3 $S/beautify_inventory.py <proj>/analysis/<stem>.slide_library.json \
    --images <proj>/images/image_manifest.json -o <proj>/analysis/beautify_inventory.json
# → 然后 A5~A6（手写 SVG → 导出）
```

图表/表格**按数据重画**，不要把原图原样搬进去；数据值冻结。

---

## 六、🚨 美化好不好看，先看问题在哪

“不够好看”的常见病根不在配色，而在**结构**：

| 病 | 改法 |
|---|---|
| 十个等权卡片排成两行 | 建立**视觉重心**：让一块区域塔当锚点（深色区/大字号） |
| 全文灰字堆叠 | 把关键数字抬成**红色/大字号锚点** |
| 全靠卡片方框分隔 | 改用**对齐、留白、发丝线**分隔，轻盈得多 |
| 上下两段版式雷同 | 差异化：一段横向列（无框）、一段纵向行（浅底条） |
| 各区块边缘参差 | 发丝线端点、区块右边线**全部对齐到同一基准** |
| 标题重复/语义叠床架屋 | 左栏主标题就别再写一次右栏小节名 |
| 用随文「｜」串起两段信息 | 分隔符会随字长左右漂移，竖向看是锯齿。改**固定两栏**：左栏宽固定、分隔线 x 统一、右栏起点 x 统一 |
| 侧栏内容上密下空 | 别把末块硬压到底：要么把末块上提让留白均分，要么放大装饰元素锚住底部 |
| 五行条里用随文「｜」串左右两段 | 分隔符随字长漂移成锯齿。改**固定两栏**：左栏宽固定、分隔线 x 统一、右栏起点 x 统一 |

### 色块与配色（用户硬偏好，每次都适用）

- **可以用大色块，但绝不能用大面积高饱和红。** 整栏铺满联通红 `#E60012` 会刺眼，会被明确要求拆掉。
- **深色竖栏不是通用解**。左侧深色锚柱（石墨黑灰那类）是互联网后台/App 的观感，国企与政务汇报里会被判「有点互联网风格，我们是国企，要以稳重传统为主」。分量靠**浅色分区块 ＋ 明确层级**撑，不靠把一整条竖栏刷深。
- **标题区不要色块**。白底黑字大标题（21–22px 粗体、左对齐）＋ 通栏细红线（1.5–2px）＋ 右上角品牌 logo，就是标准解。红色大色块标题带（红头式）同样会被要求拆掉。
- 分区色块用极浅红 `#FDF3F4` 打底，配 `#E60012` 顶部细条或左侧 3.5px 窄条；某一段的标签可以用一小块实心红（约 78×26px、白字居中）——**小块实心可以，大面积铺红不行**。
- **红色降级为强调**：只出现在编号、名称下短横、关键数字、发丝线、页码、极窄边条。
- 反过来，全白＋细线也别走极端——会被评价「太素雅」。但「太素雅」的解法是**加浅色分区块，不是加回深色锚柱或红头带**（这两条路都被明确否过）。正确做法：全白底 ＋ 3–5 处 `#FDF3F4` 浅色分区块（列底/行底/通栏带），红色只做细顶条与窄边条，靠**分区块的数量与节奏**撑分量，整页不出现大面积深色或高饱和红。
- 深色底上的辅助小字透明度**不低于 0.74**（标题/正文 0.85+）。低于这个值投影时会糊成一片，浅色底上看不出来。
- 交付前跑色板断言：正则扫 `srgbClr val=` 逐个比对允许色板，多一个冷色就说明某处漏改。

具体版式参数（画幅、栅格、四种版式的实测坐标与采纳结论）见 `references/cn-slide-layouts.md`。

---

## 七、🚨 SVG 管线特有优势：能先看到成品

本机 **无 `soffice`**，pptx/docx 渲不出图；**但 SVG 能用 cairosvg 渲染**，这就是走 A/C 管线的最大好处：

```python
import pathlib, cairosvg
src = pathlib.Path('svg_output/slide_01.svg').read_text(encoding='utf-8')
# Linux 上没有微软雅黑，预览时换成 Noto Sans SC（交付的 SVG 仍留微软雅黑）
prev = src.replace('font-family="微软雅黑"', 'font-family="Noto Sans SC"')
pathlib.Path('/tmp/_prev.svg').write_text(prev, encoding='utf-8')
cairosvg.svg2png(url='/tmp/_prev.svg', write_to='preview.png',
                 output_width=1600, output_height=900)
```
随后 `vision_analyze(preview.png)` 严格挑毛病（溢出/重叠/对齐/层级/拥挤），改完重渲。
**交付前至少看一遍图**，不要盲交。

🚨 **但 vision 只能信它看见的结构，不能信它读出的文字**。它会凭空“发现”错别字（把「一件事」读成「一事件」）。任何“某处文字有误／建议改写”的结论，**先在源文件里 grep 核实**再动；对不上就是它读错了，不要改。同样，它说“对齐不齐／间距不均”时也先看你自己写的坐标是否真的相等——坐标是硬事实，观感是估计。

---

## 八、中文硬规范

**中文字体必须写 eastAsia**，`run.font.name` 只写 latin，中文在 PowerPoint 里静默回退宋体：

```python
from pptx.oxml.ns import qn
def cnfont(run, name='微软雅黑'):
    run.font.name = name                 # a:latin
    rPr = run._r.get_or_add_rPr()         # ⚠️ 是 ._r，不是 ._element
    for tag in ('a:ea', 'a:cs'):          # 顺序 latin → ea → cs
        el = rPr.find(qn(tag))
        if el is None:
            el = rPr.makeelement(qn(tag), {}); rPr.append(el)
        el.set('typeface', name)
```
验：`len(re.findall(r'<a:r>', x)) == len(re.findall(r'<a:ea typeface=', x))`。
SVG 里用 `font-family="微软雅黑"`，导出后 PowerPoint 正确显示。

**无渲染器时的几何断言**（python-pptx 路线用）：
1. 越界：所有形状在画幅内
2. 文字容量：中文按「字宽 ≈ 字号」，`每行字数 = 框宽/(字号/72)`，行高 `字号×1.30`，累计高 ≤ 框高
3. 图片形状数：要可编辑时断言 `PICTURE` 数为 0，并查 `slide1.xml.rels` 无图片引用
4. 颜色断言：正则扫 `srgbClr val=` 比对允许色板

---

## 九、陷阱（都踩过）

1. **`sl.shapes.title` 可能返回 `None`**。占位符类型是 `BODY` 而非 `TITLE` 时静默拿不到，**标题会丢且不报错**。必须 `list(sl.placeholders)` 迭代取。`sl.placeholders[0]` 是按 `idx==0` 查，会 `KeyError`。
2. **删模板原有页要连 rel 一起删**：`prs.part.drop_rel(sid.rId)` 再 `lst.remove(sid)`；只删后者留悬挂引用。
3. **母版元素不在 `slide.shapes` 里**：红线条/logo/页码来自 layout/master，`slide` 上图片形状为 0 是正常的，别误判成丢了品牌元素。
4. **cairosvg 缺失会静默降级**：优先 cairosvg → 退 svglib → 都无则 `PNG_RENDERER=None`，带图页面渲染失败。装 `cairosvg` 后验 `pptx_media.PNG_RENDERER == 'cairosvg'`。
5. **SVG 文本不自动换行**，必须手写 `<tspan dy>` 分行，并按字宽算好每行长度。
6. **一页塞 800+ 字偏满**，宁可给余量或建议拆页，别硬挤。
7. **模型**：硅基流动已 402 欠费，**不要用 DeepSeek-V4-Pro**。用 DeepSeek 官方 `deepseek-chat`（备百炼 `qwen-plus`），大纲需 `max_tokens ≥ 8000` 且校验 content 非空、`finish_reason != length`。
8. **`svg_to_pptx` 产物字体是 `Segoe UI`**：不修的话中文看着正常、数字英文在 Mac 上掉字。见 A7。
9. **组内文字查不到**：导出的 GROUP 里的文本用 `slide.shapes` 顶层迭代拿不到，校验一律递归展开（`scripts/pptx_postfix.py` 的 `walk()`）。
10. **`cp`/`open` 到 `/opt/data/OutPut Box` 必须加引号**：目录名带空格，不加会报 `No such file or directory`，且报错点在 `cp` 而非后续 python，容易被当成路径不存在。
11. **`write_file` 拒绝覆盖已存在的 SVG**：迭代改稿时写新文件名再 `mv` 覆盖，不要试图原地重写。

---

## 十、命令速查

```bash
S=/opt/data/ppt-master-repo/ppt-master-main/skills/ppt-master/scripts
SKILL_DIR=/opt/data/ppt-master-repo/ppt-master-main/skills/ppt-master

python3 $S/pptx_intake.py <tpl.pptx> -o <proj>/analysis
python3 $S/beautify_identity.py <src.pptx>
python3 $S/beautify_inventory.py <lib.json> --images <manifest.json> -o <out.json>
python3 $S/project_manager.py init <name> --format ppt169
python3 $S/project_manager.py import-sources <proj> <files> --move
python3 $S/svg_quality_checker.py <proj>
python3 $S/total_md_split.py <proj>
python3 $S/finalize_svg.py <proj>
python3 $S/svg_to_pptx.py <proj>
python3 $S/image_gen.py --manifest <proj>
python3 $S/image_search.py <query>

# 导出后处理 + 校验（统一字体/补logo/递归校验，A7 必做）
python3 /opt/data/skills/creative/ppt/scripts/pptx_postfix.py <out.pptx> \
    --font "Microsoft YaHei" --logo <logo.png> --palette <色值...>
```

## 十一、依赖自检

```bash
/opt/data/.venv/bin/python3 -c "import pptx,PIL,fitz,lxml;print('ok')"
/opt/data/.venv/bin/python3 -c "import cairosvg;print('cairosvg',cairosvg.__version__)"
/opt/data/.venv/bin/python3 -c "import sys;sys.path.insert(0,'$SKILL_DIR/scripts');from svg_to_pptx import pptx_media;print(pptx_media.PNG_RENDERER)"
fc-list :lang=zh family | head    # 应有 Noto Sans SC
```

## 十二、改完回写

发现 ppt-master 工作流/命令与实际不符，patch 本 skill，别只在会话里记住。新建了模板就往 REGISTRY.md 里加。

## 附：支持文件

| 文件 | 用途 |
|---|---|
| `scripts/pptx_postfix.py` | 导出后处理与校验：统一 latin/ea/cs 字体、补品牌 logo、递归校验组内文本/越界/色板 |
| `references/cn-slide-layouts.md` | 单页版式库：画幅栅格、四种版式的实测坐标、采纳与否决结论、一页容量上限 |

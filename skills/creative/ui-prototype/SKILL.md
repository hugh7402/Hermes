---
name: ui-prototype
description: "Use when 用户要画产品原型/交互原型/UI原型/线框图/可点击演示。HTML 单文件交付 + jsdom 无头验证。"
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [原型, 交互原型, UI, 线框图, HTML, WeasyPrint, jsdom, 可点击]
    trigger: 用户说"画原型"、"产品原型"、"交互原型"、"可点击原型"、"界面设计"、"线框图"、"原型图"、"做个demo页面"、"页面能点吗"、或者对标 WorkBuddy原型skill、huashu-design、prd-html-skill 时加载
---

# 产品原型图生成（HTML/CSS → PDF/PNG，无需浏览器）

## 先选路线（按保真度/交互性）

| 需求 | 路线 | 依赖 | 说明 |
|---|---|---|---|
| **静态原型图**（贴方案/汇报文档） | **HTML+CSS → WeasyPrint → PNG** | `weasyprint`(已装) + `fitz`(已装) | **默认选这个**，保真度高、中文无问题、出图快 |
| **可点击交互原型** | 手写单文件/多文件 HTML，交付**源文件**让用户本地打开 | 零依赖 | 我无法渲染交互，只能出静态图；交互靠 `<a href>`/JS 在用户浏览器里跑 |
| 手绘风线框图/草图 | `excalidraw` skill | 产出 `.excalidraw` JSON | 用户在 excalidraw.com 打开并可自行拖动编辑 |
| 需在 PowerPoint 里继续改 | `ppt-master` skill | 原生 pptx DrawingML 形状 | 图元可拖拽，适合交付给非技术人员改 |

### 本机已装的两个重型设计技能（2026-10-07 装，均 MIT）

**需要「UI 好看」或整套设计体系时，优先用它们**，而不是本 skill 的手摶路线：

| 技能 | 定位 | 何时用 | 本地状态 |
|---|---|---|---|
| **`baoyu-design`** | Anthropic **Claude Design** 引擎的本地版（宝玉打包） | 要 hi-fi mockup / 交互原型 / 整套设计系统 / 多形态（App、Dashboard、落地页、Deck）；要导出 PPTX | 全套已装（200 文件）。含 node 脚本（Figma 导入 / 设计系统编译 / PPTX 导出） |
| **`huashu-design`** | 花叔Design，中文原生，⭐24.6k | 需要**先出三个方向让你选**、反 AI 味、5 维评审、中文语境 | **裁剪版**：只有 SKILL.md + references/。**scripts/ 与 assets/ 未装** → 导出 PPTX/PDF/MP4/GIF、配音、Playwright 验证**不可用** |

⚠️ **两者都假设「交付前用浏览器验证」，本机无 chromium** → 验证环节改用本 skill 的 **jsdom 无头测试**方案（`node test_proto.js`，见上文），不依赖浏览器。
⚠️ **质量主要取决于模型**：baoyu-design 明确写 “Best with Opus 4.8”。用弱模型跑，方法链路照走，但视觉品味会打折 —— 先跟用户说清楚。

## 本机环境事实（2026-10-07 实测）

✅ **有**：`node/npm/npx`、`/opt/data/.venv` 内 `weasyprint 70.0` / `fitz(pymupdf)` / `Pillow 12.3` / `python-pptx`、中文字体 **`/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc`（文泉驿正黑）**、`libcairo.so.2` + `libpango-1.0.so.0`
❌ **无**：chromium/chrome、ImageMagick(`convert`/`magick`)、`rsvg-convert`、`inkscape`、ghostscript、libreoffice/soffice、`wkhtmltoimage`、`mutool`、`pdftoppm`。**别把方案建在这些工具上。**

⚠️ **Hermes browser 工具在本机起不来**：日志 `fatal: chrome-not-running: no supported Chromium-family browser is running` —— 它要求**已有 Chrome 在跑**，不是自带 headless。所以**不要走"打开网页截图"路线**；要截图就先装 chromium（~300MB，本机仅 4G 可用内存，不推荐）。

## 标准管线

```python
from weasyprint import HTML
import fitz

HTML(string=html, base_url=OUT).write_pdf(f'{OUT}/x.pdf')   # ① 渲染 PDF
doc = fitz.open(f'{OUT}/x.pdf')
pix = doc[0].get_pixmap(dpi=144)                            # ② 光栅化为 PNG
pix.save(f'{OUT}/x.png')
doc.close()
```

- **画布尺寸**：`@page { size: 1440px 900px; margin: 0; }` —— 不写会按 A4 排版，布局全乱。
- **出图分辨率**：`dpi=144` → 1440px 宽出 **2160×1350**，够嵌文档；要更高用 `dpi=200`。
- **单页约 2-5 秒**；多页原型就循环渲染多张 PNG。

## 🚨 五个必踩坑

1. **WeasyPrint 70 没有 `write_png`**（v60+ 已移除 PNG 输出，只有 `write_pdf`/`write_pdf`）→ 报 `AttributeError: 'HTML' object has no attribute 'write_png'`。**必须走 PDF → fitz 光栅化**。
2. **中文必须显式指定字体**：`font-family: "WenQuanYi Zen Hei", sans-serif;` —— 系统只有 48 个字体文件、CJK 仅此一个，不指定就是方框。
3. **不要用 CSS Grid**（v70 支持有限）→ 布局用 **flex** 或 `inline-block`，已验证 flex 可用。
4. **不支持的 CSS 会静默失效**（不报错、只是没效果）→ 所以必须做第 5 步。
5. **交付前必须自查**：用 `vision_analyze` 看渲染出的 PNG，确认「导航栏/侧栏/卡片/表格/中文/无错位」都在。**不要盲交**——非白像素占比低不等于没渲染，布局错位也不会报错。

## HTML 骨架（政务后台三栏，可直接改）

```html
@page { size: 1440px 900px; margin: 0; }
body { font-family:"WenQuanYi Zen Hei",sans-serif; width:1440px; height:900px;
       display:flex; flex-direction:column; background:#f5f7fa; }
.topbar { height:56px; background:linear-gradient(90deg,#1a6fd4,#2b8ae0); color:#fff;
          display:flex; align-items:center; padding:0 24px; flex:0 0 56px; }
.body   { display:flex; flex:1; }                 /* 侧栏 + 主体 */
.side   { width:200px; background:#fff; border-right:1px solid #e5e7eb; flex:0 0 200px; }
.main   { flex:1; padding:18px 22px; }            /* 面包屑/标题/卡片/筛选/表格/分页 */
```
配色：主色 `#1a6fd4`、边框 `#e5e7eb`、正文 `#1f2937`、次要文字 `#6b7280`；状态标签用浅底深字（`#e8f5e9/#2e7d32` 绿、`#e8f1fd/#1a6fd4` 蓝、`#fff4e5/#b26a00` 橙）。

## 交互原型（可点击）—— 主力交付形态（2026-10-07 实测通过）

**交付物 = 单个自包含 HTML 文件**（CSS/JS 全内联、零外部资源、零 CDN），用户双击即在浏览器点。
对标基准：腾讯 WorkBuddy 原型 skill / `huashu-design` / `prd-html-skill`，共同红线是
**单文件自包含 + 可点击交互 + 多页跳转 + 交付前浏览器验证**。

### 标准做法

1. **屏幕用 `section.screen` + `.active` 切换**，不要多文件、不要 hash 路由——便于 jsdom 驱动和静态截图。
2. **暴露测试接口**：脚本末尾挂 `window.__proto = {state, go, openDrawer, current, drawerOpen, modalOpen, toastText}`，
   否则没法自动化验证。
3. **每个可点元素给稳定 id**（`#nav-catalog`/`#tbody tr`/`#btn-go-apply`/`#btn-modal-ok`…）。
4. 抽屉/弹窗用 `position:fixed` + `.show` 类控制，**不要靠 JS 改行内 style**（静态渲染器读不到）。
5. 校验要写全：负例（必填未填/字数不够/未勾选承诺）必须被拦截。

### 🔬 无头验证：jsdom 代替 Playwright（本机无 chromium）

```bash
mkdir -p <proj>/jsdom && cd <proj>/jsdom && npm init -y && npm install jsdom
node test_proto.js     # 真实 DOM + 真实事件 + 断言，49 项用例全通过再交付
```

```js
const dom = new JSDOM(html, { runScripts:'dangerously', pretendToBeVisual:true,
  url:'file://'+P, virtualConsole:vc,
  beforeParse(w){ w.scrollTo=()=>{}; } });   // ⚠️ jsdom 未实现 scrollTo，必须桩掉，否则报 jsdomError
const click = el => el.dispatchEvent(new window.MouseEvent('click',{bubbles:true,cancelable:true}));
const input = (el,v)=>{ el.value=v; el.dispatchEvent(new window.Event('input',{bubbles:true})); };
```

必须覆盖：初始态 → 行点击开抽屉 → 标签页切换 → 抽屉跨屏联动 → **表单负例拦截** →
合法提交弹窗 → 确认后状态流转（列表新增/状态变更）→ 搜索/筛选/分页 → ESC 关闭 → 全屏可切换。
本机实测：**49 项全部通过**。

### 📸 交互态静态截图（jsdom 快照 + WeasyPrint）

WeasyPrint **不执行 JS** → 直接用原 HTML 截图会得到“未交互”的初始画面。正确做法：
**用 jsdom 跑完点击、导出 DOM 快照，再交给 WeasyPrint**。

```js
fs.writeFileSync(p, '<!doctype html>\n' + doc.documentElement.outerHTML);
```

### 🚨 快照保真度三坑（本次全部踩到）

1. **`.value` / `.checked` / `selected` 序列化会丢**——这些是「属性值」不是「特性」，
   `outerHTML` 里没有，截图里输入框会是空的（而旁边的“已输入 37 字”还在，自相矛盾）。
   导出前必须回写特性：
   ```js
   doc.querySelectorAll('input').forEach(el=>{ el.setAttribute('value', el.value);
     el.checked?el.setAttribute('checked','checked'):el.removeAttribute('checked'); });
   doc.querySelectorAll('textarea').forEach(el=>{ el.textContent = el.value||''; });
   doc.querySelectorAll('select').forEach(el=>Array.from(el.options).forEach(o=>
     o.selected?o.setAttribute('selected','selected'):o.removeAttribute('selected')));
   ```
2. **原生 `checkbox` 在 WeasyPrint 里渲染成黑色实心块**（没有对勾）→ 自绘：
   `appearance:none` + `:checked{background:主色}` + `:checked::after` 用 border 拼白色对勾。
3. **未显示的 toast 会显形**（`.toast{transform:translate(-50%,-140%)}` 里 transform 在
   WeasyPrint 中不位移）→ 快照冻结样式里加 `.toast:not(.show){display:none !important}`。

冻结样式统一写：`*,*::before,*::after{transition:none!important;animation:none!important}`。

## React 原型（baoyu-design / huashu-design 风格）的无头验证与截图（2026-10-07 跑通）

这两个 skill 的 interactive-prototype 都要求 **React + Babel、pinned CDN + integrity、多文件走 HTTP**。
本机无 chromium，下面这套已验证可行（产物：**62/62 用例通过 + 7 张真实交互态截图**）。

### 启动 HTTP 服务（skill 强制要求，不能 file://）
```bash
python3 -m http.server 4311 --directory /opt/data/designs
```
多文件原型的 `<script type="text/babel" src="x.jsx">` 在 file:// 下**静默不加载**。

### jsdom 30 的 API 变了（旧写法直接报错）
`ResourceLoader` 已移除，改为 `resources: { interceptors: [requestInterceptor(fn)] }`：
```js
const { JSDOM, VirtualConsole, requestInterceptor } = require('jsdom');   // 30.x
const intercept = requestInterceptor(req => {
  if (vendorMap.has(req.url))
    return new Response(fs.readFileSync(local), { headers:{'Content-Type':'application/javascript'} });
  return undefined;          // 其余请求（含本地 .jsx）正常走网络
});
new JSDOM.fromURL(url, { runScripts:'dangerously', resources:{ interceptors:[intercept] }, ... })
```
把 React/ReactDOM/Babel 三个 CDN URL 映射到本地副本，即可离线跑且能先校验 integrity。

### 三个会把「正常」误判成「坏了」的坑
1. **React 18 状态更新是异步提交的** —— `dispatchEvent` 之后**不 await 一帧就断言**，会得到「点击无效」
   的假结果（本机实测：探针里加了 await 后四种点击方式全部有效）。所有交互封装成 `async` + `await tick()`。
2. **受控输入必须用原生 setter** —— 直接 `el.value = x` 会被 React 内部 value tracker 忽略，
   `onChange` 不触发（表现为「搜索/字数不生效」）：
   ```js
   const d = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value');
   d.set.call(el, v); el.dispatchEvent(new window.Event('input', { bubbles:true }));
   ```
3. **等 `data-ready` 不够** —— 那只是脚本执行完的标志；必须再等真实 DOM 出现（如 `.nav button` 数量 > 0）。

### 浮层必须放在 grid 容器之外（结构性错误）
抽屉/弹窗/Toast 若写在 `display:grid` 的 `.app` 里，它们会成为 **grid item 被排到第二行**。
浏览器里 `position:fixed` 能侬幸脱流看不出，但静态渲染器会把它真的排到内容下方。
写法：`return (<><div className="app">…</div><Drawer/><Modal/><Toast/></>)`。

### 交互态截图：jsdom 驱动 → 快照 → WeasyPrint
拿不到浏览器截图，但可以：**用 jsdom 把 React 跑到目标状态，导出 `outerHTML` 快照，再交给 WeasyPrint**。
快照里必须额外处理：
```css
*,*::before,*::after{transition:none!important;animation:none!important}
.toast:not([data-open="true"]){display:none!important}
.scrim,.drawer,.modal{position:absolute!important}   /* 静态页无真实视口 */
.drawer{top:0;right:0;height:940px!important}
@page{size:1440px 940px;margin:0}  html,body,.app{height:940px!important}
```

### 🚨 WeasyPrint 不支持的 CSS（每一项都实际害过）
| 写法 | 后果 | 换成 |
|---|---|---|
| `box-shadow` 里用 `oklch(… / .x)` | **直接抛 NotImplementedError**（内部走渐变路径转不了 sRGB） | `rgb(15 23 42 / .06)`；聚焦环用**实心浅色 oklch** 代替半透明 |
| `inset:0` | 遮罩层尺寸塔陷 | `top/right/bottom/left:0` |
| `width:min(520px,94vw)` | 宽度失效 | `width:520px;max-width:94vw` |
| `display:contents` | flex 子项不再是 flex item → **分页控件重叠换行** | 用 React `Fragment` |
| `::placeholder` | 截图里输入框提示文字不显示 | 已知渲染差异，向用户说明即可 |

基调：**oklch 本身是支持的**（实测 `oklch(48% 0.09 245)` → rgb(58,97,141)），
仅「oklch + alpha 用在 box-shadow」那一类会崩。

### 交付时的取舍
skill 默认「多文件 + HTTP 预览」，但产物要经微信发到用户自己机器上 → **额外产一个单文件 standalone**：
把 4 个 `src="x.jsx"` 内联成 `<script type="text/babel">…</script>`（React/Babel 仍走 pinned CDN），
用户双击即可。内联后**必须重跑一遍测试**验证功能未变（本机：内联版同样 62/62）。

### ⚠️ 出图前必读（静态渲染器陷阱）

静态渲染器（WeasyPrint 70）有 **10 类会静默毁掉版面**的行为——按钮 `width:auto` 被撑满、`<input>` 整个不渲染、SVG 文字的 CSS `font-size` 失效、`@page` 不指定就按 A4 重排、grid 显式列放置丢子项等。共同特征是**不报错、只是悄悄变错**。

**每次出图前先读** `references/weasyprint-static-render-traps.md`（含每种陷阱的实测症状/唯一有效解 + 6 条量化验证法）。

### 交付单

- HTML 原件（用户自己点）+ 关键状态静态图（列表/抽屉/表单/弹窗/流转后）
- 说明清楚：**交互效果需用户本地浏览器验证**，截图只是证据
- 自包含：无外链、无 CDN、无网络请求，断网可用

## 参考产出

`/opt/data/.tmp_tests/proto/demo_proto.py` —— 完整可跑示例（民政数据资源目录后台，含统计卡/筛选/8列表格/分页），可直接拷改。

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
| **可点击交互原型** | 手写单文件 HTML + **真 Chrome 驱动验证** | playwright + chrome-headless-shell（已装） | **交互原型首选**：能真跑真截图（见下方「环境事实」）|
| 交互原型出静态图 | jsdom 驱动到目标态 → 快照 → WeasyPrint | jsdom + weasyprint | 需要**冻结态**图片时用（WeasyPrint 不执行 JS）|
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

## 本机环境事实（2026-10-11 复核）

✅ **有**：`node v26.5.1 / npm / npx`、`jsdom`（已装于 `.tmp_tests/proto/jsdom`）、
`/opt/data/.venv` 内 `weasyprint 70.0` / `fitz(pymupdf)` / `Pillow` / `python-pptx`、
中文字体 **`/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc`（文泉驿正黑）**、`libcairo.so.2` + `libpango-1.0.so.0`。

✅ **★ 真 Chrome 可用（2026-10-10 打通，这条推翻了旧的「本机无 chromium」结论）**：

```bash
/opt/data/chrome/shell/chrome-headless-shell-linux64/chrome-headless-shell   # Google Chrome for Testing 157.0.8095.0
```

playwright 1.63 用 `chromium.launch(executable_path=<上面路径>, args=['--no-sandbox','--disable-gpu'])` 即可完整驱动：
读/改 DOM、`set_input_files` 上传、`expect_download` 捕获导出、**截图真实交互态**全部可用。

**交互原型的验证优先走这条**（真实渲染引擎，比 jsdom 更接近用户所见）；
jsdom 仍保留给「纯逻辑/事件链断言」场景（快、无浏览器依赖）。
取包路径：npmmirror `registry.npmmirror.com/-/binary/chrome-for-testing/<版本>/linux64/chrome-headless-shell-linux64.zip`
（playwright 官方 CDN 本机拉不动；完整 chromium 因缺 4 个 GTK 库装不起来，只能走 headless shell）。

❌ **仍无**：完整 chromium（缺 libgtk-3 / libxcomposite / libxdamage / libxrandr）、ImageMagick、`rsvg-convert`、
`inkscape`、ghostscript、libreoffice/soffice、`wkhtmltoimage`、`mutool`、`pdftoppm`。**别把方案建在这些工具上。**

⚠️ 不要在含 `playwright install` 字样的命令里 `pkill -f 'playwright install'` —— **会匹配到自己的命令行自杀**（同 `pgrep -f 'bin/rclone'`）。

> 政务原型的真浏览器验证三件套（端到端 / 几何量化 / 数据审计）与两道构建门禁，见 `china-gov-ui-standards` skill 第九之二、九之三、九之六节。

### 🚨 迭代原型的四大「静默失效」（2026-10-11/12 实测，都害过）

**④ 「跑回归会重写源截图，把定稿截图糟掉」**（2026-10-12 实测，已回滚）
症状：为了验证改了样式层的版本，跑了一遍回归（含 `verify_chrome.py`），它**会向 `screenshots_真机/` 重写 9 张截图**；
而本机 Chrome **无中文字体**——重出的图体积从 205KB 掉到 75KB（中文全变方块），**交付目录当时没被覆盖，但下一步 `package.py` 会把它拷进去**。
铁律：
1. **跑任何回归/重出图前，先备份 `screenshots_真机/` 与 `交付/截图_真机/`**；
2. 跑完**逐张比对两者 MD5**，不一致的用交付图回写源目录（本例 9 张）；
3. 要看图/评图时必须内嵌中文字体（见下节“交付前自检”里的 woff2 方案），否则会把好图误判成坏图、也会把好图覆盖成坏图；
4. 回滚后**复核定稿 MD5**，确认交付物未被动过。

**③ 「换版构建会删掉交付目录里的定稿」**（2026-10-12 真实事故，险些丢掉投标定稿）
症状：为出 V3.0 跑了一次 `build.py`，**交付目录里 V2.9 的定稿 HTML 被自动清理删除**，而用户当时已宣布「V2.9 定稿」。
根因：`build.py` 每次构建会清理交付目录里的其它版本文件（含它不认识的 HTML），**它不区分「试验版」和「已定稿」**。
铁律：
1. 换版构建前，先把当前定稿**复制到交付目录之外**存档；
2. **交付目录永远只放一版**；试验产物一律放 `_试验_*` 目录，绝不放交付目录；
3. 构建后**必须 `md5sum` 核对**定稿是否还在、是否一致；
4. 用户说「停/定稿」时，要**反向检查本轮改动过的源码**（本例改过 `src/style.css` 追加样式块、改过 `build.py` 的 `VER`），**两处都回退后**重建才字节级还原成功。
   还原成功与否以 MD5 相等为准，不靠“应该没改动”。

**① 出图脚本与打包脚本的目录陷阱** —— 症状：**重出了图，但 mtime 还是几天前/旧图仍在**。
根因：本类原型项目的截图有**两个目录**，且方向是「源 → 交付」回拷：
- 真源目录：`<项目根>/screenshots_真机/`
- 交付目录：`<项目根>/交付/截图_真机/`

`package.py` 每次打包都会 `shutil.copy2` 把**真源目录**的全部 PNG 覆盖到交付目录（copy2 保留旧 mtime，所以看起来"没更新"）。
出图脚本写的目标目录又各不相同（有的写源目录、有的写交付目录）→ 极易出现"新图被旧图盖掉"。
另外：**别把旧图备份放在交付目录里**（`交付/_截图备份/`），它会被打包脚本当作素材一起抓取，再次覆盖新图。备份放到交付目录之外。
正确顺序：
```bash
rm -f <项目根>/交付/截图_真机/*.png <项目根>/screenshots_真机/*.png   # 两个都清
python3 各轮出图脚本.py                                              # 出图
cp <项目根>/交付/截图_真机/*.png <项目根>/screenshots_真机/             # 同步回真源（关键）
python3 package.py                                                    # 再打包
```
另：**全量出图脚本多是增量式**（文件存在就跳过）；且**历轮截图分散在各版收尾脚本里**
（`shots_v12.py`~`shots_v15.py`、`final_v18.py`、`final_v20.py`、各版 polish/reshot 等，每版只补自己那几张），
所以**改了全局观感（顶栏、表头、措辞）后想全量重出，必须把历轮出图脚本串跑一遍**——
先抽出每个脚本里 `from playwright…` 到 `package.py` 之间的出图段（并用工具确认它**不会写版本号**，会写的先去掉那段），
再按版本次序跑。只跑最新那一个脚本 = 只更新几张，其余全是旧观感。

**② 版本号有多处，改一处等于没改** —— 症状：文件名是 V2.2，页脚/`window.APP.VERSION` 还是 V2.1。
版本号至少存在三处：`build.py` 的 `VER`、`src/app.js` 的 `var VERSION`、以及交付目录的 README/旧文件名。
改完必须 `grep -rn 'V2\.1'` 复查，并用测试断言 `页脚显示版本号 == 期望` + `APP.VERSION == 期望` 兜底（测试会替你抓到残余）。

## 🚨 收到「问题反馈表」先分诊，再动手

用户常把**历次**反馈攒成一张 xlsx（序号/问题定位/修改方式/修改范围）一次交过来，里面一半已经改过了。

1. **逐条做存在性核对**：把每条点名的元素/文案（`mainnav`、`sidesw`、`#restart`、「留在本页」、「上传要素信息文件」…）
   拿去 `grep` 当前**源码 + 产物 HTML**，分两档标注 `已达成 / 待改`，落成项目内 `反馈改造清单_Vx.md`。
2. **把分诊结果摆给用户**（「68 条里 22 条已达成、46 条待改」）——他会直接圈定只改哪几条，这一步省掉的返工比任何实现技巧都多。
3. **只按他点名的编号改**，不要顺手"优化"邻项；他会明确说「只改这两条，其他都是历史修改」。
4. 元素路径是旧版结构（`div.mainnav` / `div.sidesw` / `#restart`）就在产物里搜不到 → 那是历史项，**别照路径硬改**。

## 🚨 抽屉/弹窗内的事件绑定：绑在 `init()` 里等于没绑

症状：抽屉里 `select` 的联动（切换后下方配置区跟着变）永远不生效，而且**配置区一直是空的**。
根因：handler 写在屏级 `init()` 里，而目标元素要等 `openDrawer()/openModal()` 注入 DOM 后才存在 →
绑定时 `getElementById` 返回 null，静默跳过（不报错，最难查）。

铁律：**绑定抽屉/弹窗内部元素的 handler，必须写在 `openDrawer()/openModal()` 调用的下一行**，
并**紧接着手动调一次**该 handler 渲染初始态：

```js
A().openDrawer('发起数据归集任务', body, foot, true);
var dk = document.getElementById('c-dock');
if (dk) { dk.onchange = applyDock; applyDock(); }   // ← 初始态也要跑一遍
```

验证：真 Chrome 里 `select.value = X; dispatchEvent(new Event('change',{bubbles:true}))`，再读联动字段文本。
**只读代码会以为已经实现了**——本次就是这么漏掉的。现成脚本见 `scripts/verify_proto_chrome.py`。

## 📦 交付：mac 启动包打包

微信发给用户在 macOS 上跑，包内必须 `index.html` + `启动.command` + `serve.py` + `启动.sh` + `使用说明.md`。

- 本机常**没有 `zip` 命令** → 用 `zipfile` 手工写 `ZipInfo`，**必须显式设 `external_attr = 0o755 << 16`**
  保留 `.command`/`.sh` 的执行位，否则用户解压后双击无反应（macOS 只看执行位）。现成脚本：`scripts/package_mac_launch.py`。
- 打包前 `sed -i 's/V2\.9/V3.0/g'` 清掉包内 `使用说明.md`、`启动.command` 的旧版本号，再 `grep -o 'V2\.9'` 复核。
- 双格式：`.zip`（微信传）+ `.tar.gz`（mac 双击解压），都用脚本现做。
- 包内 `index.html` 的 MD5 必须与交付版 HTML **逐一比对相等**；打包后要**读回 zip 每个成员**算 hash（源目录看着对、包内可能是旧副本）。
- 🚨 `serve.py` **必须发 `Cache-Control: no-store`**（覆写 `end_headers()`），并让它打印 `index.html` 的
  MD5/字节数/时间做版本指纹。否则「持久化 Chrome 配置目录 + 无缓存头」会让用户看到旧页面，
  然后回过头来说「启动包没改」——而包里其实是对的。
- 🚨 **不要往打开地址上挂 `?t=<时间戳>` 之类的一次性参数**。地址栏本身就是这套交付的验收重点：
  双击后必须是 `http://localhost:8080/`（就一个斜杠），切页后才是 `http://localhost:8080/sjqxjgmx`。
  禁缓存靠上面的 `no-store` 响应头 + 指纹打印就够，用 query 防缓存会被判不合格。
  同理，页面启动引导里**根路径不得被 `pushState`/`replaceState` 改写成默认屏路由**。
  完整规则与启动引导代码见 `demo-launch-package` skill 第一节。
- 启动包的双平台细节、禁缓存完整写法、逐成员校验与验证脚本见 **`demo-launch-package`** skill（本类的专管 skill）。

> 静态出图（WeasyPrint→PDF→PNG）的前提是 `import weasyprint` 能过；若该导入因缺系统库报错，
> **不要在库上折腾**——交互原型本来就走真 Chrome 截图，直接改这条路并向用户说明「不出静态图」。

## 🎨 品质感与动效（2026-10-11 新增，对标 auteur/impeccable）

> 🚨 **用户已定方向（2026-10-12）**：**按「①政务规范内的高级感」做，不做花哨**——
> 靠**层次 / 密度 / 动效 / 排版 / 状态驱动交互**取胜，**不靠**彩虹渐变、拟态、光效。
> 同时**暂不换模型**（仍用 deepseek-v4-flash 出稿）。新产品若要提“更酷”，必须先问是否仍在①范围内。

**背景**：用户反馈「WorkBuddy 出的原型更时尚、有动效」。`slopscan` 实测：我们的 V2.9 是 **0 fail**（没有 AI 味），
而一个裸模型输出是 **13 fail**（紫蓝渐变 + 12 处 `transition: all`）。
所以我们的短板**不是"脏"，是"平"** —— 缺层次、缺动效、缺密度。
**结论：不要加彩虹渐变，要加层次 + 有理由的动效 + 信息密度。**

### 1. 视觉层次（不靠装饰）
- 配色分层：中性色**向品牌色偏移** 0.005–0.015 chroma；⚠️ **不要暖米色**（L 0.84–0.97 的暖米带是 AI 默认脸）。
- 必须有三个层级：页面底 / 卡片面 / 浮起面。`box-shadow` 只给**真浮起**的东西，全页一个光方向，blur > offset。
- 分隔用 **1px 低对比细线**，别用色块拼接；表头浅底与斑马纹**二选一**，不要叠。
- 数字用 tabular/等宽数字，数值列**右对齐**；表头字号 ≤ 正文，靠颜色区分，不靠加粗堆尸。
- **卡片是最后选项**：能用「标题 + 细线 + 密排表格」表达的就不用卡片；**禁止卡片套卡片**。
- 一屏一个**签名元素**（大号关键数字 / 高密度表格 / 真实的业务图形），让专家记得住这页。
- 留白有节奏：密排区与留白区**交替**，不要全页 uniform padding。
- 🚨 政务硬约束优先：主色 ≤3 种（国办发〔2017〕47号）。"炫" 靠层次/密度/动效/排版，不靠彩虹渐变。

### 2. 动效（数字规则，直接照抄）
- **只在有理由时动**：层级 / 叙事 / 反馈 / 状态变化 / 空间定位 / 避免跳变。**「看着酷」不是理由，没理由就删。**
- **频率决定有无**：每天点 100+ 次的操作（搜索、翻页、切换标签）→ **零动画**；几十次（hover、列表导航）→ 近乎零。
- 缓动：进场/出场一律 `ease-out`；**UI 里禁用 `ease-in`**；位移动画用自定义曲线 `cubic-bezier(.23,1,.32,1)`；**禁 `transition: all`**。
- 时长：按压 100–160ms ｜ 下拉/浮层出现 150–250ms ｜ 抽屉/弹窗进场 200–500ms，**出场比进场短**（200/150）；超 300ms 必须写理由。同类元素时长**必须一致**。
- 只动 `transform` + `opacity`（动 width/height/top/left 会掉帧）；**入场禁止 `scale(0)`**，最小 `0.95`；按压 `scale(0.97)`。
- 抽屉 / toast 用 `transition`，**不要 `@keyframes`**（重复触发会从零重放）。
- hover 效果必须包在 `@media (hover:hover) and (pointer:fine)` 内，否则触屏会误触发。
- **必须写** `@media (prefers-reduced-motion: reduce)`：保留透明度过渡，去掉位移动画。
- 列表错峰 30–80ms；错峰只是装饰，**不得阻塞交互**。
- 一屏只留一个「wow 峰」，其余降强度。
- ⚠️ **与静态出图管线的冲突**：动画**不得承担布局与可见性**——内容默认就要可见（否则 WeasyPrint 快照 / JS 失败时是空白页）。动画只做「增强」，不做「呈现」。

### 3. 少提问、先出完整版（对标「需求少反而更完整」）
- 需求单薄时**不要挤牙膏式追问**，按默认清单一次补齐，**先给完整版**，再问「哪块要调」。
- **默认补齐清单**（政务后台，缺一不可）：顶栏(系统名+用户) · 左侧多级菜单(含激活态) · 面包屑 · 页面标题+操作按钮区 · 统计卡(3–5) · 搜索筛选区(2–4 字段+重置) · 表格(表头/序号/状态标签/操作列) · 分页(总数+每页) · 抽屉详情 · 确认弹窗 · toast 提示 · 空状态 · 权限受限态。
- 数据一律**编得像真的**（真实感的中文机构名/日期/编号），**不留 `xxx`/「示例1」占位**。
- 一次交付完整体验，不要留 TODO 给用户。

### 4. 交付前自检（新增，可量化）
```bash
# 反 AI 味扫描：必须 0 fail（有 fail 逐条修，不许 suppress）
node /opt/hermes/optional-skills/creative/auteur/scripts/slopscan.mjs <产物.html>
```
⚠️ **自己写 grep 自查时必须先剔除注释**：实测把自己的中文注释（“……原来用 transition:.15s（等价 all）……”）
当成了真的 `transition: all`，误报一次。先 `sed 's#/\*.*\*/##g'` 去注释再 grep，或直接用 `slopscan` 为准。
再加：真 Chrome 截图 → **`vision_analyze` 自己看一遍**，逐项确认：层次（三代面）、对齐、信息密度、无空白塌陷、无元素重叠。
⚠️ 本机截图环境只有文泉驿正黑一款中文字体：产物若只写 `PingFang SC`/`Microsoft YaHei`，截图里中文会是**方块**——
这不是产物缺陷（用户机器上正常），但**评测时必须加字体回落**再看，别据此误判。

### 5. 相关技能（2026-10-11 装/核）
> ✅ 已装（均官方、已过安全扫描）：`auteur`（444K）、`impeccable`（2.2M，需 GITHUB_TOKEN）、
> `claude-design`、`sketch`、`scrollcraft`。装 hub 技能需 GitHub token，未认证会被 60 次/时限流。
| 技能 | 何时加载 |
|---|---|
| `auteur` | 要「好看 / 有表现力 / 多屏像一套系统」时的审美与动效总纲。**必读** `auteur/references/taste.md`（反 AI 味 + 层次）与 `auteur/references/motion.md`（数字级动效规则）、多屏统一看 `auteur/references/system.md`；`auteur/scripts/slopscan.mjs`、`auteur/scripts/motionqa.mjs`、`auteur/scripts/shoot.mjs` 可直接跑（自带目录 `/opt/hermes/optional-skills/creative/auteur/`） |
| `sketch` | 方向未定时，**先出 2–3 个视觉方向**让用户挑，再深入 |
| `scrollcraft` | 滚动叙事/落地页式体验（本类政务后台基本用不上） |
| `impeccable` | 更狠的前端审美标准；⚠️ 完整版需从 hub 下载（GitHub 限流，需 `GITHUB_TOKEN`） |
| `china-gov-ui-standards` | 政务配色与规范硬约束，**优先级高于本节的审美偏好** |

### 6. 模型选型（原型生成专用，别凭感觉定）

原型生成对模型的要求与写代码不同：**要输出上限大、审美在线、一次成型**。选型必须实测，步骤：
1. **同一短需求**投给备选模型（**需求故意写得少**，模拟真实场景；prompt 一字不改才可比）。
2. `max_tokens` **至少 32000**。
   🚨 **12000 会把整页原型截断**（实测：32.7KB 就断，`</html>` 不闭合、正文只剩 165 字）——
   截断样本**不能用来评审美**，只能当“输出上限不足”的证据。
   ⚠️ **32000 对推理型模型（如 deepseek-v4.1-flash）也不够**：实测看板页用满 32000 token 后仍未闭合（34KB 产物，
   推理 token 吃掉预算）→ 推理型模型出整页原型要留 48000–64000，并在断言里校验 `finish_reason=='stop'` 与 `</html>` 闭合。
3. 失败要**打印响应体再定性**，退避重试 429/5xx（20s/40s，共 3 次）。
   🚨 **HTTP 码不等于原因**：实测同一个 429，响应体写的是「余额不足或无可用资源包，请充值」；另一个 400 写的是「The product is not activated」。**只记状态码就下结论，会把账号问题当模型能力缺陷汇报给用户**（已经错过一次，且用户会追问出处）。批量测模型时，错误分支必须把 body 前 300 字打出来。
4. 量化指标（脚本已存 `.tmp_tests/proto/eval_bakeoff.py`）：
   `@keyframes/transition/animation` 数、`gradient/box-shadow/CSS变量` 数、
   `(hover:hover)` 媒体查询门、`prefers-reduced-motion`、JS 报错数、**正文文字数**、输出 token、finish_reason。
5. 再过 **`slopscan`**（反 AI 味）与**真 Chrome 截图 + `vision_analyze`**（自己的眼）。
6. 🚨 截图前**必注入中文字体**：本机 **没有任何系统中文字体**（`fc-list :lang=zh` 为空，Chrome 把中文全渲染成方块；写文泉驿/写不存在的字体名宽度一样，说明根本不生效）。
   唯一有效解法：下载 woff2 子集并内嵌——
   `curl -sL https://cdn.jsdelivr.net/npm/@fontsource/noto-sans-sc@5.2.5/files/noto-sans-sc-chinese-simplified-400-normal.woff2 -o <评测目录>/_evalcjk.woff2`（~1.1MB，国内直连可达）
   ✅ **已存一份持久副本：`/opt/data/assets/fonts/noto-sans-sc-cjk.woff2`——直接用它，别再依赖 `/tmp`（会被清，且磁盘紧张）。**，
   然后注入 `<style>@font-face{font-family:"EvalCJK";src:url("_evalcjk.woff2") format("woff2")}html,body,body *{font-family:"EvalCJK",sans-serif !important}</style>`。
   验证看 `document.fonts` 里有 `EvalCJK:loaded`。现成脚本：`.tmp_tests/proto/eval_bakeoff.py`。
   ⚠️ 副作用：强制单一字体后页面里的**图标字体/emoji/符号**（☰ ⚙ ↗）也会成方块，**别当成产物缺陷**（真实用户机器上正常）。
7. 换模型前先算成本/额度，并**取得用户同意**（用户规矩：效果第一 → 性价比 → 换模型须点头）。
   成本要算**「每次出一屏稿的钱」**，不只是比 token 数：取模型**公示价目**（DeepSeek / 百炼 / 智谱官网价格页；这些页面多是 JS 渲染，抓取器拿不到表，**用真浏览器读 `table` 单元格**）× 本次实测 token（输入按 prompt 量级、输出按 `completion_tokens`）。
   实测同一需求：贵模型输出 18.6k token、便宜模型 25.1k token，但单价差 2.5 倍 → **总成本由单价主导；输出短的模型不一定更省钱**，正文密度与关键帧数要一起看。
   建议按「日常用便宜的、极致用贵的」两档报给用户，并**明确说清不换模型时差距怎么补**（靠 skill 里的规则/自检补，而不是靠换模型）。

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

> 被要求写**演示脚本 / 口播稿**（按需求条款逐步走、含屏幕指路与时长核算）时，加载 `speech-draft` skill 的「系统演示脚本」一节——界面事实要逐屏从原型里读出来，不许凭印象写。

- HTML 原件（用户自己点）+ 关键状态静态图（列表/抽屉/表单/弹窗/流转后）
- 说明清楚：**交互效果需用户本地浏览器验证**，截图只是证据
- 自包含：无外链、无 CDN、无网络请求，断网可用

## 参考产出

`/opt/data/.tmp_tests/proto/demo_proto.py` —— 完整可跑示例（民政数据资源目录后台，含统计卡/筛选/8列表格/分页），可直接拷改。

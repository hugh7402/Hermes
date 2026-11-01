# 结构性重构一版高保真原型（实测记录）

> 2026-10-10 实战：「四川一体化数据资源管理系统」原型由 **三系统并成两系统 + 换系统切换方式 + 进度条拆两段 + 加版本号**。
> 结果：7 套脚本 **195 项全绿**、一次交付、零来回。本文是该次改动的方法与事故清单。
> 方法论在 SKILL.md 九之九；本文存**细节与可复用的证据**。

---

## 一、本次改动清单（用户反馈表 5 条 + 1 项）

| # | 用户原话（精简） | 落地做法 | 归属 |
|---|---|---|---|
| 1 | 删除「四川省级数据资源共享交换平台」 | 顶栏 brand 里那个 `<span>` 删掉；顶栏**不再重复显示系统名**（改由系统导航行承担） | 壳 |
| 2 | 删除「按规范填写 7 个属性组共 52 项（含 11 项条件必填…）」 | 表单操作条上的 `span#form-tip` 整条删；**字段与 11 条联动规则不动** | 单屏 s1 |
| 3 | 删「切换到其他系统 / 数据归集系统 / 一数一源一标准治理系统」整块 | 删掉 `renderSysSwitch()` 与 `.sidesw` 全部 CSS | 壳 |
| 4 | 原型由**两个系统**组成；**按正常导航栏切换**，不要专门的切换按钮 | 新增顶部「**系统导航行**」（平台栏正下方）：`系统：` + 两个系统名，当前项高亮 + 「当前」标记，点击切到该系统 `home` 屏 | 壳 |
| 5 | 生命周期进度条**拆两部分**：编目归目录系统、归集与治理归集系统 | `LIFECYCLE` 由**一个 8 段数组**改成**按系统分组的对象**（catalog 3 段 / collect 5 段），`renderPipeline(sysKey, stage)` 按当前系统取段 | 壳 + 全部屏幕 |
| 6 | 在原型后**加上版本号** | 文件名 `..._V1.1.html` + 界脚「版本 V1.1」+ `APP.VERSION` 导出 | 构建 + 壳 |

**判断性决定（需向用户确认的那一条）**：用户说"拆成 编目 / 归集与治理 两部分"，
但 `发起归集任务 / 数据归集工单 / 目录归集状态` 三屏原本挂在**目录系统**侧栏的「数据归集」组下。
它们的状态节点（`col` / `colrun`）属于**归集段**，若留在目录系统，目录系统的进度条又会横跨两个系统 → 仍违背第 5 条。
**故一并迁入归集系统**，并在交付说明里**明确把这条判断摆给用户确认**（用户问的是流程分组，没直接点名这三屏该去哪）。
> 教训：需求里"两部分"这类划分，**落到具体屏时会有边界屏归属不明**；不要默默选，改完把判断列出来让用户点头或推翻。

---

## 二、影响面清单（改前 grep 出来的全部落点）

```
src/app.js
  L9-80   SYSTEMS（三个系统定义：name / org / nav / side）
  L83-92  LIFECYCLE（单一 8 段数组）
  L95-113 META（每屏 sys / nav / menu / crumb / title / stage）
  L117-123 ROLES（角色，含机构）
  L193-208 renderTopbar   ← 含硬编码平台的 span、系统名、机构
  L210-214 renderMainnav  ← 高亮用静态 n.on（**缺陷**）
  L216-225 renderPipeline ← 用全局 LIFECYCLE
  L239-248 renderSysSwitch ← 整块删
  L251-287 render()       ← 外壳拼装 + 高亮/机构刷新
  L324-329 roleFor()
  L345-376 bindShell()    ← [data-sys] 点击 → 跳哪个屏
  L331-342 renderFooter()
screens/*.js
  s1.js   form-tip
  s1b.js  旧系统名 ×3、流转说明
  s3.js   跨系统文案 ×11（含 go-sys / go-sys2 / go-sys-m 三个按钮）
  s4.js   var SYS = '数据归集系统'、"切换到数据目录管理系统…"
  s5.js   标签、"切换到一数一源一标准治理系统"、go-govern 按钮
  s6/s7/s8.js  旧系统名
产物/脚本
  build.py  输出文件名、防腐清理
  package.py 主交付物路径
  测试 ×7   文件名硬编码 + .pipeline 节点数断言 + 旧状态词断言
```

**关键：测试脚本必须在第一遍就进清单。** 本次 7 个脚本里 4 个引用了 `S.govern` / `.pipeline` / 交付文件名。

---

## 三、锚点脚本的形状（可直接复用）

```python
SRC = pathlib.Path('.../proto/src'); s = APP.read_text()

def rep(old, new, label):
    global s, n
    assert old in s,               f'❌ 锚点未找到：{label}'
    assert s.count(old) == 1,      f'❌ 锚点不唯一（{s.count(old)} 处）：{label}'
    s = s.replace(old, new, 1); n += 1; print(f'  ✓ {label}')

def cut(start_marker, end_marker, new, label):
    """把 start..end（不含 end）整段换成 new —— 用于替换整个代码块"""
    global s, n
    i, j = s.find(start_marker), s.find(end_marker)
    assert i >= 0 and j > i, f'❌ 起止点有问题：{label}'
    s = s[:i] + new + s[j:]; n += 1; print(f'  ✓ {label}')
```

**为什么必须断言**：本次两个真实事故都出在没有断言的地方 ——
① 一次"在锚点前插入新块"的替换没删旧块 → 调试面板 DOM 重复（两个 `id="dbgbox"`）；
② 同批脚本里另一次替换**静默没命中**，日志只显示少打了一行、看日志会以为改完了。

**工作方式建议**：把改动拆成 2~3 个脚本（壳/屏幕/文档各一个），每个脚本跑完打印 `✓ N 处`。
本次分 `refit_v11.py`（壳+CSS 13 处 + 5 处）、`refit_v11b.py`（屏幕 22 处）、`refit_v11_docs.py`（文档 10 处）。

---

## 四、两系统归属表（改完的形态）

| 系统 | 屏 | 流程段 |
|---|---|---|
| **数据目录管理系统** | s1 新增政务数据目录 / s1b 数据目录列表 / s2 数据目录审批管理 | 编目流程：编目填报 → 审核发布 → 已发布（3 段） |
| **数据归集管理系统** | s3 发起归集任务 / s3b 数据归集工单 / s5b 目录归集状态 / s4 s4b 归集工单审核 / s4c s4d 数源管理 / s5 离线归集任务 / s6 s6b 治理规则配置与审批 / s7 s7b 治理任务 / s7c 数据清洗明细 / s8 治理成效 | 归集治理流程：归集审批 → 自动建表 → 归集已实施 → 治理规则 → 治理完成（5 段） |

**内部状态键保持原命名**：`S.catalog` / `S.collect` / `S.govern` 三个状态桶**照旧**，
`ROLES.govern`、`roleFor()` 返回的 `'govern'` 也照旧 ——
它们只是**状态/角色的内部键，不是系统 id**，改名会牵动 4 个测试文件却对用户零价值。
> 取舍原则：**用户可见的语义要改干净，纯内部的键可以留但必须加注释说明它不是系统 id。**

---

## 五、四处同步表（改名/加版本号的完整落点）

| 落点 | 本次实际症状 | 修法 |
|---|---|---|
| `build.py` 输出名 | — | `VER='V1.1'`；`out = OUT_DIR / f'名称_{VER}.html'` |
| `build.py` 防腐清理 | 旧 `名称.html` 仍在交付目录 | 已有 `for stale in OUT_DIR.glob('*.html'): if stale != out: unlink()` → 自动清掉，日志打印 `🧹 已清理历史遗留文件` |
| `package.py` | 硬编码旧名 | 改 `sorted(OUT.glob('名称*.html'))[-1]` |
| **测试脚本 ×7** | 会一直验证过期版本 | 一律改 `sorted(交付目录.glob('名称*.html'))[-1]` |
| `README.md` / `演示操作手册.md` | 文件名、"三个系统"表述、按钮名、话术过期 | 同批更新 10 处，并把上一版改动降级为「历史版本」章节 |

**七套脚本**：`verify_feedback`(本次反馈专项) / `verify_chrome`(真机渲染) / `verify_refit`(四项要求) /
`e2e_demo`(端到端六步) / `geom_check`(几何量化) / `check_actbar`(操作栏不压内容) / `verify_debug`(调试开关)。

---

## 六、本次新抓到的壳缺陷（结构性改动才会暴露）

1. **模块导航高亮写死**：`renderMainnav` 用 `SYSTEMS[k].nav[i].on`（静态 `on: true`），
   而 `META[screen].nav` 早就记录了每屏该高亮谁 —— **切屏时高亮永远不变**。
   改为 `renderMainnav(sys, activeNav)` 用 `meta.nav`。
2. **顶栏机构取自系统**：s3/s3b/s5b 并入归集系统后，顶栏显示「大数据中心 · 张\*\* · 数据管理员」——机构与角色打架。
   改为机构取自**当前角色**（`ROLES[roleFor(screen)].org`）。
3. **重复接线**：`render()` 里 `cp2 = getElementById('dbgcopy')` 那三行**写了两遍**（`var` 重复声明合法，所以一直没报错）。
   删掉重复块。
4. **`.actbar .tip{margin-right:auto}` 承担了按钮右对齐职责** —— 删 tip 必须补 `justify-content:flex-end`，
   否则按钮左移 20px→0。实测确认：按钮距右边缘仍 20px。

---

## 七、新增第二层导航的落地要点

```html
<div class="sysnav">
  <span class="sn-label">系统：</span>
  <span class="sn on" data-sys="catalog"><i class="dot"></i>数据目录管理系统<span class="cur">当前</span></span>
  <span class="sn"    data-sys="collect"><i class="dot"></i>数据归集管理系统</span>
</div>
```

- 用 `<span data-sys>` 而非 `<a>`/`<button>`：**整个原型统一用 span 做可点元素**，静态渲染器不会把它撑满。
- 高亮：`.sn.on{background:#fff;border-bottom:3px solid var(--pri)}` —— 与主导航同一套选中语言（主色下划线），
  但额外给**白底 + 3px 下边框**，让"层"的语义区分开。
- 小圆点 `.dot` 让两个系统看起来像同级可切换项，当前项圆点变主色。
- `data-sys` 的点击行为：`SYSTEMS[k].home`（本次 catalog→`s1b`、collect→`s3b`），**在 SYSTEMS 里声明 home，不要在 bind 里写映射表**。
- **系统导航行高度用变量** `--sysnav-h:36px`，并同步 `.wrap` 的 calc（见 SKILL.md 九之九）。

---

## 八、实测数字（可作为下次的对照基线）

| 项 | 值 |
|---|---|
| 交付物 | `四川一体化数据资源管理系统_V1.1.html` · 600 KB · 4414 行 · MD5 `f8be1a83c861e584f7f391788d391c09` |
| 真机截图 | 36 张（含 3 张本轮新增：两系统导航 / 目录系统编目流程 / 归集系统归集治理流程） |
| 七套脚本 | 33 + 33 + 38 + 56 + 17 + 操作栏全过 + 18 = **195 项全绿** |
| 导航溢出实测 | 1920 / 1600 / 1440 三档：两系统均 0 溢出、单行、模块 7 项 / 11 项 |
| 外壳四层高度 | 平台栏 52 + 系统导航 36 + 模块导航 40 + 进度条 36 |
| 构建门禁 | `node --check` 两个 script 块 ✅ + 17 类敏感词 0 命中 ✅ |

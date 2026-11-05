# 单页驾驶舱拆成分层多页：实现配方

把一个已经能跑的单页七块驾驶舱，改造成「一页领导层 + 若干下钻页」。
改造期间页面必须持续可跑，每一步都能在浏览器里验证。

---

## 1. 先把样式与脚本抽成共用文件

单页版把 CSS 和 JS 都内联在 HTML 里，多页必须抽出来，否则每加一页就复制一份逻辑，
改一个判定口径要改五处。

```python
from pathlib import Path
src = Path("index.html").read_text(encoding='utf-8')
i = src.index('<style>'); j = src.index('</style>')
Path("app.css").write_text(src[i+7:j], encoding='utf-8')
k = src.index('<script>'); l = src.index('</script>', k)   # 最后一个内联 script
Path("app.js").write_text(src[k+8:l], encoding='utf-8')
```

抽完先 `node --check app.js` 确认没有截断断错位置，再做下一步。

**文件名一律 ASCII**：`app.js` `app.css` `app-extra.css` `data.xlsx` `xlsx.full.min.js`。
中文名在 macOS 解压后是 NFD，浏览器请求是 NFC，字节对不上就 404。

## 2. 让每个渲染函数「缺 DOM 也不炸」

这是整件事的关键。多页之后，同一个 `app.js` 被五个页面引入，但 `milestones.html` 里
没有 `#ring`、`tasks.html` 里没有 `#msGrid`——原来那些裸 `document.getElementById(x).innerHTML = ...`
一旦拿不到元素就抛 `TypeError`，整个脚本中断，页面一片空白。

在 `app.js` 顶部加三个辅助函数，然后把所有 DOM 写入换成它们：

```js
const $el  = id => document.getElementById(id);
const $set = (id, html) => { const e = $el(id); if (e) e.innerHTML = html; };
const $txt = (id, txt)  => { const e = $el(id); if (e) e.textContent = txt; };
```

需要改的三类：

| 原写法 | 改成 |
|---|---|
| `document.getElementById('x').innerHTML = v` | `$set('x', v)` |
| `document.getElementById('x').textContent = v` | `$txt('x', v)` |
| `document.getElementById('x').style / .classList` | `const e = $el('x'); if (e) e.style...` |

**列表型渲染里的 `const el = document.getElementById('drill'); el.innerHTML = h;` 也要加 `if (!el) return;`**，
否则后面那些 `el.querySelectorAll(...).forEach(...)` 全部会炸。

**事件绑定全部要塞进存在性判断**，否则某页没有某个按钮时，加载阶段就抛错：

```js
(function bind(){
  const on = (id, ev, fn) => { const e = $el(id); if (e) e[ev] = fn; };
  on('bReload','onclick', ...);
  on('asof','change', ...);
})();
```

拖拽、`input[type=date]`、双击回到今天这类全局监听，同样每个 `$el` 都要判空。

## 3. 把巨石 `render()` 拆成按层函数

原来的 `render()` 从健康度一路干到甘特，中间用注释 `── 一、` `── 二、` 分段。
按这些分段边界直接切成独立函数，再留一个全量入口：

```js
function renderOverview()   { /* 进度环 + 判定卡 + 关键结论 + 数字卡 + 入口卡文案 */ }
function renderDeviation()  { /* 按分类 / 按责任组的偏差对比条 */ }
function renderMilestones() { /* 里程碑方格 */ }
// renderDrill / renderIssues / renderKpi / renderGantt 原本就是独立函数，不动

function render() {           // 名字保持不变，调用方不用改
  if (!S.loaded) return;
  renderOverview(); renderDeviation(); renderMilestones();
  renderDrill(); renderIssues(); renderKpi(); renderGantt();
}
```

每个函数开头都 `if (!S.loaded) return;`，内部只读自己需要的 `S.*`，不依赖别的函数先跑过。

**共用同一份状态** `S`（tasks / ms / ops / pf / weeks / sim / openCat / openSys）。
五页各自独立加载 `data.xlsx`，但要保证 `loadWB()` 只有一份，各页只是重新调 `render()`。

## 4. 页面骨架

每页共用同一段 head + 顶栏，只换 body 和当前页签高亮：

```html
<link rel="stylesheet" href="app.css">
<link rel="stylesheet" href="app-extra.css">
<div class="top">
  <h1>项目名</h1><div class="src" id="src">数据源：加载中…</div>
  <div class="tabs">
    <a class="tab on" href="index.html">总览</a>
    <a class="tab" href="milestones.html">节点与偏差</a>
    ...
  </div>
  <div class="sp"></div>
  <div class="clock">数据日期 <input type="date" id="asof"></div>
  <button class="btn" id="bLoad">载入数据</button>
  <button class="btn" id="bSim">示例数据</button>
  <button class="btn" id="bReload">刷新</button>
</div>
<div class="wrap"> ...本页内容... </div>
<div id="fstat"></div>
<script src="xlsx.full.min.js"></script>
<script src="app.js"></script>
<script>autoLoad();</script>
```

- 用 `sed`/模板批量生成五页，保证顶栏和底部脚本块完全一致，只有 body 和 `class="tab on"` 不同。
- 下钻页顶部放 `<a class="back" href="index.html">← 返回总览</a>`。
- 首页不放任何明细表；每个入口卡是一个 `<a class="enter" href="...">`，
  里面的数字用独立 `<span id="cMsEnter">` 等，在 `renderOverview()` 里用 `$txt` 填实时值。
  入口卡必须带数（「39 项任务 · 0 项延期 · 0 项预警」），光写“点此进入”没人点。

## 5. 空数据也要让首页有信息量

进度列全空时，首页不要靠「实际进度」撑场面，改用这些由日期和行数推出来的真实值：

- 计划进度（按 as-of 日期算，纯事实推导）
- 已填报 N / 总 M（“各组都还没报”本身就是信息）
- 距最近一个里程碑还有多少天，已过期的高亮
- 各任务分类数量、指标条数、周轴周数

领导打开看到「项目刚起步、还有 N 天到第一个节点、各组还没报进度」，比看一个全 0 的环有用。

## 6. 验证断言

在真浏览器里逐页跑，一页一组：

```js
S.loaded === true
S.tasks.length / S.ms.length / S.ops.length / S.pf.length / S.weeks.length  // 与底盘逐项相等
document.getElementById('warnBox').style.display === 'none'                 // 没弹加载失败提示

// 首页
[...document.querySelectorAll('.ms-item')].length === S.ms.length
[...document.querySelectorAll('.mcard')].length > 0
['cMsEnter','cTaskEnter','cIndEnter','cGantEnter'].every(id => document.getElementById(id).textContent.trim().length > 3)

// 节点页
[...document.querySelectorAll('.bar-row')].length > 0        // 分类+责任组两组合计

// 任务页
[...document.querySelectorAll('#drill tr.lv1')].length > 0
[...document.querySelectorAll('#issues tr')].length > 1

// 指标页 / 甘特页
[...document.querySelectorAll('#kpi2 tr')].length > 0
[...document.querySelectorAll('#gantt tr[data-task]')].length === S.tasks.length
[...document.querySelectorAll('#gantt thead tr:first-child th')].length > 0

document.documentElement.scrollWidth <= window.innerWidth + 2   // 无横向溢出
```

指标页行数会明显少于指标条数——那是按主线折叠的首层，不是丢数据，点开主线才展开明细。

## 坑

- **不要用正则批量改 JS 语句补括号**：`$set('legend', '...' + '...';` 这种多行拼接，
  按“第一个分号”补 `)` 会插进字符串内部（把 `background:#FFF3CD` 变成 `background:#FFF3CD)`），
  语法检查报错的位置和真实出错点差好几行。含模板字符串或 HTML 的语句一律手工改。
- **开发期给 `app.js` 加个全局错误出口**，把异常写进 `#fstat`，这样页面检查时能直接看到错误文本，
  不用去翻控制台：
  ```js
  window.onerror = (m,s,l,c) => { const f=$el('fstat'); if(f) f.textContent='JS错误: '+m+' @'+l; return false; };
  ```
- **`$el` 判空不是可选项**：漏一处，那一页就整片空白，而其他页都正常，很容易误判成“这一页结构有问题”。
- **先跑通一页再复制其余四页**：`index.html` 通了说明 `app.js` 的拆函数和判空都对了，剩下的是模板填空。

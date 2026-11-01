# 原型验收协议 —— 结构测试会漏掉的那一类 bug

> 动因（2026-10-07 真实事故）：**71 项功能测试全绿，但表格四列数据全错位**，视觉终检才发现。
> 结构测试只验行数/筛选/分页，永远抓不到「数据落错列」这类 bug。

## 六道验收，缺一道漏一类

| # | 验收项 | 抓什么 | 自动化 |
|---|---|---|---|
| 1 | 功能测试（jsdom 驱动，含**负例**） | 交互不通、校验不拦 | ✅ `node test_x.js` |
| 2 | **数据→单元格映射测试** | **字段落错列 / 索引错位** | ⚠️ 必须手写断言 |
| 3 | 文字重叠量化 | 标签叠成一团 | ✅ `scripts/verify_render.py` |
| 4 | 关键短语存在性 | 内容没渲染 / 元素被挤出页外 | ✅ 同上 `--expect` |
| 5 | 页数 + 页面尺寸 | 内容溢出视口 / `@page` 没生效 | ✅ 同上 |
| 6 | 视觉终检（vision） | 前五道都测不出的观感错误 | ❌ 人工 |

**第 2 道最容易漏**，因为它「看起来已经测过了」—— 你测了行数，就以为测了表格。

## 第 2 道：数据→单元格映射怎么测

不要只数行数。**挑一行已知数据，逐列断言它的值。**

```js
const cell = (id, i) =>
  d.querySelector(`#tb tr[data-id="${id}"] td:nth-child(${i})`).textContent.trim();

ok('列映射·提供单位 = 社会救助处', cell(1, 2) === '社会救助处', cell(1, 2));
ok('列映射·共享类型 = 无条件共享', cell(1, 3).includes('无条件共享'), cell(1, 3));
ok('列映射·数据量 = 126,000',      cell(1, 4) === '126,000', cell(1, 4));
ok('列映射·更新周期 = 每月',        cell(1, 5) === '每月', cell(1, 5));
```

### 真实事故

同一份数据集在多个方向/变体里被写成了**不同的字段顺序**：

```js
// 变体甲: [id, name, code, org, SIZE, SHARE, CYCLE, UPDATED, status, flag]
// 变体乙: [id, name, code, org, SIZE, SHARE, status, flag, CYCLE]
// 渲染代码却沿用了同一套索引 r[4]/r[6]/r[7]/r[8]
```

后果：共享类型列显示数据量、数据量列显示更新周期、周期列显示日期、日期列显示状态 —— **四列全错**。
而行数、筛选、分页、状态联动**全部正常**，71 项测试全绿。

### 推论（结构性预防）

**多份手写数组 + 一套渲染代码时，索引错位是「必然」不是「偶然」。**
多方向共享渲染逻辑前，**先把数据结构归一化**：统一字段顺序，或干脆改成具名对象
（`{name, code, org, size, share, ...}`）。

## 第 3 道：文字重叠量化

```python
for a, b in itertools.combinations(pg.get_text('words'), 2):
    ra, rb = fitz.Rect(a[:4]), fitz.Rect(b[:4])
    if ra.intersects(rb):
        inter = (ra & rb).get_area()
        if inter / min(ra.get_area(), rb.get_area()) > 0.30:
            ...   # 记为重叠
```

判据：**相交面积 / 较小者 > 0.30**。

**别用「间距」当判据** —— 表格列天然相距很远，按间距判会把正常表格全标成问题。

## 第 5 道：页数与尺寸

- `page_count > 1` → 有内容溢出视口（`html,body{overflow:hidden}` **挡不住分页**）
- 尺寸必须 = 目标 CSS px × **0.75**（WeasyPrint 用 pt）；显示 `595×842` 就是**没指定 `@page`，按 A4 重排了**

## 第 6 道：视觉终检怎么问

**别问「好看吗」。用具体、可证伪的问题：**

- ❌「这张图怎么样？」
- ✅「第 5 行的提供单位/共享类型/数据量分别是什么？严格按表头对应读，不要脑补」
- ✅「有没有文字重叠、裁切、溢出？中文正常吗？」
- ✅「某个元素是显示成一行，还是被拆成了两行？」

**视觉模型会漏掉 10px 的小方块**（把「存在但很小」报成「不存在」）→
它说「没有」不等于没有，**必须配合程序量化**（第 3~5 道）。

## 图形/可视化类的额外一道

SVG 图的元素「是否存在」，用 DOM 数（`querySelectorAll('.doc').length`）**不够**：
元素都在 DOM 里，但**字号被忽略、坐标重叠、渲染成一团** —— DOM 查询完全看不出来。
必须量**渲染后**的 bbox 与字号分布。

---

# 附：两类 JS 侧「静默失效」（不报错，只是功能没了）

## 1. 监听器挂在会被重建的节点上 → 事件永不触发

```js
// ❌ renderCards() 里用 parentNode.innerHTML 重建了 tbody
//    这个 <tr id="card-row"> 被移除，监听器落在脱离文档的节点上
//    表现「点了没反应」；单测只测渲染结果，完全测不出来
 document.getElementById('card-row').addEventListener('click', ...);

// ✅ 挂在重建范围之外的稳定祖先上
 document.querySelector('table.cards').addEventListener('click', e => {
   const c = e.target.closest('.card'); if (!c) return;
   ...
 });
```

**自检**：任何用 `innerHTML` 重建的区块 → 确认监听器挂在**重建范围之外**。

## 2. `el.parentNode.innerHTML = html` 会把 `el` 自己替换掉

```js
// ❌ 第一次能跑，第二次 getElementById 返回 null → 抛
//    Cannot read properties of null (reading 'parentNode')
 document.getElementById('card-row').parentNode.innerHTML = rowsHtml;

// ✅ 写进一个不会消失的容器
 document.querySelector('#cards tbody').innerHTML = rowsHtml;
```

**表现**：首屏正常，**一筛选/搜索就崩或列表不更新** —— 很像业务逻辑 bug，其实是选择器把自己删了。

---

## 验收跑法

```bash
node test_x.js                                            # 1) 含负例 + 列映射断言
node render_states.js                                     # 2) 驱动到目标态 + 导快照
scripts/verify_render.py _shots/ --size 1440x940 --expect expect.json   # 3)~5)
scripts/probe_pagebreak.py _shots/1_xxx.html --block .acts              # 5) 失败时定位
# 6) 视觉终检：用上面那三个可证伪问题问
```

# 静态渲染器（WeasyPrint）会静默毁掉版面 10 类陷阱

> 实测环境：WeasyPrint **70.0**（`/opt/data/.venv`），2026-10-07。
> 共同特征：**不报错、不崩溃，只是版面悄悄变错**。所以必须用程序量化验证（见文末），不能靠肉眼看图。

## 1. `<button>` 的 `width:auto` 被解析成「占满可用宽度」

**症状**：一行 4 个按钮被摊开到 600pt（各约 190pt 宽），最后一个被挤到下一行或挤出容器（页外、**静默消失**）。

**实测无效的写法**：`width:max-content` / `width:fit-content` / `max-width:100%` / `vertical-align` 调整 —— 全部照旧摊开。

**唯一有效解**：`display:inline`。

```css
.pager button{display:inline; margin-left:16px}   /* ✅ */
.pager button{display:inline-block}              /* ❌ 被撑到 190pt */
```

**不要用 flex 容器放按钮**（flex 子项会被撑开，把后面的按钮挤出页外）。用 inline 流 + `margin` 排布，必要时 `white-space:nowrap`。

**浏览器一致性**：浏览器里 `button{display:inline}` 同样按内容宽度渲染，行为一致 → 这个改动是安全的，不是 hack。

## 2. 完全不渲染 `<input>`

**症状**：`<input>` 的 value、placeholder、`border-bottom`、背景 **什么都不画**。对搜索驱动的界面是致命伤（截图里搜索框整个消失）。

**解**：出图前把 `<input>` 换成同样 class 的 `<span>`，把 value（没有就画 placeholder）当普通文本渲染。

```js
doc.querySelectorAll('input').forEach(inp => {
  const sp = doc.createElement('span');
  const val = inp.value, ph = inp.getAttribute('placeholder') || '';
  sp.className = (inp.className ? inp.className + ' ' : '') + 'snap-field';
  sp.textContent = val || ph;
  if (!val && ph) sp.setAttribute('style', 'color:' + PLACEHOLDER_COLOR);  // 占位符灰度
  inp.parentNode.replaceChild(sp, inp);
});
```

**前提**：源码里输入框样式必须用 **class 选择器**（`.ask .field`），**不能**用标签选择器（`.ask input`）——后者在替换成 `span` 后失效。这一点要在写源码时就留好。

## 3. SVG `<text>` 不认 CSS 的 `font-size` / `fill`

**症状**：`.doc-t{font-size:9.5px}` 完全无效，所有 SVG 文字**一律按默认 14px** 渲染 → 标签互相压叠、图挤成一团。

**诊断信号**：`get_text('dict')` 统计 span 的 size，若全部落在同一个值（如清一色 14.0）就是 CSS 没生效。

**解**：写成 SVG 表现属性。

```html
<text x="10" y="20" font-size="9.5" fill="#22303a" text-anchor="start">标签</text>
```

**注意优先级**：CSS 优先级 > SVG 表现属性。所以两边都要写、且取同一个值——浏览器走 CSS，WeasyPrint 走属性，结果一致。

**以下 SVG 能力实测正常，可以放心用**：`text-anchor`（start/middle/end 三种都精确命中锚点）、`<g transform="translate(...)">`、白字压黑圆、`<rect>`、`<circle>`、`<path>`、`stroke-width`。

## 4. flex 的 `margin-left:auto` 不可靠

**症状 A**：右侧项被压到 min-content —— 「共 14 项」竖成三行（三个词的 x0 完全相同、宽度只剩 9pt）。
**症状 B**：右侧项被摊开 500pt（子项间距均匀分布）。
**症状 C**：绝对定位的 flex 容器宽度被算成**父容器宽** → 子项被均匀摊开；加 `text-align:right` 也无效。

**解**：`float:right`，且被浮动元素要放在**源码最前**。

```html
<div class="foot">
  <span class="right">右侧内容</span>   <!-- 必须放最前 -->
  <span>左侧内容会绕着它排</span>
</div>
```
```css
.foot .right{float:right}
.foot .note{display:block; overflow:hidden}   /* 防文字绕到浮动元素下面 */
```

**单行文本**的右侧对齐也可以直接 `position:absolute; right:0` + 手动调 `bottom` 对齐基线。

## 5. 必须显式指定 `@page{size:...}`

不指定时 WeasyPrint 默认 **A4（595×842pt）**，页面宽度被压到约 **794 CSS px** → 桌面版式（尤其是宽表格）全部重排、单元格换行变高、内容溢到第 2 页。而 `HTML(...).write_pdf()` 传的 `W,H` 变量**根本不起作用**。

```js
st.textContent = `
  @page{size:1440px 940px;margin:0}
  *,*::before,*::after{transition:none !important;animation:none !important}
  html,body{height:940px !important;overflow:hidden !important}
`;
```

**自查**：`fitz` 读 PDF 的 `page.rect` —— 若显示 595×842 就是没生效（期望 1080×705pt = 1440×940 CSS px）。

## 6. grid 的显式列放置 / `grid-auto-flow:column` 会丢子项

**症状**：`grid-column:3` 的元素**整块消失**；`grid-auto-flow:column` 的容器**只渲染第一个子项**。

**解**：这两个条形（工具栏、页脚）不要用 grid。用 inline 流 + 绝对定位 / float。

## 7. 其他不支持或行为异常的写法

| 写法 | 症状 | 替代 |
|---|---|---|
| `inset:0` | 尺寸塌陷、元素不可见 | `top/right/bottom/left` 四边分开写 |
| `min(a,b)` | 宽度计算失效 | 固定 `width` + `max-width` |
| `display:contents` | flex 布局塌（子元素不再是 flex item） | React Fragment / 去掉包裹层 |
| `box-shadow` 里用**带 alpha 的 oklch** | 直接抛 `NotImplementedError`（内部走渐变路径转不了 sRGB） | 阴影用 `rgb(r g b / a)` |
| `::placeholder` | 不渲染 | 见第 2 条 |
| `flex:1` + `overflow-y:auto` | 不收敛：侧栏清单把整体高度顶出视口（多出一页） | `display:grid; grid-template-rows:auto minmax(0,1fr)` 显式定行 |
| 覆盖层写在 grid/flex 容器**内部** | 被当成 grid/flex item 排进下一行（浏览器靠 `position:fixed` 侥幸掩盖） | 覆盖层做成容器的**兄弟节点** |

**oklch 本身是支持的**（`oklch(48% 0.09 245)` 实测转出 `rgb(58,97,141)`），只有「带 alpha 的 oklch 用在 box-shadow」这一种组合炸。

## 8. 量化验证法（不靠看图）

```python
import fitz
pg = fitz.open(pdf)[0]
```

| 要查什么 | 怎么查 | 判据 |
|---|---|---|
| 文字重叠 | 取 `get_text('words')` 全部 bbox 两两求交，算 `相交面积 / min(面积)` | > 0.30 判重叠 |
| 基线是否对齐 | `get_text('words')` 按 y 分行，打印每行的 `词@x0` | 同一行内 y 极差 < 2pt |
| 字号是否生效 | `get_text('dict')` 统计所有 span 的 `size` 分布 | 全落同一个值 = CSS 没生效 |
| 元素是否消失 | 全文 grep 关键字 | 缺 = 被挤出页外或没渲染 |
| 内容是否溢出视口 | `doc.page_count` | > 1 = 有溢出（`overflow:hidden` 挡不住分页） |
| 页面尺寸对不对 | `pg.rect.width/height` | 期望 = CSS px × 0.75 |

**这些检查比 vision 看图可靠得多** —— 视觉模型会漏掉 10px 的小方块（会把「存在但很小」报成「不存在」）。

## 9. 出图管线（本机无 chromium 时的完整链路）

```
jsdom 驱动真实交互（点击/键盘/输入）
  → 序列化 DOM 快照（删 script、替换 input、注入 @page + 冻结样式）
  → WeasyPrint 排 HTML → PDF
  → fitz 光栅化 → PNG（WeasyPrint 70 已移除 write_png）
```

**注意顺序**：WeasyPrint **不执行 JavaScript**。所以页面状态必须在 jsdom 里驱动好、序列化成静态 HTML，再交给它排版。

## 10. 快照脚本自身的坑（比渲染器陷阱更隐蔽）

**忘记切屏 = 截到上一屏。** 快照脚本驱动多个屏时，只调了「展开某一行」的动作、却没先调用切屏函数 —— 结果渲出来的是上一屏。

**快速自查：两张图的关键词数/词数完全相同 → 几乎一定是同一个屏。**（实测：5 个屏里第 4、5 张的词数与其他屏一模一样才被发现）

顺序不能反：**先切屏，再驱动状态。**

## 11. 分页溢出怎么定位（隔离实验法）

一个块整块掉到下一页且只差一点点时，不要猜。对同一份快照注入不同的**单条** CSS，逐个渲染并记录页数与第 1 页内容最底 y：

```python
CASES = {
  '0_原样':              '',
  '1_隐藏该块':          '.acts{display:none !important}',
  '2_该块 padding 归零': '.acts{padding:0 !important}',
  '3_隐藏上一个区块':    '.spread + .spread{display:none !important}',
  '4_该块去 nowrap':     '.acts{white-space:normal !important}',
  '5_页面加高 100pt':    '@page{size:1440px 1040px !important}',
}
# 逐个写文件 → WeasyPrint → fitz 读 page_count 与第1页 max(word.y1)
```

**判读规则**：
- 隐藏某块后页数变 1 → 就是那块放不下（不是它前面的内容有问题）
- 该块 `padding` 归零后变 1 → 只差几个 pt，从这个块的 padding / 内部行高里省
- 页面加高 100pt 后「内容最底」也只多一点点 → 确认是真溢出，不是分页副作用
- 隐藏某个前置区块看省了多少 → 知道哪一段最占地

**关键性质**：`white-space:nowrap` 的块**不会被拆分**，放不下就整块搬走 —— 所以“只差 1pt”也会整块跳页，看上去像“突然多出一整页”。此时不要大改，只需省 3-5pt。

## 12. 表单控件的可发现性

细到看不见的实线下划线（如 1px `#b9b2a4` 在暖白底上）会被读者 —— 包括 vision 模型 —— 当成**标签文字**而不是“要在这里填”。

台账/纸质表单的正统写法是**虚线填空线**：

```css
.fin,.fsel{border-bottom:1px dotted var(--ink-3)}
```

虚线同时传达了“这里要填”的语义，且比加粗实线更贴合纸质表格。错误态再换成实线朱色，对比更明确。

## 13. 交付前检查清单

1. 功能测试全绿（jsdom 驱动，改任何 CSS/结构后都要重跑）
2. 文字重叠 = 0（量化）
3. 关键短语全部存在（量化 grep）
4. 页数 = 1（或明确知道哪些内容在折叠线以下）
5. `pg.rect` 尺寸正确（= 目标 CSS px × 0.75）
6. 视觉终检（vision 看图，用具体问题问：文字内容/是否重叠/是否裁切）

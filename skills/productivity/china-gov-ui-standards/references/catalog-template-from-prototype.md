# 按原型数据复刻一条目录的编目模板（单条目录版）

> 场景：用户说「重新生成一份《政务数据目录编目模板_XX》**要和现在原型中的数据保持一致**」。
> 2026-10-11 实战（四川省自然人基本登记信息）。与批量版（`department-catalog-batch.md`）的区别：
> 这个要求**数据必须取自原型运行时**，不是照规格编；而且**必须真导入验证逐项一致**。

## 三步固定流程

### ① 抽真实值（playwright 打开交付 HTML，读运行时对象）

```python
info = pg.evaluate("""(() => {
  const cats = (window.APP.S && window.APP.S.catalogs) || [];
  const c = cats.find(x => (x.name || '').indexOf('自然人') >= 0) || cats[0];
  const D = window.DATA || {};
  return { catalog: { name: c.name, code: c.code, org: c.org, summary: c.summary,
                      source: c.source, domain: c.domain, level: c.level,
                      share: c.share, method: c.method, status: c.status },
           items: (D.catalog || {}).items || [],          // 数据项 15 项，键：cn/en/desc/type/len/…
           fields: (window.FORM_SPEC || []).flatMap(g => (g.fields||[]).map(f =>
                     ({ idx: f.idx, label: f.label, group: g.name, required: f.required,
                        values: f.values || [] }))) };
})()""")
```

要素取值只有三个来源，别乱找：

| 来源 | 拿到什么 |
|---|---|
| `window.APP.S.catalogs[i]` | 记录级：name/code/org/summary/source/domain/level/share/status/method/items/audits |
| `window.DATA.catalog.items` | 15 个数据项的全部属性（18+ 个键） |
| `window.FORM_SPEC` | 列顺序（组的数组位置）、必填标记、值域 |

⚠️ **记录里的 `vals` 往往是空对象**：`vals` 只在**文件导入**时逐要素写入；手工建的种子记录没有它。
别因为 `vals` 空就以为抽不到值 —— 记录级的那些键就是它的“已填要素”。

### ② 生成（`openpyxl`，沿用 `gen_template.py` 的渲染配方）

- **工作表1「政务数据目录编目模板」**：行1 标题 / 行2 填写说明 / 行4 属性组（合并单元格，蓝底白字）/ 行5 字段名（带 `*` `◐` 标记）/
  **行6 起才是数据行**（导入器在前 8 行里挑匹配数最多的一行当表头，这个布局正好合适）。
  37 要素 × 6 组（基础标识 4 / 数据特征 10 / 范围界定 6 / 共享开放 7 / 事项业务关联 8 / 发布管理 2），**列顺序 = 组内数组位置**（不是 idx）。
- **工作表2「数据项」**：第一列 = 数据目录名称（挂接键），**前 12 列列序固定**（见下），规格里其余属性追加在第 13 列之后。
- 取值的兜底规则：先查手工维护的 KEY/CAT 字典（关键要素的真实值），命中不了再取该要素值域的**第一个值**，仍无则空串。

### ③ 真导入验证（**这一步不能省，也不能只看文件**）

```python
pg.evaluate('window.APP.setRole("editor")')
pg.evaluate('window.APP.go("s1")')
pg.set_input_files('#file-upload', str(XLSX)); pg.wait_for_timeout(3000)
got = pg.evaluate("""(() => {
  const cats = window.APP.S.catalogs;
  const c = cats.filter(x => x.method === '数据目录导入').pop();
  return c ? { name: c.name, org: c.org, source: c.source, domain: c.domain, level: c.level,
               share: c.share, status: c.status, n: cats.length,
               items: (c.items||[]).map(i => ({cn:i.cn, en:i.en, type:i.type, len:i.len, pk:i.pk})) } : null; })()""")
assert len(got['items']) == 15
for a, r in zip(got['items'], ref_items):        # 与原型 DATA.catalog.items 逐项比
    assert all(str(a[k]) == str(r[k]) for k in ('cn', 'en', 'type', 'len', 'pk'))
```

判据口径（本次 12/12 全过）：目录总数 +1；名称/提供单位/领域/层级/共享属性/状态=待审核 全对；
**来源系统取值 ∈ 原型值域**；**15 项数据项按 cn/en/type/len/pk 逐项一致**。

## 硬接口：数据项工作表前 12 列（按列号读，不可重排）

导入器源码（`s1.js` 导入段）：只有「目录名称」列按表头名找，其余全按列号：

```js
cn: r[1], en: r[2], type: r[3], len: r[4], pk: r[5], req: r[6],
share: r[7], share_cond: r[8], open: r[9], open_cond: r[10], desc: r[11]
```

| 列 | 表头 | 来源键 |
|---|---|---|
| 1 | 数据目录名称 | 本次目录名（挂接键）|
| 2 | 数据项中文名称 | `cn` |
| 3 | 数据项英文名称 | `en` |
| 4 | 数据类型 | `type`（值域内：字符型C / 日期型D / 日期时间型T / 整型I / 浮点型F）|
| 5 | 长度 | `len` |
| 6 | 是否主键 | `pk` |
| 7 | 是否必填 | `nullable === '否' ? '是' : '否'` |
| 8 | 共享属性 | `share` |
| 9 | 共享条件 | `share_cond` |
| 10 | 开放属性 | `open` |
| 11 | 开放条件 | `open_cond` |
| 12 | 数据项描述 | `desc` |
| 13+ | 值域 / 值域名称 / 数据项来源系统 / 数据项来源系统所属分类 / 数据敏感级别 / 是否为法定源头 / 是否用于公共数据资源登记 | `has_domain` / `domain_name` / `src_sys` / `src_cat` / `sensitivity` / `legal_source` / `for_reg`（**导入器不读，仅人工核对**，底色用另一种）|

**真实事故**：我按规格标签把 19 列排成“数据项名称/英文名/**描述**/类型/长度/…”→ 导入后 15 项全错位
（描述→类型、类型→长度、长度→主键）。**“把表头改得更规范”在按位读的消费方面前 = 静默错位。**

## 交付前的两个自检

```python
# ① 必填项不得为空（条件项 ◐ 留空才是对的：不允许回流原因 / 共享频率说明 / 不予发布原因）
[h for c in cols if (h := str(ws.cell(5, c).value)).startswith('*') and not str(ws.cell(6, c).value or '').strip()]
# ② 每个取值为空的『提供单位/来源系统/所属领域』类字段，都要能说出“为什么空得对”
```

⚠️ 曾经漏的两个必填项：`*使用条件`、`*开放条件`（写上前缀“仅用于政务服务事项办理与数据核验，不得对外提供…”这类通行表述即可）。
事项业务关联的 6 个可选编码项（基本目录/业务项/实施清单的名称与编码）**不编造**，留空。

## 附带发现：值域一致性要查“既有种子数据”

本轮：原型种子目录的「数据来源系统」写着 **公安人口信息管理系统**，而当前值域里公安厅对应的是
**四川省人口基础信息库**（`SECLASS` → 国直）—— 原型自己内部不一致，用户一核文件名/内容就会发现。

处理：模板**写值域内的值**（+ 所属分类按 `SECLASS` 联动填 国直），交付说明里**明说这一处与原型记录不同、
原型那条是旧名**，并给出「要不要我把原型里那条也一起改」的选项；**不擅自改原型数据**（用户正在用它演示）。

## `pg.evaluate` 里的两个 JS 坑（本轮各挂一次）

1. **箭头函数包装写错 → `SyntaxError: Unexpected end of input`**（报在 evaluate，不在 Python）：
   `(() => [].slice.call(q))\n.map(e => ({…}))()` ← `.map` 落在箭头函数**外面**了。
   正确：`(() => [].slice.call(q).map(e => ({…})))()`（map 放进箭头体内，再 `()()` 闭合）。
2. **空数组上 `JSON.stringify(v[0]).slice(0,120)`** → `Cannot read properties of undefined`（`JSON.stringify(undefined)` 返回 undefined）：
   写 `String(JSON.stringify(v.length ? v[0] : null)).slice(0,120)`。

共同点：**这两个错都在浏览器侧抛，Python 栈里只能看到一行 `Page.evaluate: …`** —— 先看括号闭合与空数组，别怀疑数据。

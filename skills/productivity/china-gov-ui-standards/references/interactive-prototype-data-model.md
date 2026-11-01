# 可交互原型：数据模型 · 导入管线 · 零依赖 xlsx 解析

> 2026-10-10 实跑验证（V1.2）。场景：把「一条写死数据的演示原型」升级成
> **能手工新建、能文件导入、能逐条审核发布、且贯通到下游归集/治理**的真实原型。
> 交付形态是**单文件自包含 HTML，零外链、断网可用** —— 所以任何解析都必须自己写。

## 一、数据模型：集合 + 「当前操作对象」引用

### 为什么这样切

原实现全链路 8 个屏幕都读 `S.catalog`（单个对象）。要支持"可累积多条"，
直觉做法是把下游全改成遍历数组 —— 那是 8 个屏幕 + 全部测试的大改。

**改成"集合 + 指向其中一条的引用"，下游零改动**：

```js
var SEED_CATALOG = {
  code: 'R510000TAB' + today().replace(/-/g,'') + '00000001',
  name: '…', org: '…', summary: '…', source: '…',
  domain: '民生保障', level: '省级', share: '有条件共享',
  status: '已发布', published: true, collectStatus: '未归集',
  method: '手工新增', items: [], vals: {},
  audits: [{ node: '审核', role: '数据管理员', user: '李**',
             time: now(), opinion: '…' }],
  submitAt: now(), createdAt: now()
};

var S = { catalogs: [SEED_CATALOG], catalog: SEED_CATALOG, seq: 1, /* … */ };
```

新建：

```js
function addCatalog(rec) {
  var c = { /* 补默认值 */ };
  S.catalogs.push(c);
  S.catalog = c;                 // ← 关键：下游读的是这个引用
  return c;
}
function newCatalogCode() {
  S.seq += 1;
  return 'R510000TAB' + today().replace(/-/g,'') + ('0000000' + S.seq).slice(-8);
}
```

### 踩过的点

- **种子给「已发布」**：下游各屏（建表/归集/治理）一开始就有数据，不会空态。
- **重置功能要连集合一起复位**（`S.catalogs=[base]; S.catalog=base; S.seq=1;`），否则重置后序号继续涨、旧记录还在。
- **行内操作按钮的 id 唯一性**：只给当前操作那一行 `id="btn-collect"`，其余用 `data-coll="<编码>"`，
  点击时先 `S.catalog = 匹配记录` 再 `render()`，然后 `document.getElementById('btn-collect').click()` 复用原逻辑。
- **列表"来源方式"列**让两种建档方式在演示时可见。
- 角标改成按真实待办数（`S.catalogs.filter(c=>c.status==='待审核').length`）。

### 值一律按「要素名称」取，不按编号

内部编号 ≠ 显示顺序（补录字段是 55/56）。**`vals[N]` 字面量一律视为可疑**。

```js
var idxOf = function (label) { /* 遍历 FORM_SPEC 按 label 找 idx，见 SKILL.md 九之七 */ };
var get = function (lb, d) {
  var i = idxOf(lb);
  return String(i == null ? '' : (_v[i] || '')).trim() || d;
};
var cat = addCatalog({
  name: get('数据目录名称', '未命名数据目录'),
  org:  get('数据提供单位', '四川省公安厅'),
  summary: get('数据摘要', ''),
  source:  get('数据来源系统', '暂无系统'),
  domain:  get('数据所属领域', '民生保障')
});
```

> 事故症状：按 `vals[2]` 取「数据提供单位」，实际拿到**数据摘要** —— 每条记录的机构都变成摘要文案，
> 而字段渲染、校验、列表其它列全正常。

## 二、导入管线（CSV 与 xlsx 并轨）

### 形状归一（最容易漏的一步）

CSV 路径给的是**字符串**，xlsx 路径给的是**已解析的二维数组**。
若统一送进 `parseDelim`，后者会被当字符串再切一次（结果全错或空）。

```js
function asRows(x) { return Array.isArray(x) ? x : parseDelim(String(x == null ? '' : x)); }
```

### 表头按「要素名称」匹配

```js
function mapColumns(rows) {
  var labels = {};
  (window.FORM_SPEC || []).forEach(function (g) {
    (g.fields || []).forEach(function (f) { labels[String(f.label).trim()] = f.idx; });
  });
  var best = -1, bestN = 0, map = {};
  rows.slice(0, 8).forEach(function (r, ri) {
    var m = {}, n = 0;
    r.forEach(function (cell, ci) {
      var t = String(cell == null ? '' : cell).trim().replace(/^[◐*★\s]+/, '');  // 剥掉必填标记
      if (labels[t] !== undefined && m[labels[t]] === undefined) { m[labels[t]] = ci; n++; }
    });
    if (n > bestN) { bestN = n; best = ri; map = m; }
  });
  return { headRow: best, map: map, matched: bestN };
}
```

- `matched < 2` 时**明确报错并回显读到的首行**，不要静默生成 0 条。
- 目录名称列为空的行**跳过**（用 `idxOf('数据目录名称')` 定位，不要写 `vals[1]`）。
- 第 2 个工作表 = 数据项，首列「数据目录名称」作挂接键：`itemMap[名称] = [ ...items ]`。
- 导入完成：**先 `render()` 再弹结果表**（弹窗列出编码/名称/提供单位/领域/来源/数据项数）。
- 文件读入：xlsx 用 `readAsArrayBuffer`、CSV 用 `readAsText`；读完 `fi.value = ''` 以便重复选同一文件。

### CSV 解析（带引号转义）

```js
function parseDelim(text) {
  var rows = [], row = [], cur = '', q = false, i, ch;
  text = text.replace(/^\uFEFF/, '');           // 去 BOM
  for (i = 0; i < text.length; i++) {
    ch = text[i];
    if (q) {
      if (ch === '"') { if (text[i+1] === '"') { cur += '"'; i++; } else { q = false; } }
      else { cur += ch; }
    } else if (ch === '"') { q = true; }
    else if (ch === ',' || ch === '\t') { row.push(cur); cur = ''; }
    else if (ch === '\n') { row.push(cur); rows.push(row); row = []; cur = ''; }
    else if (ch !== '\r') { cur += ch; }
  }
  if (cur !== '' || row.length) { row.push(cur); rows.push(row); }
  return rows.filter(function (r) { return r.some(function (c) { return String(c || '').trim(); }); });
}
```

## 三、浏览器内零依赖解析 xlsx（可直接拷）

xlsx 就是 ZIP。只需支持 **stored(0)** 与 **deflate(8)**；
后者用浏览器原生 `DecompressionStream('deflate-raw')`（Chrome 80+），**不需要引 SheetJS**。

```js
function unzipEntries(buf) {
  var dv = new DataView(buf), u8 = new Uint8Array(buf), out = [], p = -1, i;
  for (i = buf.byteLength - 22; i >= 0 && i > buf.byteLength - 66000; i--) {
    if (dv.getUint32(i, true) === 0x06054b50) { p = i; break; }      // EOCD
  }
  if (p < 0) throw new Error('不是有效的 xlsx 文件（未找到 ZIP 目录）');
  var n = dv.getUint16(p + 10, true), off = dv.getUint32(p + 16, true);
  for (var k = 0; k < n; k++) {
    if (dv.getUint32(off, true) !== 0x02014b50) { break; }            // 中央目录条目
    var method = dv.getUint16(off + 10, true);
    var csize  = dv.getUint32(off + 20, true);
    var nlen   = dv.getUint16(off + 28, true);
    var elen   = dv.getUint16(off + 30, true);
    var clen   = dv.getUint16(off + 32, true);
    var lho    = dv.getUint32(off + 42, true);
    var name   = new TextDecoder().decode(u8.subarray(off + 46, off + 46 + nlen));
    var lnlen  = dv.getUint16(lho + 26, true), lelen = dv.getUint16(lho + 28, true);
    var st     = lho + 30 + lnlen + lelen;                            // 本地头之后即数据
    out.push({ name: name, method: method, data: u8.subarray(st, st + csize) });
    off += 46 + nlen + elen + clen;
  }
  return out;
}

function entryText(buf, name) {
  var e = unzipEntries(buf).filter(function (x) { return x.name === name; })[0];
  if (!e) return Promise.resolve(null);
  if (e.method === 0) return Promise.resolve(new TextDecoder().decode(e.data));
  if (typeof DecompressionStream === 'undefined') {
    return Promise.reject(new Error('当前浏览器不支持解压，请使用 Chrome / Edge 打开'));
  }
  var st = new Blob([e.data]).stream().pipeThrough(new DecompressionStream('deflate-raw'));
  return new Response(st).text();
}

/* 单元格 → 二维数组；t="s" 走 sharedStrings，t="inlineStr" 走 is，其余取 v */
function sheetRows(xml, shared) {
  var doc = new DOMParser().parseFromString(xml, 'application/xml');
  var out = [], rl = doc.getElementsByTagName('row'), i, j, q;
  for (i = 0; i < rl.length; i++) {
    var row = [], cl = rl[i].getElementsByTagName('c');
    for (j = 0; j < cl.length; j++) {
      var c = cl[j], ref = c.getAttribute('r') || '', col = 0, m = ref.match(/^[A-Z]+/);
      if (m) { for (q = 0; q < m[0].length; q++) { col = col * 26 + (m[0].charCodeAt(q) - 64); } col -= 1; }
      var typ = c.getAttribute('t'), v = c.getElementsByTagName('v')[0], val = '';
      if (typ === 's' && v) { val = shared[parseInt(v.textContent, 10)] || ''; }
      else if (typ === 'inlineStr') {
        var is = c.getElementsByTagName('is')[0]; val = is ? is.textContent : '';
      } else if (v) { val = v.textContent; }
      row[col] = val;                       // 注意：按 r 属性定位列，空单元格不出现在 XML 里
    }
    out.push(row);
  }
  return out;
}

/* 读全部工作表 —— 返回 [[[cell,…],…], …]，与 CSV 解析后形状一致 */
function xlsxSheets(buf) {
  return entryText(buf, 'xl/sharedStrings.xml').then(function (ss) {
    var shared = [];
    if (ss) {
      var d = new DOMParser().parseFromString(ss, 'application/xml');
      var si = d.getElementsByTagName('si');
      for (var i = 0; i < si.length; i++) {
        var ts = si[i].getElementsByTagName('t'), s = '';
        for (var j = 0; j < ts.length; j++) { s += ts[j].textContent; }
        shared.push(s);
      }
    }
    var names = unzipEntries(buf).map(function (x) { return x.name; })
      .filter(function (n) { return /^xl\/worksheets\/sheet\d+\.xml$/.test(n); })
      .sort(function (a, b) {
        return parseInt(a.replace(/\D+/g, ''), 10) - parseInt(b.replace(/\D+/g, ''), 10);
      });
    if (!names.length) throw new Error('文件中未找到工作表');
    return Promise.all(names.map(function (n) { return entryText(buf, n); }))
      .then(function (xs) { return xs.map(function (x) { return x ? sheetRows(x, shared) : []; }); });
  });
}
```

### 已知边界

- **Excel 重存后会改成 deflate** —— 已覆盖（`DecompressionStream`），不要只处理 stored。
- 依赖**中央目录里带尺寸**（Excel 正常如此）；zip64 大文件未处理，编目模板量级用不到。
- 单元格**必须按 `r` 属性算列号**，不能按出现顺序 —— 空单元格不在 XML 里（否则整行列错位）。
- 解析失败要**弹明确错误 + 建议"另存为 CSV 再导入"**，不要静默。

## 四、配套模板生成（从 form_spec 渲染，不手写）

```python
spec   = json.load(open('data/form_spec.json'))
groups = [g for g in spec if not g.get('isTable')]      # 数据项组是表，不进主表

# 行 4 = 属性组（合并单元格），行 5 = 字段名（* 必填 / ◐ 条件必填），行 6+ = 样例数据
for g in groups:                     # ⚠️ g 是 dict，不要写成 for gname, g in groups
    gname = g['name']
    for f in g['fields']:
        MARK = '*' if f.get('required') == 'req' else ('◐' if f.get('required') == 'cond' else '')
        ws.cell(r_fld, col, MARK + str(f['label']))
# 第 2 个工作表：数据项，首列「数据目录名称」作挂接键
```

- 样例数据要**覆盖各属性组**（值域字段取第一个合法值），让人一眼看出模板怎么填。
- 模板与交付 HTML 一起给用户，**文件名带业务含义**（`政务数据目录编目模板.xlsx`）。
- 生成器脚本放项目 `proto/` 下，与 `build.py` 同批维护。

## 五、这类改动的验证清单

专项脚本（本次 38 项）至少覆盖：

1. **初始态**：`catalogs.length == 1`、种子状态、`S.catalog` 指向同一条。
2. **手工新增**：提交后 `catalogs.length +1`、**新编码 ≠ 种子编码**、状态「待审核」、
   来源方式「手工新增」、**带上了数据项**。
3. **列表/审批可见**：列表行数增加、出现「来源方式」列、审批页待审核行数正确、`#btn-audit2` 存在。
4. **审核发布贯通**：审核后状态「已发布」、审核记录 1 条（一步）、已发布数 +1、
   **归集工单里绑定的是新建/导入的目录名**（不是种子）。
5. **导入**：`set_input_files` 上传真模板 → 数量 `+6`、名称/提供单位/领域**逐项断言**、
   数据项按目录名称挂接成功、结果弹窗文案含条数。
6. **导入的目录同样贯通**：审批页 6 条可选、点选切换当前目录、审核发布、可发起归集。
7. **零 JS 错误**（`pageerror` 收集）。

⚠️ **`set_input_files` 后要多等**（解析 + 建记录），本次用 2500ms；
断言前先确认 `catalogs.length` 已到位，不要用固定 sleep 赌。

⚠️ 回归时留意**依赖"天然待审核"的旧测试**：种子改成「已发布」后，
"直接进审批页就点审核"的脚本会超时 —— 正解是**先提交再断言**（也才是真实流转）。

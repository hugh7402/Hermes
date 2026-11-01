# 演示数据完整性：上传即现算、统计与明细同源

来源：2026-10-10 第三轮原型改造（用户要求「原型不能完全是静态数据」「支持文件导入」，
并要求生成约 100 条的归集离线数据）。

## 一、为什么必须现算

一旦原型允许**上传数据文件**用于现场演示，页面里任何写死的统计都会立刻自相矛盾：
上传 100 条、KPI 显示 1000 条；KPI 说某类问题 0 条、明细清单里却有十几行。

两类矛盾：

| 矛盾 | 成因 | 后果 |
|---|---|---|
| 行数对不上 | 统计写死 | 「我传了 100 条，为什么显示 1000」 |
| 统计与明细对不上 | 只重算统计、没重建明细 | 「该类共 0 条」但清单有 18 行 —— **最伤可信度** |

**铁律：派生统计被重算时，其明细清单必须在同一次重算里重建，并成对替换。**

## 二、内置与外部导入的分工（避免推翻已验收叙事）

```js
// 内置数据集：每个数字都被人复核过、演示话术也按它写过 → 不重算
var builtin = !!(window.DATA && window.DATA.stats && window.DATA.stats.total === n);
if (!builtin) {
  var pr = computeStats(lines, true);          // withProblems = true
  if (pr) {
    window.DATA = window.DATA || {};
    window.DATA.stats = pr.stats;              // 统计
    window.DATA.problems = pr.problems;        // 明细（必须成对）
    C().stats = pr.stats;
  }
}
```

判据：内置那份的数字**进过测试断言、进过演示话术** → 重算等于把已验收的东西推翻。
外部文件必须现算，否则行数就对不上。

## 三、现算规则的可拷实现（纯 JS，零依赖）

```js
/* 口径：total − dup_removed = after_dedup(清洗总量) = good(优质) + problem(问题)
   问题四类：过滤（校验码不通过）/ 转换（格式转换）/ 保留原值（与权威源不一致）/ 去重 */
function computeStats(lines, withProblems) {
  var hdr = (lines[0] || '').replace(/^\uFEFF/, '').split(',').map(function (x) { return x.trim(); });
  // 按「列名包含关键字」定位，允许模板加列/换序
  var pick = function () {
    for (var a = 0; a < arguments.length; a++) {
      for (var j = 0; j < hdr.length; j++) { if (hdr[j].indexOf(arguments[a]) >= 0) { return j; } }
    }
    return -1;
  };
  var iUid = pick('唯一标识'), iId = pick('身份证'), iName = pick('姓名'),
      iBirth = pick('出生日期'), iSex = pick('性别');
  if (iUid < 0) { return null; }               // 认不出关键列就明确失败，别静默出 0 条

  var recs = [];
  for (var i = 1; i < lines.length; i++) {
    if (lines[i].trim()) { recs.push(lines[i].split(',')); }
  }
  if (!recs.length) { return null; }

  // ★ 权威源索引方向必须按业务语义：主关联字段=身份证号，验证字段=姓名
  //   → 建「姓名 → 身份证号」；反着建会一条都命中不了（本次算出 0 条才发现）
  var authByName = {}, authById = {};
  (window.DATA && window.DATA.auth || []).forEach(function (row) {
    if (iId >= 0) { authById[row[iId]] = row[iName >= 0 ? iName : 0]; }
    if (iName >= 0) { authByName[row[iName]] = row[iId]; }
  });

  var idOk = function (s) {                    // GB 11643 校验码要真算
    if (!s || !/^\d{17}[\dXx]$/.test(s)) { return false; }
    var w = [7,9,10,5,8,4,2,1,6,3,7,9,10,5,8,4,2], c = '10X98765432', sum = 0;
    for (var k = 0; k < 17; k++) { sum += (parseInt(s.charAt(k), 10) || 0) * w[k]; }
    return c.charAt(sum % 11) === s.charAt(17).toUpperCase();
  };

  // ① 去重（保留首条）
  var seenU = {}, dupRemoved = 0, kept = [];
  recs.forEach(function (c) {
    var u = c[iUid] || '';
    if (seenU[u]) { dupRemoved++; return; }
    seenU[u] = 1; kept.push(c);
  });

  // ② 逐行判定（每行只归一类，保证四类相加 == 问题数）
  var pFilter = 0, pConvert = 0, pKeep = 0, pDup = 0, seenId = {}, prob = withProblems ? [] : null;
  kept.forEach(function (c) {
    var uid = c[iUid] || '', idv = iId >= 0 ? (c[iId] || '') : '',
        nm = iName >= 0 ? (c[iName] || '') : '',
        birth = iBirth >= 0 ? (c[iBirth] || '') : '', sex = iSex >= 0 ? (c[iSex] || '') : '';
    var type = '', field = '', rule = '', act = '', o = '', a = '';
    if (iId >= 0 && !idOk(idv)) {
      type = '过滤'; field = '身份证件号码'; rule = '一数一标准·身份证件号码 GB 11643 校验';
      act = '校验不通过，标记过滤待整改（未写入清洗仓有效集）'; o = idv;
    } else if (iBirth >= 0 && birth && !/^\d{4}-\d{2}-\d{2}$/.test(birth)) {
      type = '转换'; field = '出生日期'; rule = '一数一标准·出生日期格式 YYYY-MM-DD';
      act = '按标准规则转换为规范值后写入清洗仓'; o = birth;
    } else if (iSex >= 0 && sex && ['男','女','未知'].indexOf(sex) < 0) {
      type = '转换'; field = '性别'; rule = '一数一标准·性别值域 {男,女,未知}';
      act = '按标准规则转换为规范值后写入清洗仓'; o = sex;
    } else if (iName >= 0 && iId >= 0 && authByName[nm] && authByName[nm] !== idv) {
      type = '保留原值'; field = '姓名';
      rule = '一数一源·主关联字段=身份证件号码，验证字段=姓名';
      act = '保留原值（记入问题清单待业务确认）'; o = idv; a = authByName[nm];
    } else if (iId >= 0 && idv && seenId[idv]) {
      type = '去重'; field = '自然人唯一标识';
      rule = '一数一标准·自然人唯一标识唯一性校验'; act = '重复记录，仅保留首条'; o = uid;
    } else if (iId >= 0 && idv) { seenId[idv] = 1; }

    if (type === '过滤') { pFilter++; }
    else if (type === '转换') { pConvert++; }
    else if (type === '保留原值') { pKeep++; }
    else if (type === '去重') { pDup++; }
    if (prob && type) {
      prob.push({ n: prob.length + 1, t: type, f: field, rid: uid, key: uid,
                  o: o, a: a, act: act, rule: rule });
    }
  });
  var problem = pFilter + pConvert + pKeep + pDup, after = kept.length;
  var stats = {
    total: recs.length, dup_removed: dupRemoved, after_dedup: after, cleaned: after,
    good: after - problem, problem: problem,
    by_type: { '过滤': pFilter, '转换': pConvert, '保留原值': pKeep, '去重': pDup }
  };
  return withProblems ? { stats: stats, problems: prob } : stats;
}
```

**两处关键设计**：

1. **每行只归一类**，所以「四类相加 == 问题数」「清洗总量 == 优质 + 问题」**由构造保证**，
   不需要额外校验。若允许一行同时命中多类，这两个恒等式就断了。
2. **明细条目的 `rid` 用「唯一标识」而不是行下标** —— 与九之五同源：
   任何重排/抽样后，下标都会失效；用业务唯一键才追得回原记录。

## 四、抽样生成小数据集

用户要「约 100 条」时：

```python
step = max(1, len(body) // 100)
sample = [body[i] for i in range(0, len(body), step)][:100]   # 等间隔，保问题数据比例
```

⚠️ **不要取前 100 条** —— 问题数据若集中在后面，小数据集里一条都没有，治理环节演示不出来。
⚠️ 抽样后**不要**沿用大数据的统计（行数对不上），要靠上面的现算逻辑。
⚠️ 统计「取样里含多少条问题」时，注意源 CSV **可能不含 `_rid` 列**（打包用的键不进交付 CSV），
`hdr.index('_rid')` 会返回 -1，统计出 0 条是**统计代码的问题**，不是数据的问题 ——
先确认列在不在，再下结论。

## 五、验证清单

- [ ] 上传内置数据集 → 统计**与上传前完全一致**（不走重算分支）
- [ ] 上传外部文件 → `total` == 文件实际行数
- [ ] `after_dedup == good + problem` 且 `total − dup_removed == after_dedup`
- [ ] `sum(by_type.values()) == problem`
- [ ] 明细清单条数 == `problem`，且按类型筛出的条数 == `by_type[类型]`
- [ ] 抽查一条明细：`rid` 能在源文件里找到对应记录

# 演示数据的「语义」配方（既有实体 / 时间线 / 真实字段 / 外科式修正）

> 来源：2026-10-10 第四、五轮原型迭代。用户两次直接纠出演示数据的**逻辑硬伤** ——
> 这两类错**功能测试全绿也照样漏**，只有"业务上说得通吗"这一问能拦住。
> 配套 SKILL.md 章节：九之十三。

---

## 一、时间线语义：既有实体 vs 本次新建

### 症状

弹窗写着「三处创建时间与工单审批通过时间一致 = 证明是本次审批后自动建表」，
而三处分别是**前置仓表 / 归集仓表 / 离线归集任务**。
用户一句反驳即崩：**「前置仓的表应该是以前就存在的」**。

### 正确模型

```js
function buildTables() {
  var c = C();
  if (c.tables) return;
  var t = c.techAuditAt || A().now();
  c.tables = {
    // 既有表：数据先落地，早于本次工单
    前置仓: { name: 'ods_' + c.table, created: c.stagedAt || A().fsDays(3),
              fields: 15, rows: c.rows || 1000, existed: true },
    // 本次新建：审批通过才建
    归集仓: { name: 'dwd_' + c.table, created: t, fields: 15, rows: 0, existed: false },
    任务:   { name: c.orderNo + '_' + c.table + '_offline', created: t,
              type: '离线归集', status: '待执行' }
  };
  c.task = c.tables.任务;
  A().S.done.table = true;
  A().S.done.tech = true;
}
```

辅助函数（app 层，导出给各屏复用）：

```js
/* n 天前的时刻（用于表示「既有表」的创建时间） */
function fsDays(n) {
  var d = new Date(Date.now() - n * 86400000), p = function (x) { return (x < 10 ? '0' : '') + x; };
  return d.getFullYear() + '-' + p(d.getMonth() + 1) + '-' + p(d.getDate()) + ' ' +
         p(d.getHours()) + ':' + p(d.getMinutes()) + ':' + p(d.getSeconds());
}
```

### 「归集前 / 归集后」空态对照（这才是"流程"看得见的证据）

归集数据库：**归集前 0 张表**，并明确提示"执行归集后才会新增"；执行后才出现 1 张表 + 字段。

```js
/* 归集数据库：归集前为空，归集后才新增该表 */
if (!isOds && !c.taskRun) {
  return html +
    '<div class="notice warn"><span class="ic">!</span><div>归集数据库中<b>暂无</b>该表。' +
    '前置数据库已有表 <span class="mono">' + A().esc('ods_' + c.table) + '</span>，' +
    '需执行归集任务后，归集库才会新增对应表并写入数据。</div></div>' + /* KPI：0 张 / 待新增 1 张 */
    /* 表格：colspan 空态说明 */ ;
}
```

KPI 必须**区分标签**：`既有表` / `本次新建`，不要两栏都写"本次新建"。

### 验证要点文案的正确写法

```js
'验证要点：<b>归集仓表</b>与<b>离线归集任务</b>的创建时间 = 工单审批通过时间（本次自动建表）；'
+ '<b>前置仓表</b>为既有表，创建于 ' + A().esc(tb.前置仓.created) + '（早于本次归集，数据已先行落地）。'
```

**前置仓页那句"创建时间 = 工单审批通过时间"要直接删掉** —— 它是错的。

### 配套：默认就绪但不隐藏按钮

```js
// app.js 状态里：前置仓（ODS）为既有库表，默认已存在且数据已落地
collect: { staged: true, stagedAt: fsDays(3), rows: 1000, /* … */ }
```

```js
// s5 操作条：已就绪时改文案，但按钮仍在（自动化与演示都要还能点）
(c.staged ? '<span class="btn" id="btn-stage">📎 重新录入待归集数据</span>'
          : '<span class="btn pri" id="btn-stage">📎 录入待归集数据</span>') +
'<input type="file" id="file-data" accept=".csv,.txt" style="display:none">'
```

⚠️ 改这类三元表达式时**不要把 `+` 链写坏** —— 多一个悬空的 `: '')`
会让整个内联 script 抛 `SyntaxError`、页面白屏。构建的 `node --check` 门禁能一秒定位。

---

## 二、字段必须真在 schema 里（展示层 vs 数据层）

### 反面案例

用户要求把「保留原值」样本从"姓名不一致"换成"日常常见的问题"。
第一版**只在构建脚本里后处理问题明细**，把字段名改成「联系电话」并合成假的号码对。

**问题**：该目录的 **15 个数据项里没有「联系电话」**（实际是：自然人唯一标识 / 身份证件类型 /
身份证件号码 / 姓名 / 曾用名 / 性别 / 出生日期 / 民族 / 国籍 / 政治面貌 / 宗教信仰 /
兵役状况 / 数据批次号 / 数据融合加工时间 / 户籍地省市县代码）。
专家对照数据项清单即可发现该字段不存在。

### 自查动作

```bash
# 动"展示"之前，先确认字段在规格里
python3 -c "import json;d=json.load(open('data/demo_dataset.json'));
print([f['cn'] for f in d['catalog']['fields']])"
```

### 正解：换成 schema 内、且异常类型合理的字段

选字段的判据（用户原话："姓名不一致**通常不会发生**"）：

| 字段类 | 该不该用它做「保留原值」样本 |
|---|---|
| 姓名 / 身份证号 | ❌ 极少发生 —— 用了会被当场指出 |
| 联系电话 / 住址 / 政治面貌 / 文化程度 | ✅ 变更频繁、权威源更新滞后，日常高频 |
| 性别 / 出生日期 / 行政区划代码 | ⚠️ 属值域·格式类，归「转换」不归「保留原值」|

本次落地：**政治面貌**。业务语义一句话讲得清——
"业务系统政治面貌为最新登记，公安人口库登记滞后 → 按策略保留原值，记入问题清单待业务确认"。

顺带要改的：
- 问题条目的 `field` / `rule` / `action` / `orig` / `authority`
- `rule_source.verify_field`（一数一源配置页会显示它）

---

## 三、外科式数据修正（不要重跑随机生成器）

生成器含随机过程（未固定种子）→ 重跑会让验收过的五项数字漂移。
**在冻结的数据集上就地修正**：

```python
import json, collections, pathlib
DS = pathlib.Path('data/demo_dataset.json')
d = json.loads(DS.read_text(encoding='utf-8'))
rows, auth, probs = d['rows'], d['authority_rows'], d['problems']

byRid     = {r['_rid']: r for r in rows}
authByRid = {a['_rid']: a for a in auth}
authById  = {}
for a in auth:
    authById.setdefault(a['sfzjhm'], a)      # 兜底：按业务唯一标识配对

ALT = {'群众': '共青团员', '中共党员': '群众', '共青团员': '群众', '民主党派': '群众'}
for p in [x for x in probs if x['type'] == '保留原值']:
    r = byRid.get(p['_rid'])
    a = authByRid.get(p['_rid']) or authById.get(r['sfzjhm'])
    r['xm'] = a['xm']                        # ① 还原上一版被改坏的值
    cur, wrong = r['zzmm'], ALT.get(r['zzmm'], '群众')
    a['zzmm'] = wrong                        # ② 权威源登记为滞后值
    p.update(field='政治面貌', key=r['zrrwybs'], orig=cur, authority=wrong,
             rule='一数一源·主关联字段=身份证件号码，验证字段=政治面貌',
             action='业务系统政治面貌为最新登记，权威源登记滞后 → 按策略保留原值，记入问题清单待业务确认')

d['rule_source']['verify_field'] = '政治面貌'

# ③ 计数守护：改完立刻断言口径未变
cnt = collections.Counter(p['type'] for p in probs)
assert cnt.get('保留原值') == 18 and sum(cnt.values()) == 66, f'问题数被破坏：{cnt}'
DS.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding='utf-8')
```

改完**重新输出全部 CSV**（源 `data/` 与交付 `交付/演示数据/` 两处都要，
否则交付包与内嵌数据不一致）。

### 让"规则真跑得出来"变成可执行断言

不要只靠口头保证。校验脚本里逐条核对：

```python
for p in [x for x in probs if x['type'] == '保留原值']:
    r = BY[p['_rid']]; a = AUTH.get(p['_rid'])
    if a and a['zzmm'] != r['zzmm'] and p['orig'] == r['zzmm'] and p['authority'] == a['zzmm']:
        mis += 1
print(f'→ {mis}/{len(kk)} 条确实不一致  {"✅ 通过" if mis == len(kk) else "❌ 失败"}')
```

---

## 四、抽样报告说"0"时先查匹配键

**事故**：抽样脚本报"取样中含问题数据 0 条"，实际 7 条。
根因：用内部主键 `_rid` 列匹配，而**导出的 CSV 里没有 `_rid`**，
`hdr.index('_rid')` 返回 -1 后静默跳过，计数恒为 0。

```python
# ❌ 错：内部主键不外发，CSV 里没有这一列
rid_i = hdr.index('_rid') if '_rid' in hdr else -1

# ✅ 对：用业务唯一标识列匹配
prob_keys = {p['key'] for p in ds['problems']}
key_i = hdr.index('自然人唯一标识')
n_prob = sum(1 for r in sample if r[key_i] in prob_keys)
```

**通则：任何"计数为 0"的结论，先验证计数用的键在数据里真实存在。**

### 小数据集要等间隔抽样，不要取前 N 条

```python
step = max(1, len(body) // 100)          # 1000 行 → 每 10 行取 1 条
sample = [body[i] for i in range(0, len(body), step)][:100]
```

取前 100 条可能一条问题数据都没有，治理环节就演示不出来。
（本次等间隔抽样后：100 行含 7 条问题，覆盖身份证件号码 / 出生日期 / 性别 / 政治面貌 4 个字段。）

---

## 五、只读详情页不要出现两个同名字段

**事故**：归集工单详情里「归集方式」出现两次 ——
一条 `c.dock`（数据绑定），一条写死 `'离线归集'`。

```js
// ❌ 删掉这一类：旁边塞一个写死的占位值
'<div class="r"><div class="k">归集方式</div><div class="v">' + A().esc(c.dock || '库表对接') + '</div></div>' +
'<div class="r"><div class="k">归集方式</div><div class="v">离线归集</div></div>' +
```

**通则：只读详情页的每个字段都要与创建它的表单同源。**
同名字段只留一条，且必须取自数据。

---

## 六、"系统按它执行"的只读表格要给编辑入口

用户原话：**"这些表结构信息应该可以编辑修改，后面增加编辑功能"**。

适用对象：**下游会按它执行**的展示型表格 —— 表结构信息、治理规则、数据项清单。

形状：
- 【✎ 编辑表结构】按钮 → 抽屉内**逐行可改**（下拉/输入框），字段名**只读并说明原因**
  （"与数据项保持一致，不可修改"）
- 保存后**下游按新值执行**（写回 `window.DATA.fields`，自动建表读它）
- 保存后重绘 + toast 回显改了**几个字段**

```js
// 保存：逐字段回写，pk/nullable 这类相反语义要显式转换，别直接赋值
flds.forEach(function (f, i) {
  var t = document.getElementById('st-type-' + i);
  var l = document.getElementById('st-len-' + i);
  var p = document.getElementById('st-pk-' + i);
  var nn = document.getElementById('st-nn-' + i);
  if (t) f.type = t.value;
  if (l) f.len = String(l.value || '').trim();
  if (p) f.pk = p.value;
  if (nn) f.nullable = nn.value === '是' ? '否' : '是';   // 「是否非空」→ 内部 nullable 取反
});
```

配套的"动作型"功能同理（本次一并补齐）：
- 列表【查看】→ 详情抽屉（要素 + 数据项清单）
- 工单【查看】→ 工单详情抽屉（工单信息 + 各环节审核状态与意见）
- 任务【详情】→ 任务抽屉（前后仓表名 / 字段数 / 行数 / 状态 + 执行入口）
- 治理任务【重新执行】→ 确认弹窗 → `running` → 延时 `done` + 刷新统计

---

## 七、改动后的回归清单（本次实际用到）

结构/语义一改，必跑的判定顺序：

1. **构建门禁**：`node --check` + 合规词扫描 + 旧产物清理（先说话）
2. **数据级校验**：规则是否真跑得出来（本次 6/6）
3. **端到端**：全链路能否走通
4. **逐条判定失败**：是「真 bug」还是「过时断言」

⚠️ 本次三个**过时断言**（改语义后必然出现，别去"修"代码）：
- e2e「三处创建时间一致」→ 新语义下**本来就不该一致**（前置仓必须更早）
- `verify_chrome`「进度条 3 段」→ 段数已因职责重划变为 6
- 测试里写死的版本号「V1.1」→ 改为从文件名反推

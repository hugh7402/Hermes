# 高保真政务原型的保真度自查（2026-10-10 第五轮反馈 V1.6 + V1.7）

来源：用户《问题反馈表》第 42~53 条（累积表，前 41 条此前已完成）+ 无反馈表的 V1.7 自查。

## 一、第 42~53 条逐条落点

| 序号 | 要求 | 落点 |
|---|---|---|
| 42 | 删除导入弹窗流程说明文字 | `s1.js` 导入结果弹窗末尾的 `mut sm` div |
| 43 | 导入结果要展示目录要素填充效果 | 弹窗内按**属性组**逐项列出 `c.vals`（基础标识/数据特征/范围界定/共享开放/事项业务关联）|
| 44 | s3 归集工单【查看】实现 | `[data-view]` → `openDrawer` 工单详情（编号/表英文名/归集方式/状态/审核时间 + 字段映射表）|
| 45 | 所有「留在本页」→「取消」 | 10 处（s1×2/s1b/s2/s3/s4/s5/s6×2/s7）|
| 46 | 编辑表结构（核实是否已实现） | **早已实现**，但入口在**技术审核抽屉内**（`#btn-edit-struct`），不是 s4 主页面 |
| 47 | 删除弹窗「验证要点」 | s4 建表完成弹窗 + s6 规则审批弹窗（**连 notice 容器一起删**）|
| 48 | 自动建表过程要动态（时间戳不能全一样） | 每步 `plusMs(基准, i*320)` + 毫秒后缀 + 耗时 |
| 49 | 删除「✓ 三处时间一致」 | s4 eqbar 的 `span.chk`（3 处，含抽屉里的两条）|
| 50 | 问题字段不要都一样 | 见下方第三节（规则改多选 + 数据层真冲突）|
| 51/52 | 删除【重置数据】按钮 | s8 右上角 + 底部两处，连 `['restart','restart2']` 绑定逻辑一起删 |
| 53 | 删除 s7c 操作条视窗说明文字 | s7.js 的 `actbar .tip` 内文案 |

## 二、第 43 条：导入结果展示「目录要素填充效果」的可拷写法

按 `FORM_SPEC` 的属性组逐组列出**非空**要素，空组不渲染：

```js
made.slice(0, 3).map(function (c) {
  var gs = (window.FORM_SPEC || []).filter(function (g) { return !g.isTable; });
  return '<div class="panel"><div class="ph"><h3>' + A().esc(c.name) + ' · 目录要素</h3>' +
    '<span class="meta">' + A().esc(c.method) + '</span></div><div class="pb">' +
    gs.map(function (g) {
      var rows = g.fields.filter(function (f) {
        var i = A().idxOf(f.label);                       // ← 必须按名称取编号
        return i != null && String((c.vals || {})[i] || '').trim();
      });
      if (!rows.length) { return ''; }                     // 空组不渲染
      return '<div style="margin-bottom:10px">' +
        '<div style="font-weight:600;color:var(--pri);font-size:12.5px;margin-bottom:5px">' +
        A().esc(g.name) + '</div><div class="kv">' + rows.map(function (f) {
          var i = A().idxOf(f.label);
          return '<div class="r"><div class="k">' + A().esc(f.label) + '</div>' +
            '<div class="v">' + A().esc(String((c.vals || {})[i])) + '</div></div>';
        }).join('') + '</div></div>';
    }).join('') + '</div></div>';
}).join('')
```

## 三、第 50 条：问题字段多样化的三层改法

### ① 规则配置界面 —— 验证字段改多选

```js
['政治面貌', '兵役状况', '宗教信仰', '民族', '姓名', '性别', '户籍地省市县代码']
  .map(function (v, i) {
    return '<label class="sm"><input type="checkbox" name="g-verify-cb" value="' + v + '"' +
      (i < 4 ? ' checked' : '') + '> ' + v + '</label>';
  }).join('')
```
读取处（提交、文案联动）一律**收集所有勾选**，不再读 `.value`：

```js
var ver = [].slice.call(document.querySelectorAll('input[name="g-verify-cb"]:checked'))
  .map(function (e) { return e.value; }).join('、') || '—';
```

### ② 规则引擎 —— 按主关联字段关联权威源后逐字段比对

```js
var RS = (window.DATA && window.DATA.ruleSource) || {};
var VF = (RS.verify_field_list && RS.verify_field_list.length)
  ? RS.verify_field_list : [RS.verify_field || '姓名'];
var vIdx = {};
VF.forEach(function (lb) { var j = pick(lb); if (j >= 0) { vIdx[lb] = j; } });
var relField = function (c, ar) {           // 返回首个不一致的验证字段
  for (var q = 0; q < VF.length; q++) {
    var j = vIdx[VF[q]]; if (j == null) { continue; }
    var bv = c[j] == null ? '' : String(c[j]);
    var av = ar[j] == null ? '' : String(ar[j]);
    if (bv !== av) { return { field: VF[q], v: bv, a: av }; }
  }
  return null;
};
// 分支：主关联字段命中且存在不一致字段时才算问题；未命中则放行给后续分支
else if (iId >= 0 && idv && authById[idv] && relField(c, authById[idv])) { … }
```

⚠️ 权威源索引要**按主关联字段（身份证件号码）建 `authById[行]`**，不要再按「姓名→身份证号」——
后者是反的，只能做"这个姓名对应的号是否一致"，无法逐字段取值比对。

### ③ 数据层 —— 真实冲突，且分布到多个字段

18 条「保留原值」分布 `政治面貌 5 / 兵役状况 5 / 宗教信仰 4 / 民族 4`，
做法是**在冻结数据集上做外科式修正**（不重跑生成器，见 SKILL.md 九之十三 ③）：

```python
PLAN = [('政治面貌', 5), ('兵役状况', 5), ('宗教信仰', 4), ('民族', 4)]
FIELD_KEY = {'政治面貌': 'zzmm', '兵役状况': 'byzk', '宗教信仰': 'zjxy', '民族': 'mz'}
for p in KEEP:                      # KEEP = 18 条 type == '保留原值'
    r, a = BY[p['_rid']], AB[p['_rid']]
    cur = r[col]; wrong = next(v for v in ALT[f] if v != cur)
    a[col] = wrong                  # 权威源登记滞后
    p.update(field=f, orig=cur, authority=wrong,
             rule='一数一源·主关联字段=身份证件号码，验证字段=' + f,
             action='保留原值（' + REASON[f] + '，不作转换，记入问题清单待业务确认）')
assert len(KEEP) == 18 and sum(cnt.values()) == 66, '五项数字被破坏'
```

同时更新 `rule_source.verify_field`（字符串）与 `verify_field_list`（数组）——**两处都要有**，
界面读字符串、引擎读数组。

结果：问题清单 8 种字段（身份证件号码/出生日期/性别/政治面貌/兵役状况/宗教信仰/民族/自然人唯一标识），
五项数字未变（66 = 过滤12 / 转换28 / 保留原值18 / 去重8）。

## 四、本轮真 bug①：弹窗没有滚动 → 按钮点不到

把「验证字段」块改成 `span2` 后弹窗变高，**基线 `.modal{position:fixed;top:50%;left:50%;transform:…}` 没有
`max-height` / `overflow-y`** → 底部按钮被挤出视口，**真人点不到、Playwright 也点不到**。

- 症状（Playwright）：`Page.click: Timeout 30000ms exceeded`，日志里反复
  `element is visible, enabled and stable / scrolling into view if needed / done scrolling /`
  **`element is outside of the viewport`**。
- 根因定位法：**读错误日志里"重试原因"那一行**，不要只看超时结论。
- 修法：`.modal { max-height:88vh; overflow-y:auto; }`（抽屉侧本就是 `flex` + `.db{overflow-y:auto}`，不受影响）。

**预防：任何让表单变高（加字段、改 `span2`、加多选）的改动，都要回头确认弹窗容器可滚动。**

## 五、本轮真 bug②：`e.onchange = fn` 把事件对象当参数传进去

```js
function syncSource(keepClass) { if (!keepClass) { 带出所属分类 } }
e.onchange = syncSource;                    // ❌ keepClass = Event 对象 → 恒真 → 带出静默失效
e.onchange = function () { syncSource(false); };   // ✅
```

症状：**手工/自动化 select 都能改，值却不带出**，且**没有任何报错**。
凡带可选参数的函数被直接赋给事件属性，都会中这一条。

配套：**载入时（`init`）以 `syncSource(true)` 调用**，只收敛可选范围、不改写已存数据；
带出改为**"值真的变了才触发"**（用 `data-sys` 记住上一次的值比对）：

```js
var last = sel.getAttribute('data-sys') || '';
if (!keepClass && sel.value !== last) { var cls = SECLASS[sel.value]; if (c && cls) { c.value = cls; } }
sel.setAttribute('data-sys', sel.value);
```

## 六、测试纪律：脚本失败必须返回非零

本轮自查发现**我自己写的专项脚本失败时也 `exit 0`** —— 回归循环把所有套件都打成 ✅，
**红的被当绿的**。这类"测试自己骗自己"比 bug 更危险。

```python
OK, BAD = [], []
def chk(n, cond, msg): (OK if cond else BAD).append(...); print(...)
...
sys.exit(1 if BAD else 0)      # 每个自写脚本结尾都要有
```

配套：回归脚本按 exit code 判定，并把最后一行的 `通过 N 项 · 失败 M 项` 一并打出，避免只看退出码漏掉"失败但退出 0"。

## 七、验证脚本的两个落点问题

1. **别用不存在的容器 id 当选择器**：产物里没有 `#screen-s7c` 这类容器（屏幕无该 id），
   `pg.inner_text('#screen-s7c .actbar')` 直接超时。改用**不依赖容器的类选择器**
   （`.actbar` 全量取再过滤）。
2. **依赖特定流程状态的断言，要插在流程走到那一步的位置**：
   `#btn-edit-struct` 只在**技术审核抽屉打开时**存在，所以在 e2e 里要插在"点了技术审核"之后，
   而不是走到 s4 之后的任意位置。插进去后要**复原抽屉状态**（脚本后续步骤依赖它），否则下一行点击就超时。

## 八、本轮验证结果（可作为脚本清单基线）

11 套：专项 V1.7 **19/19**、专项 V1.6 **14/14**、数据级 **6/6**、可交互 38、专项 44、真机渲染 33、
四项要求 38、端到端 56、几何 17、操作栏、调试开关 18 —— 全绿。

V1.7 专项覆盖：值域 10 项 / 5 个部门口径在值域内 / 交付样例取值合规 / 载入不改写已存数据 /
选民政厅后系统收敛无残留 / 三类系统分类带出（省直·国直·国直）/ 选「暂无系统」时分类隐藏（原 11 条联动不回归）。

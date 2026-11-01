# 角色切换显式化 + 变化对照卡（可拷实现）

> 对应 SKILL.md 九之十五。2026-10-11，反馈表第 54/55 条，一次实现通过（专项 18/18 + 12 套回归全绿）。
> 项目参考实现：`/opt/data/designs/drs-demo/proto/src/app.js`、`screens/s4.js`。

## 一、角色模型：名称必须互不相同

```js
// 角色 = 真实业务岗位（不是「管理员」四种写法）；duty 用于切换面板里解释职责
var ROLES = {
  editor:  { name: '张**', org: '四川省公安厅',     role: '数据编目员',
             duty: '目录要素填报、数据项维护、数据目录导入' },
  audit1:  { name: '李**', org: '四川省大数据中心', role: '目录审核员',
             duty: '数据目录审核与发布' },
  biz:     { name: '王**', org: '四川省大数据中心', role: '归集业务审核员',
             duty: '创建归集任务工单、归集工单业务审核' },
  collect: { name: '赵**', org: '四川省大数据中心', role: '归集平台管理员',
             duty: '归集工单技术审核、归集确认、自动建表与归集执行' },
  govern:  { name: '刘**', org: '四川省大数据中心', role: '数据治理工程师',
             duty: '治理规则配置、治理任务执行与成效评估' }
};
var ROLE_ORDER = ['editor', 'audit1', 'biz', 'collect', 'govern'];

function roleFor(sc) {                    // 屏幕 → 该环节的办理角色
  if (sc === 's1' || sc === 's1b' || sc === 's5b') return 'editor';
  if (sc === 's2') return 'audit1';
  if (sc === 's3' || sc === 's3b') return 'biz';
  if (sc === 's4' || sc === 's4b' || sc === 's4c' || sc === 's4d' || sc === 's5') return 'collect';
  return 'govern';
}

// ★ 手动切换后不再跟随屏幕；null = 跟随流程
function roleCurrent() {
  return (S.roleManual && ROLES[S.roleManual]) ? S.roleManual : roleFor(S.screen);
}
```

状态位：`var S = { roleManual: null, ... }`（其他状态不动）。

## 二、顶栏徽标 + 角色条 + 切换面板

顶栏 `.who` 里的角色改成可点徽标：

```js
'<span class="roledrop" id="btn-role" title="切换角色">' +
  '<span id="who-role">数据管理员</span><span class="cd">▾</span></span>'
```

每次 `render()` 后统一更新顶栏并接线（注意 `roleCurrent()` 而不是 `roleFor(S.screen)`）：

```js
var _rk = roleCurrent();
var r = ROLES[_rk] || ROLES.editor;
if (wu) wu.textContent = r.name;
if (wr) wr.textContent = r.role;
if (wo) wo.textContent = r.org;
var _br = document.getElementById('btn-role');
if (_br) { _br.classList.toggle('manual', !!S.roleManual);   // 手动态要高亮
           _br.onclick = openRoleSwitch; }
// 角色条上的两个按钮（存在才绑）
var _bf = document.getElementById('btn-role-fix');
if (_bf) { _bf.onclick = function () { setRole(roleFor(S.screen)); }; }
var _bfl = document.getElementById('btn-role-follow');
if (_bfl) { _bfl.onclick = function () { setRole(null); }; }
```

角色条插在 `.mainscroll` 内、面包屑之后（不占额外高度，不动 `.wrap` 的 calc）：

```js
function roleBar() {
  var need = roleFor(S.screen);
  if (roleCurrent() === need) { return ''; }        // 角色一致就不显示，不干扰正常流程
  var n = ROLES[need], cur = ROLES[roleCurrent()];
  return '<div class="rolebar"><span class="ic">◷</span>' +
    '<span>本环节由「<b>' + esc(n.role) + '</b>（' + esc(n.name) + ' · ' + esc(n.org) + '）」办理；' +
    '当前角色为「' + esc(cur.role) + '」。</span>' +
    '<span class="btn sm pri" id="btn-role-fix">切换为' + esc(n.role) + '</span>' +
    '<span class="btn sm" id="btn-role-follow">恢复跟随流程</span></div>';
}
// render() 里： '<div class="crumb">…</div>' + roleBar() +
```

切换动作（**先 render 再 toast**，顺序反了 toast 会被重绘冲掉）：

```js
function setRole(k) {
  S.roleManual = k;
  var r = ROLES[roleCurrent()];
  render();
  if (k) { toast('已切换为「' + r.role + ' · ' + r.name + '」', 'ok'); }
  else { toast('已恢复跟随流程', 'ok'); }
}
```

切换面板（`openModal` + 点击整条卡片切换；底部给【跟随办理流程】）：

```js
function openRoleSwitch() {
  var cur = roleCurrent();
  openModal('切换角色',
    '<div class="notice"><span class="ic">i</span><div>系统按角色区分办理权限。' +
    '切换后按所选角色办理，也可恢复为随办理环节自动切换。</div></div>' +
    '<div class="rolelist">' + ROLE_ORDER.map(function (k) {
      var r = ROLES[k];
      return '<div class="rl' + (k === cur ? ' on' : '') + '" data-role="' + k + '">' +
        '<div class="rl-l"><div class="rl-r">' + esc(r.role) + '</div>' +
        '<div class="rl-d">' + esc(r.duty) + '</div></div>' +
        '<div class="rl-r2"><span>' + esc(r.org) + '</span><b>' + esc(r.name) + '</b>' +
        (k === cur ? '<span class="tag ok">当前</span>' : '') + '</div></div>';
    }).join('') + '</div>',
    '<span class="btn" data-close="1">取消</span>' +
    '<span class="btn pri" id="role-follow">跟随办理流程</span>');
  document.querySelectorAll('.rolelist .rl').forEach(function (el) {
    el.onclick = function () { closeModal(); setRole(el.getAttribute('data-role')); };
  });
  var f = document.getElementById('role-follow');
  if (f) { f.onclick = function () { closeModal(); setRole(null); }; }
}
```

CSS 要点（徽标必须**看得出是控件**，本轮视觉终检就是抓这个）：

```css
.topbar .roledrop{display:inline-flex;align-items:center;gap:4px;padding:3px 9px;
  margin:0 3px;background:rgba(255,255,255,.16);      /* ← 没有底色就会像纯文字 */
  border:1px solid rgba(255,255,255,.72);border-radius:3px;cursor:pointer;font-weight:600}
.topbar .roledrop.manual{background:#ffb400;border-color:#ffb400;color:#2b1d00}  /* 手动态显眼 */
.rolebar{display:flex;align-items:center;gap:10px;margin:8px 0 2px;padding:8px 12px;
  background:#fff7e6;border:1px solid #f0c987;border-left:3px solid #b26a00;border-radius:3px;font-size:12.5px}
.rolebar .btn{margin-left:auto}                         /* 按钮靠右，别摞在一起 */
```

## 三、归集前后对照卡

```js
function flowCard() {
  var c = A().S.collect, st = window.DATA.stats || {};
  var total = A().num(st.total || 1000);      // ★ 数据驱动，不要写死
  var done = !!c.taskRun;
  var ods = 'ods_' + c.table, dwd = 'dwd_' + c.table;
  return '<div class="flowcard' + (done ? ' done' : '') + '">' +
    '<div class="fc-s"><div class="fc-t">前置数据库（ODS）</div>' +
      '<div class="fc-n mono">' + A().esc(ods) + '</div>' +
      '<div class="fc-d"><b>1</b> 张表 · <b>' + total + '</b> 行</div>' +
      '<div class="fc-tag">既有库表，数据已先行落地</div></div>' +
    '<div class="fc-a"><div class="fc-line"></div>' +
      '<div class="fc-lb">归集任务<br><b>' + (done ? '已执行' : '待执行') + '</b></div>' +
      '<div class="fc-line"></div></div>' +
    '<div class="fc-s' + (done ? ' on' : '') + '">' +
      '<div class="fc-t">归集数据库（DWD）</div>' +
      '<div class="fc-n mono">' + A().esc(dwd) + '</div>' +
      '<div class="fc-d">' + (done ? '<b>1</b> 张表 · <b>' + total + '</b> 行'
                                   : '<b>0</b> 张表 · <b>0</b> 行') + '</div>' +
      '<div class="fc-tag' + (done ? ' ok' : '') + '">' + (done
        ? '本次新建 <b>+1</b> 张表 · 归集 <b>' + total + '</b> 行'
        : '归集后新增 1 张表并写入数据') + '</div></div></div>';
}
```

接入位置：`renderSrc()` 里 `html` 拼好之后 `html += flowCard();`，三个分支（未审核 / 归集前 / 归集后）就都带上了。

配套 KPI 口径（既有实体不随 `taskRun` 归零）：

```js
var stTotal = (window.DATA.stats || {}).total || 1000;
var _rows = isOds ? A().num(stTotal) : (A().S.collect.taskRun ? A().num(stTotal) : 0);
var _sub  = isOds ? '既有数据已落地' : (A().S.collect.taskRun ? '本次归集写入' : '待执行归集任务');
```

## 四、专项验证（本机实测 18/18 通过）

用真 Chrome 驱动；关键断言：

```python
# 角色名互不相同（本轮病根的直接判据）
rn = [go(sc) or who_role() for sc in ['s1','s2','s3','s4','s6']]
chk(len(set(rn)) == 5, f'5 个环节角色名称互不相同：{rn}')

# 手动切换 → 顶栏更新 + 徽标手动态 + 角色条出现
click('#btn-role'); click('.rolelist .rl:has-text("数据治理工程师")')
chk('刘**' in who and manual_class_on('#btn-role'), '手动切换生效且徽标标记手动态')
chk('#btn-role-fix' exists, '角色条给一键切换')
click('#btn-role-fix')            # 回本环节角色 → 角色条应消失

# 手动角色不随屏幕跟随，【跟随办理流程】后恢复
click('#role-follow'); go('s2')   # → 角色应自动变为目录审核员

# 对照卡：前 / 后 两个状态（直接置状态，不跑全流程）
set_collect(tables={前置仓:…, 归集仓:…}, taskRun=False); go('s4d')
chk('待执行' in card and re.search(r'0\s*张表', card), '归集前：0 张表 / 待执行')
set_collect(taskRun=True); go('s4d')
chk('已执行' in card and '+1' in card, '归集后：+1 张表 + 归集行数')

# ★ 数据驱动证明（防写死回归）：改 stats 看页面是否跟着变
evaluate('window.DATA.stats.total = 888'); go('s4d')
chk('888' in card and '1000' not in card, '行数由真实口径驱动')
```

断言坑（本轮 3 项假失败全是这个原因）：

| 坑 | 现象 | 正确写法 |
|---|---|---|
| 千分位 | 页面是 `1,000`，断言 `'1000' in txt` 失败 | 用 `'1,000' in txt` |
| 分支不同标签 | 归集前「归集库表总数」/ 归集后「归集数据库表总数」 | 按 `'表总数'` 过滤，不拄完整标签 |
| 结构化抽取 | 用 `document.querySelectorAll` 抽 .kpi 再 `innerText` 比字符串更稳 | 拼接用 `innerText.replace(/\s+/g,' ')` 再比 |

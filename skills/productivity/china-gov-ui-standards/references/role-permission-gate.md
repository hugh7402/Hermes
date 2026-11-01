# 角色权限门：实现与验证配方

来源：2026-10-11 第 56/57 条 + V2.1 自查轮（四川一体化数据资源管理系统原型 V2.0/V2.1）。
上游章节：`china-gov-ui-standards` 九之十七（本节给可拷代码）、九之十五 ①（被本节推翻的过渡形态）。

## 1. 角色数据形状

```js
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

// 屏幕 → 所需办理角色
function roleFor(sc) {
  if (sc === 's1' || sc === 's1b' || sc === 's5b') return 'editor';
  if (sc === 's2') return 'audit1';
  if (sc === 's3' || sc === 's3b') return 'biz';
  if (sc === 's4' || sc === 's4b' || sc === 's4c' || sc === 's4d' || sc === 's5') return 'collect';
  return 'govern';
}
```

**角色名必须互不相同**（第一版 6 个角色里 4 个都叫「数据管理员」，用户直接说「看不出角色转换」）。

## 2. 状态与判定

```js
// 状态对象里
role: null,          // 当前办理角色（显式；不随屏幕自动切换）

function roleCurrent() {            // 注意：不回落 roleFor(screen)
  return (S.role && ROLES[S.role]) ? S.role : 'editor';
}
function roleAllowed() { return roleCurrent() === roleFor(S.screen); }
```

渲染时：`'<div class="main"' + (roleAllowed() ? '' : ' data-gated="1"') + '>'`，
并在 `bindShell()` 之前同步 body 标记：

```js
if (roleAllowed()) { document.body.removeAttribute('data-gated'); }
else { document.body.setAttribute('data-gated', '1'); }
```

## 3. 权限条 + 切换面板

```js
function roleBar() {
  if (roleAllowed()) { return ''; }
  var need = roleFor(S.screen), n = ROLES[need], cur = ROLES[roleCurrent()];
  return '<div class="rolebar"><span class="ic">✕</span>' +
    '<span>本环节须由「<b>' + esc(n.role) + '</b>（' + esc(n.name) + ' · ' + esc(n.org) +
    '）」办理；当前角色「' + esc(cur.role) + '」无该权限，无法继续操作。' +
    '请在右上角切换为「' + esc(n.role) + '」后继续。</span>' +
    '<span class="btn sm pri" id="btn-role-fix">切换为' + esc(n.role) + '</span></div>';
}

function openRoleSwitch() {
  var cur = roleCurrent(), need = roleFor(S.screen);
  var order = ROLE_ORDER.slice();
  if (order.indexOf(need) > 0) { order.splice(order.indexOf(need), 1); order.unshift(need); }
  openModal('切换角色',
    '<div class="notice"><span class="ic">i</span><div>系统按角色区分办理权限，' +
    '各办理环节须由对应角色操作。请切换为当前环节所需角色后继续。</div></div>' +
    '<div class="rolelist">' +
    order.map(function (k) {
      var r = ROLES[k];
      return '<div class="rl' + (k === cur ? ' on' : '') + '" data-role="' + k + '">' +
        '<div class="rl-l"><div class="rl-r">' + esc(r.role) +
          (k === need ? '<span class="tag need">本环节所需</span>' : '') + '</div>' +
        '<div class="rl-d">' + esc(r.duty) + '</div></div>' +
        '<div class="rl-r2"><span>' + esc(r.org) + '</span><b>' + esc(r.name) + '</b>' +
        (k === cur ? '<span class="tag ok">当前</span>' : '') + '</div></div>';
    }).join('') + '</div>',
    '<span class="btn" data-close="1">取消</span>');   // 不要「跟随办理流程」按钮
  document.getElementById('modal').classList.add('rolepanel');   // 供 CSS 豁免
  document.querySelectorAll('.rolelist .rl').forEach(function (el) {
    el.onclick = function () { closeModal(); setRole(el.getAttribute('data-role')); };
  });
}
```

## 4. 幂等切换 + 轻量切换

```js
function setRole(k) {                       // 未变化则不重绘，否则冲掉已打开的浮层
  if (!ROLES[k] || S.role === k) { return; }
  S.role = k;
  render();
  toast('已切换为「' + ROLES[k].role + ' · ' + ROLES[k].name + '」', 'ok');
}

function setRoleSoft(k) {                   // 只更新外壳与门，不重绘内容
  if (!ROLES[k] || S.role === k) { return; }
  S.role = k;
  var r = ROLES[k];
  var wu = document.getElementById('who-user'), wr = document.getElementById('who-role'),
      wo = document.getElementById('who-org');
  if (wu) { wu.textContent = r.name; }
  if (wr) { wr.textContent = r.role.split('（')[0]; }
  if (wo) { wo.textContent = r.org; }
  var m = document.querySelector('.main');
  if (m) { roleAllowed() ? m.removeAttribute('data-gated') : m.setAttribute('data-gated', '1'); }
  roleAllowed() ? document.body.removeAttribute('data-gated')
                : document.body.setAttribute('data-gated', '1');
  var br = document.getElementById('btn-role');
  if (br) { br.classList.toggle('deny', !roleAllowed()); }
  var bar = document.querySelector('.rolebar');
  if (bar && roleAllowed()) { bar.parentNode.removeChild(bar); }
}
```

导出：`window.APP.setRole / setRoleSoft / roleFor / roleCurrent`（自动化验证要用）。

## 5. 点击拦截（不要用 pointer-events:none）

```js
var GATED_SEL = '.mainfoot .btn, .screen .actbar .btn, #modal-foot .btn, #drawer-foot .btn';

document.addEventListener('click', function (e) {      // 捕获阶段，只注册一次（模块作用域）
  if (roleAllowed()) { return; }
  var el = e.target && e.target.closest ? e.target.closest(GATED_SEL) : null;
  if (!el || el.id === 'btn-role-fix') { return; }
  e.preventDefault(); e.stopPropagation();
  toast('当前角色无本环节办理权限，请在右上角切换为「' + ROLES[roleFor(S.screen)].role + '」', 'warn');
}, true);
```

## 6. CSS

```css
/* 只挡办理动作：查看类链接保持可用 */
.main[data-gated="1"] .mainfoot .btn,
.main[data-gated="1"] .screen .actbar .btn,
.main[data-gated="1"] #modal-foot .btn,
.main[data-gated="1"] #drawer-foot .btn{opacity:.5;cursor:not-allowed}
.main[data-gated="1"] .mainfoot .btn.pri{background:#a9b7c6;border-color:#a9b7c6}
.main[data-gated="1"] .rolebar .btn{opacity:1;cursor:pointer}      /* 提示条自身豁免 */

/* 浮层在 .main 之外，必须再挂 body 作用域 */
body[data-gated="1"] #drawer-foot .btn,
body[data-gated="1"] #modal-foot .btn{opacity:.5;cursor:not-allowed}
body[data-gated="1"] #modal.rolepanel #modal-foot .btn{opacity:1;cursor:pointer}  /* 切换面板豁免 */

.rolebar{background:#fdecec;border-color:#f2bcbc;border-left:3px solid #c62828}
.rolelist .rl-r .tag.need{margin-left:6px;background:#fff4e5;color:#b26a00;font-weight:400}
.topbar .usertools .roledrop{display:inline-flex;align-items:center;gap:4px;padding:3px 9px;
  margin:0 3px;background:rgba(255,255,255,.16);border:1px solid rgba(255,255,255,.72);
  border-radius:3px;cursor:pointer;font-weight:600}          /* 必须看得出是可点控件 */
.topbar .usertools .roledrop.deny{background:#c62828;border-color:#ffd6d6;color:#fff}
```

## 7. 自动化验证清单（10 项）

1. 无权限场景建立：`has('.main[data-gated="1"]')`
2. 办理按钮不可用态：`opacity < 0.7 && cursor === 'not-allowed'`
3. 点办理动作 → toast 含「无本环节办理权限」
4. **动作未生效**：点击后业务状态未推进（如目录仍「待审核」）
5. 面板第一个角色 = 本环节所需角色
6. 该角色带 `.tag.need`「本环节所需」
7. 抽屉打开后切走角色 → `#drawer-foot .btn.pri` opacity < 0.7
8. 抽屉内点击 → 同样给提示
9. 跨环节导航当前角色**保持不变**（`set` 后长度为 1）
10. 切回正确角色 → `data-gated` 消失、opacity 回到 1

## 8. 测试适配（详见 SKILL.md 九之十七 ⑤）

```python
def _go(pg, sc):
    pg.evaluate('window.APP.go("%s"); window.APP.setRole(window.APP.roleFor("%s"));' % (sc, sc))
    pg.wait_for_timeout(180)

def _clk(pg, *a, **kw):
    pg.evaluate("""(() => {
      if (!document.querySelector('.main[data-gated=\"1\"]')) { return; }
      const el = document.querySelector('.screen.on');
      const sc = el ? el.id.replace('screen-', '') : 's1';
      window.APP.setRoleSoft(window.APP.roleFor(sc));
    })()""")
    return pg.click(*a, **kw)          # ← 千万别也被替换成 _clk，否则无限递归
```

失败信号对照：
- `TimeoutError: Page.click` ＋ `... intercepts pointer events` → 目标被门挡住（或角色没切成功）
- `RecursionError` → 包装函数自递归
- 切屏后角色没变 → 用了 `_go` 但该跳转是**应用内跳转**，不走 `go()`

/* ==========================================================================
   屏6 · 数据治理规则配置
   两步向导：一数一标准（≥3 项字段规则）→【下一步】→ 一数一源（关联权威源比对）
   提交后进入审批（s6b），审批通过自动创建治理任务
   ========================================================================== */
window.SCREENS = window.SCREENS || {};
(function () {
  'use strict';
  var A = function () { return window.APP; };
  function G() { return A().S.govern; }

  var RULE_LIB = {
    '自然人唯一标识': [
      { k: '唯一性校验（不得重复）', d: '在同一数据目录内该字段不得出现重复值' },
      { k: '非空校验', d: '该字段不允许为空' },
      { k: '长度校验', d: '长度不超过 255 个字符' }
    ],
    '身份证件号码': [
      { k: 'GB 11643-1999 公民身份号码校验', d: '18 位，末位校验码须与加权算法一致' },
      { k: '非空校验', d: '该字段不允许为空' },
      { k: '字符集校验', d: '仅允许 0-9 与 X' }
    ],
    '出生日期': [
      { k: '日期格式校验 YYYY-MM-DD', d: '格式须为 YYYY-MM-DD' },
      { k: '日期范围校验', d: '不得晚于当前日期，不得早于 1900-01-01' },
      { k: '非空校验', d: '该字段不允许为空' }
    ],
    '性别': [
      { k: '值域校验 {男,女,未知}', d: '取值须属于指定值域集合' },
      { k: '非空校验', d: '该字段不允许为空' }
    ],
    '姓名': [{ k: '非空校验', d: '该字段不允许为空' }, { k: '长度校验', d: '不超过 200 个字符' }],
    '民族': [{ k: '非空校验', d: '该字段不允许为空' }],
    '国籍': [{ k: '非空校验', d: '该字段不允许为空' }]
  };
  var GOV_FIELDS = ['自然人唯一标识', '身份证件号码', '出生日期', '姓名', '性别', '民族', '国籍'];
  // 预置 3 项（满足「不少于 3 项」要求）
  var DEF_RULES = [
    { f: '自然人唯一标识', m: '一数一标准', r: '唯一性校验（不得重复）', n: 8, on: true },
    { f: '身份证件号码', m: '一数一标准', r: 'GB 11643-1999 公民身份号码校验', n: 12, on: true },
    { f: '出生日期', m: '一数一标准', r: '日期格式校验 YYYY-MM-DD', n: 28, on: true },
    { f: '姓名', m: '一数一标准', r: '非空校验 + 长度与字符校验（2-30 位，汉字/字母）', n: 5, on: true },
    { f: '性别', m: '一数一标准', r: '值域校验（男/女/未知）', n: 3, on: true },
    { f: '民族', m: '一数一标准', r: '值域校验（GB/T 3304 中国各民族名称代码）', n: 2, on: true },
    { f: '户籍地省市县代码', m: '一数一标准', r: '行政区划代码校验（GB/T 2260 六位码）', n: 6, on: true },
    { f: '联系电话', m: '一数一标准', r: '格式校验（手机号 11 位 / 固话含区号）', n: 4, on: true }
  ];

  var wizardOpen = false, step = 1;

  /* ── 列表页 ── */
  function renderList() {
    var g = G();
    var st = g.ruleStatus;
    return '' +
      '<div class="pagetitle"><h1>数据治理规则配置</h1>' +
        '<span class="sub">为待治理数据配置一数一标准与一数一源治理规则</span>' +
        '<div class="right">' + A().tag('数据归集管理系统', 'info', '◷') + '</div></div>' +

      '<div class="kpis c4">' +
        '<div class="kpi' + (g.taskStatus ? ' k-ok' : ' k-warn') + '"><div class="k-l">规则配置状态</div>' +
          '<div class="k-v" style="font-size:20px">' + A().esc(st) + '</div>' +
          '<div class="k-s">' + (g.taskStatus ? '已启用并创建治理任务' : '待完成配置') + '</div></div>' +
        '<div class="kpi"><div class="k-l">待治理数据量</div><div class="k-v">' +
          A().num(window.DATA.stats.cleaned) + '<span class="k-u">行</span></div>' +
          '<div class="k-s">归集仓 → 清洗仓</div></div>' +
        '<div class="kpi"><div class="k-l">已配置规则数</div><div class="k-v">' +
          (g.rules.length || 0) + '<span class="k-u">项</span></div><div class="k-s">要求不少于 3 项</div></div>' +
        '<div class="kpi"><div class="k-l">待整改问题数据</div><div class="k-v k-danger">' +
          (g.taskRun ? A().num(window.DATA.stats.problem) : '—') + '</div>' +
          '<div class="k-s">' + (g.taskRun ? '治理完成后统计' : '待治理') + '</div></div>' +
      '</div>' +

      '<div class="filters">' +
        '<div class="f"><label>数据目录名称</label><input class="inp" value="' + A().esc(A().S.catalog.name) + '" readonly></div>' +
        '<div class="f"><label>数据源单位</label><input class="inp" value="四川省公安厅" readonly></div>' +
        '<div class="f"><label>归集方式</label><input class="inp" value="离线归集" readonly></div>' +
        '<span class="btn sm pri">查询</span><span class="btn sm">重置</span>' +
        '<span class="toggle" id="ftoggle">展开 ▾</span>' +
        '<div class="more f"><label>规则配置状态</label><input class="inp" value="' + A().esc(st) + '" readonly></div>' +
        '<div class="more f"><label>目录状态</label><input class="inp" value="正常" readonly></div>' +
      '</div>' +

      '<div class="tblwrap"><table class="data" id="tbl-rule">' +
        '<thead><tr><th>数据目录名称</th><th>数据源单位</th><th>归集表英文名称</th>' +
        '<th>目录状态</th><th>归集方式</th><th>规则配置状态</th><th>配置人</th>' +
        '<th style="width:150px">操作</th></tr></thead><tbody>' +
        '<tr><td>' + A().esc(A().S.catalog.name) + '</td><td>四川省公安厅</td>' +
        '<td class="mono">' + A().esc(A().S.collect.table) + '</td>' +
        '<td>' + A().statusTag('正常') + '</td><td>离线归集</td>' +
        '<td>' + A().statusTag(st === '已启用' ? '已启用' : st === '审核中' ? '审核中' : '待配置') + '</td>' +
        '<td>刘**</td>' +
        '<td><div class="ops">' +
          (g.taskStatus ? '<a data-view="1">查看</a>' : '<a id="btn-config">配置</a>') +
        '</div></td></tr>' +
        '</tbody></table></div>' +
      '<div class="pager"><span class="cnt">共 1 条</span><span class="pg on">1</span></div>' +

      '<div class="actbar"><span class="tip">点击【配置】进入规则配置详情页，' +
        '先配置 <b>一数一标准</b>（不少于 3 项），再点【下一步】配置 <b>一数一源</b>关联比对</span>' +
        '<span class="btn pri" id="btn-config2">配置</span></div>';
  }

  /* ── 向导页 ── */
  function renderWizard() {
    var g = G();
    var steps = '<div class="steps" style="display:flex;gap:0;align-items:center;margin-bottom:14px">' +
      [{ n: 1, t: '一数一标准', d: '字段级校验规则（不少于 3 项）' },
       { n: 2, t: '一数一源', d: '关联权威数据源比对' }].map(function (s, i) {
        var on = step === s.n, done = step > s.n;
        return (i ? '<span class="arw" style="flex:0 0 34px;height:1px;background:var(--bd);margin:0 10px"></span>' : '') +
          '<div style="display:flex;align-items:center;gap:9px">' +
          '<i style="width:24px;height:24px;border-radius:50%;display:flex;align-items:center;' +
          'justify-content:center;font-style:normal;font-size:12px;' +
          (on ? 'background:var(--pri);color:#fff' : done ? 'background:var(--ok);color:#fff' : 'background:#fff;border:1.5px solid var(--bd);color:var(--t3)') +
          '">' + (done ? '✓' : s.n) + '</i>' +
          '<div><div style="font-size:13.5px;font-weight:' + (on ? 600 : 400) + ';color:' +
          (on ? 'var(--pri)' : done ? 'var(--ok)' : 'var(--t3)') + '">' + s.t + '</div>' +
          '<div class="mut sm">' + s.d + '</div></div></div>';
      }).join('') + '</div>';

    var html = '<div class="pagetitle"><h1>数据治理规则配置 · ' + A().esc(A().S.catalog.name) + '</h1>' +
      '<span class="sub">两步向导：配置一数一标准规则 → 配置一数一源规则 → 提交审批</span>' +
      '<div class="right"><span class="btn sm" id="btn-back">返回列表</span></div></div>' + steps;

    if (step === 1) {
      html += '<div class="notice"><span class="ic">i</span><div>' +
        '为每个字段选择 <b>一数一标准</b> 模式并关联治理规则，' +
        '须<b>配置不少于 3 项一数一标准校验规则</b>。</div></div>' +
        '<div class="panel"><div class="ph"><h3>一数一标准规则</h3>' +
        '<span class="meta">规则库 ' + DEF_RULES.length + ' 项 · 已启用 <b>' +
        DEF_RULES.filter(function (r) { return r.on; }).length + '</b> 项（不少于 3 项）</span>' +
        '</div><div class="pb">' +
        '<div class="tblwrap"><table class="data" id="tbl-std">' +
        '<thead><tr><th class="c" style="width:44px">序号</th><th style="width:160px">数据字段</th>' +
        '<th style="width:110px">治理模式</th><th>关联治理规则</th>' +
        '<th class="c" style="width:92px">使用状态</th><th class="c" style="width:96px">命中问题</th>' +
        '<th style="width:110px">操作</th></tr></thead><tbody>' +
        DEF_RULES.map(function (r, i) {
          return '<tr' + (r.on ? '' : ' style="opacity:.55"') + '>' +
            '<td class="c">' + (i + 1) + '</td><td><b>' + A().esc(r.f) + '</b></td>' +
            '<td>' + A().tag(r.m, 'info', '◷') + '</td><td>' + A().esc(r.r) + '</td>' +
            '<td class="c"><span class="sw' + (r.on ? ' on' : ' off') + '" data-rule-sw="' + i +
              '"><i></i>' + (r.on ? '使用' : '不使用') + '</span></td>' +
            '<td class="c"><b style="color:' + (r.on ? 'var(--warn)' : 'var(--t3)') + '">' +
              (r.on ? r.n + ' 条' : '—') + '</b></td>' +
            '<td><div class="ops"><a data-edit-rule="' + i + '">编辑</a><span class="sep">|</span>' +
              '<a class="mut" data-del-rule="' + i + '">删除</a></div></td></tr>';
        }).join('') +
        '</tbody></table></div>' +
        '<div class="row" style="margin-top:10px">' +
        '<span class="btn" id="btn-add-rule">＋ 新增规则</span>' +
        '<span class="btn" id="btn-add-rule-lib">从规则库选择</span>' +
        '<span class="mut sm">规则库内置身份证件号码 GB 11643 校验、出生日期格式校验、唯一性校验等 8 条标准规则</span>' +
        '</div></div></div>';
    } else {
      html += '<div class="panel"><div class="ph"><h3>一数一源规则</h3>' +
        '<span class="meta">将待治理数据关联到权威数据源进行比对</span></div><div class="pb">' +
        '<div class="fgrid c2">' +
        '<div class="fi"><label><span class="req">*</span>是否需进行关联校验</label>' +
          '<div class="ctl"><select id="g-relate"><option>是</option><option>否</option></select></div></div>' +
        '<div class="fi"><label><span class="req">*</span>关联权威数据源</label>' +
          '<div class="ctl"><select id="g-auth">' +
          '<option selected>四川省自然人基础信息权威库（公安人口库）</option>' +
          '<option>四川省法人基础信息权威库</option></select></div>' +
          '<span class="tl">表名 authority_natural_person　已提前内置到系统</span></div>' +
        '<div class="fi"><label><span class="req">*</span>设置主关联字段</label>' +
          '<div class="ctl"><select id="g-main">' +
          ['身份证件号码', '自然人唯一标识'].map(function (v) {
            return '<option' + (v === '身份证件号码' ? ' selected' : '') + '>' + v + '</option>'; }).join('') +
          '</select></div><span class="tl">用于将待治理数据与权威源逐行关联</span></div>' +
        '<div class="fi span2"><label><span class="req">*</span>设置验证字段</label>' +
          '<div class="ctl" style="flex-wrap:wrap;gap:10px">' +
          ['政治面貌', '兵役状况', '宗教信仰', '民族', '姓名', '性别', '户籍地省市县代码']
            .map(function (v, i) {
              return '<label class="sm"><input type="checkbox" name="g-verify-cb" value="' + v +
                '"' + (i < 4 ? ' checked' : '') + '> ' + v + '</label>';
            }).join('') +
          '</div><span class="tl">可多选；逐行关联权威源后比对这些字段，任一项不一致即判定为问题数据' +
          '</span></div>' +
        '<div class="fi span2"><label><span class="req">*</span>异常数据处理策略</label>' +
          '<div class="ctl" style="gap:16px">' +
          '<label class="sm"><input type="radio" name="g-strat" value="保留原值" checked> 保留原值</label>' +
          '<label class="sm"><input type="radio" name="g-strat" value="转换为权威数据"> 转换为权威数据</label>' +
          '</div><span class="tl" id="strat-tip"></span></div>' +
        '</div></div></div>' +
        '<div class="notice"><span class="ic">i</span><div>' +
        '比对逻辑：以 <b id="rel-main-txt">身份证件号码</b> 为主关联字段，将归集仓数据逐行关联到权威数据源，' +
        '再比对 <b id="rel-verify-txt">政治面貌、兵役状况、宗教信仰、民族</b>；' +
        '不一致的记录按所选异常策略处置。' +
        '<span id="hit-tip"></span></div></div>';
    }

    html += '<div class="actbar"><span class="tip">' +
      (step === 1 ? '第 1 步：一数一标准（不少于 3 项）' : '第 2 步：一数一源关联比对配置') + '</span>' +
      (step === 1 ? '<span class="btn pri" id="btn-next">下一步 →</span>'
                  : '<span class="btn" id="btn-prev">← 上一步</span>' +
                    '<span class="btn pri" id="btn-submit-rule">提交</span>') +
      '</div>';
    return html;
  }

  function render() { return wizardOpen ? renderWizard() : renderList(); }

  /* 提交 → 进入审核中，并创建治理任务 */
  function submitRule() {
    var g = G();
    var strat = (document.querySelector('input[name=g-strat]:checked') || {}).value || '保留原值';
    var auth = (document.getElementById('g-auth') || {}).value || '';
    var main = (document.getElementById('g-main') || {}).value || '';
    var ver = [].slice.call(document.querySelectorAll('input[name="g-verify-cb"]:checked'))
      .map(function (e) { return e.value; }).join('、') || '—';
    g.rules = DEF_RULES.slice();
    g.source = { relate: true, authority: auth, table: 'authority_natural_person',
                 main: main, verify: ver, strategy: strat };
    g.ruleStatus = '审核中';
    g.ruleSubmitAt = A().now();
    A().S.done.gconf = true;
    A().render();            // 先重绘再开弹窗
    A().openModal('治理规则配置已提交',
      '<div class="notice ok"><span class="ic">✓</span><div>已配置 <b>3 项一数一标准规则</b>与 <b>1 项一数一源规则</b>，' +
      '已提交审核。</div></div>' +
      '<div class="kv" style="margin-top:12px">' +
      '<div class="r"><div class="k">一数一标准</div><div class="v">3 项（唯一性校验 / GB 11643 校验 / 出生日期格式校验）</div></div>' +
      '<div class="r"><div class="k">关联校验</div><div class="v">是</div></div>' +
      '<div class="r"><div class="k">权威数据源</div><div class="v">' + A().esc(auth) + '</div></div>' +
      '<div class="r"><div class="k">主关联字段</div><div class="v">' + A().esc(main) + '</div></div>' +
      '<div class="r"><div class="k">验证字段</div><div class="v">' + A().esc(ver) + '</div></div>' +
      '<div class="r"><div class="k">异常处理策略</div><div class="v">' + A().esc(strat) + '</div></div>' +
      '</div>' +
      '<div class="notice" style="margin-top:10px"><span class="ic">→</span><div>' +
      '在【审批管理】列表对治理规则进行审核，<b>通过后系统自动创建治理任务</b>。</div></div>',
      '<span class="btn" data-close-m="1">取消</span>' +
      '<span class="btn pri" id="to-appr">前往规则审批管理</span>');
    var t = document.getElementById('to-appr');
    if (t) t.onclick = function () { A().closeModal(); A().go('s6b'); };
  }

  /* 规则审批 */
  function renderApprove() {
    var g = G();
    var done = !!g.taskStatus;
    return '' +
      '<div class="pagetitle"><h1>数据治理规则配置审批管理</h1>' +
        '<span class="sub">规则审核通过后自动创建治理任务</span>' +
        '<div class="right">' + A().tag('数据归集管理系统', 'info', '◷') + '</div></div>' +
      (done
        ? '<div class="notice ok"><span class="ic">✓</span><div>规则审核已通过，系统已<b>自动创建治理任务</b>。</div></div>'
        : g.ruleStatus === '审核中'
        ? '<div class="notice warn"><span class="ic">◷</span><div>规则配置待审核，请点击【审核】完成审批。</div></div>'
        : '<div class="notice warn"><span class="ic">!</span><div>尚无待审核的规则配置，请先在【数据治理规则配置】提交。</div></div>') +
      '<div class="tblwrap"><table class="data" id="tbl-rappr">' +
        '<thead><tr><th>数据目录名称</th><th>归集表英文名称</th><th>规则项数</th>' +
        '<th>异常处理策略</th><th>提交时间</th><th>状态</th>' +
        '<th style="width:110px">操作</th></tr></thead><tbody>' +
        (g.ruleStatus === '待配置'
          ? '<tr><td colspan="7" class="t-center mut" style="padding:24px">暂无待审核数据</td></tr>'
          : '<tr><td>' + A().esc(A().S.catalog.name) + '</td>' +
            '<td class="mono">' + A().esc(A().S.collect.table) + '</td>' +
            '<td class="c">' + (g.rules.length || 3) + ' 项</td>' +
            '<td>' + A().esc(g.source ? g.source.strategy : '保留原值') + '</td>' +
            '<td class="td">' + A().esc(g.ruleSubmitAt || '—') + '</td>' +
            '<td>' + A().statusTag(done ? '已启用' : '审核中') + '</td>' +
            '<td><div class="ops">' +
              (done ? '<a data-view="1">查看</a>' : '<a id="btn-rappr">审核</a>') +
            '</div></td></tr>') +
        '</tbody></table></div>' +
      '<div class="pager"><span class="cnt">共 ' + (g.ruleStatus === '待配置' ? 0 : 1) + ' 条</span>' +
        '<span class="pg on">1</span></div>' +
      '<div class="actbar"><span class="tip">' +
        (done ? '治理任务已创建，前往【治理任务管理】执行'
              : g.ruleStatus === '审核中' ? '点击【审核】通过，系统将自动创建治理任务'
              : '请先提交规则配置') + '</span>' +
        (g.ruleStatus === '审核中' ? '<span class="btn pri" id="btn-rappr2">审核</span>' : '') +
        (done ? '<span class="btn pri" id="go-task">前往治理任务管理 →</span>' : '') +
      '</div>';
  }

  function doApprove() {
    var g = G();
    A().openDrawer('治理规则审核 · ' + A().S.catalog.name,
      '<div class="panel"><div class="ph"><h3>一数一标准规则（3 项）</h3></div><div class="pb">' +
      '<table class="data"><thead><tr><th class="c">序号</th><th>数据字段</th><th>治理模式</th>' +
      '<th>关联治理规则</th></tr></thead><tbody>' +
      (g.rules.length ? g.rules : DEF_RULES).map(function (r, i) {
        return '<tr><td class="c">' + (i + 1) + '</td><td><b>' + A().esc(r.f) + '</b></td>' +
          '<td>' + A().tag(r.m || '一数一标准', 'info', '◷') + '</td>' +
          '<td>' + A().esc(r.r) + '</td></tr>';
      }).join('') + '</tbody></table></div></div>' +
      '<div class="panel"><div class="ph"><h3>一数一源规则</h3></div><div class="pb"><div class="kv">' +
      '<div class="r"><div class="k">关联校验</div><div class="v">是</div></div>' +
      '<div class="r"><div class="k">权威数据源</div><div class="v">' +
        A().esc(g.source ? g.source.authority : '四川省自然人基础信息权威库（公安人口库）') + '</div></div>' +
      '<div class="r"><div class="k">主关联字段</div><div class="v">' +
        A().esc(g.source ? g.source.main : '身份证件号码') + '</div></div>' +
      '<div class="r"><div class="k">验证字段</div><div class="v">' +
        A().esc(g.source ? g.source.verify : '姓名') + '</div></div>' +
      '<div class="r"><div class="k">异常处理策略</div><div class="v">' +
        A().esc(g.source ? g.source.strategy : '保留原值') + '</div></div>' +
      '</div></div></div>' +
      '<div class="fi" id="fi-rop" style="margin-top:12px"><label><span class="req">*</span>审核意见</label>' +
      '<div class="ctl"><textarea id="rop">规则配置完整，一数一标准 3 项、一数一源关联字段设置合理，同意通过。</textarea></div>' +
      '<span class="msg">不少于 10 字</span></div>',
      '<span class="btn" data-close="1">取消</span><span class="btn pri" id="rop-ok">审核通过</span>', true);
    var b = document.getElementById('rop-ok');
    if (b) b.onclick = function () {
      var op = ((document.getElementById('rop') || {}).value || '').trim();
      if (op.length < 10) { A().toast('审核意见不少于 10 字', 'err'); return; }
      var g2 = G();
      g2.ruleStatus = '已启用';
      g2.ruleApprovedAt = A().now();
      // 规则审核通过后系统「创建治理任务」，任务此时为「待上线」；
      // 需到治理任务管理点【配置】填调度详情、提交后才变【已上线】并执行
      g2.taskStatus = '待上线';
      g2.taskCreatedAt = g2.ruleApprovedAt;
      A().closeDrawer(); A().render();
      A().openModal('治理任务已创建',
        '<div class="notice ok"><span class="ic">✓</span><div>规则审核通过，系统已<b>自动创建治理任务</b>。</div></div>' +
        '<div class="kv" style="margin-top:12px">' +
        '<div class="r"><div class="k">治理任务名称</div><div class="v mono">' +
          A().esc(A().S.catalog.name) + '_治理任务</div></div>' +
        '<div class="r"><div class="k">任务创建时间</div><div class="v td">' + A().esc(g2.taskCreatedAt) + '</div></div>' +
        '<div class="r"><div class="k">规则审核通过时间</div><div class="v td">' + A().esc(g2.ruleApprovedAt) + '</div></div>' +
        '</div>',
        '<span class="btn" data-close-m="1">取消</span>' +
        '<span class="btn pri" id="to-gtask">前往治理任务管理</span>');
      var t = document.getElementById('to-gtask');
      if (t) t.onclick = function () { A().closeModal(); A().go('s7'); };
    };
  }

  /* 从内置规则库新增一条一数一标准规则 */
  function openAddRule() {
    var FIELDS = ['自然人唯一标识', '身份证件号码', '出生日期', '姓名', '性别', '民族',
                  '户籍地省市县代码', '联系电话', '现居住地址', '文化程度'];
    var LIB = [
      '唯一性校验（不得重复）',
      'GB 11643-1999 公民身份号码校验',
      '日期格式校验 YYYY-MM-DD',
      '非空校验 + 长度与字符校验',
      '值域校验（对照标准代码表）',
      '行政区划代码校验（GB/T 2260 六位码）',
      '格式校验（正则表达式）',
      '数值范围校验'
    ];
    var used = {};
    DEF_RULES.forEach(function (r) { used[r.f] = 1; });
    var free = FIELDS.filter(function (f) { return !used[f]; });
    A().openDrawer('新增一数一标准规则',
      '<div class="fgrid c2">' +
      '<div class="fi" id="fi-ar-f"><label><span class="req">*</span>数据字段</label>' +
        '<div class="ctl"><select id="ar-f">' +
        free.concat(['（自定义）']).map(function (f) {
          return '<option>' + A().esc(f) + '</option>';
        }).join('') + '</select></div></div>' +
      '<div class="fi" id="fi-ar-r"><label><span class="req">*</span>关联治理规则</label>' +
        '<div class="ctl"><select id="ar-r">' +
        LIB.map(function (r) { return '<option>' + A().esc(r) + '</option>'; }).join('') +
        '</select></div></div>' +
      '<div class="fi"><label>命中问题数（预评估）</label>' +
        '<div class="ctl"><input class="inp" id="ar-n" value="0"></div></div>' +
      '</div>' +
      '<div class="notice" style="margin-top:12px"><span class="ic">i</span><div>' +
      '新增的规则默认<b>启用</b>。一数一标准须<b>不少于 3 项</b>，启用中的规则才参与治理执行。</div></div>',
      '<span class="btn" data-close="1">取消</span>' +
      '<span class="btn pri" id="ar-ok">新增并启用</span>');
    var b = document.getElementById('ar-ok');
    if (b) b.onclick = function () {
      var f = (document.getElementById('ar-f') || {}).value || '';
      var r = (document.getElementById('ar-r') || {}).value || '';
      var n = parseInt((document.getElementById('ar-n') || {}).value, 10);
      if (!f) { A().toast('请选择数据字段', 'err'); return; }
      DEF_RULES.push({ f: f, m: '一数一标准', r: r, n: isNaN(n) ? 0 : n, on: true });
      A().closeDrawer();
      A().render();
      A().toast('规则「' + f + '」已新增并启用，当前启用 ' +
        DEF_RULES.filter(function (x) { return x.on; }).length + ' 项', 'ok');
    };
  }

  var init = function () {
    var b1 = document.getElementById('btn-config'), b2 = document.getElementById('btn-config2');
    function openW() { wizardOpen = true; step = 1; A().render(); }
    if (b1) b1.onclick = openW;
    if (b2) b2.onclick = openW;
    var bk = document.getElementById('btn-back');
    if (bk) bk.onclick = function () { wizardOpen = false; A().render(); };
    var nx = document.getElementById('btn-next');
    if (nx) nx.onclick = function () { step = 2; A().render(); };
    var pv = document.getElementById('btn-prev');
    if (pv) pv.onclick = function () { step = 1; A().render(); };
    var sb = document.getElementById('btn-submit-rule');
    if (sb) sb.onclick = submitRule;
    // 使用 / 不使用 开关（真实生效，影响启用数与命中问题数）
    document.querySelectorAll('[data-rule-sw]').forEach(function (sw) {
      sw.onclick = function () {
        var i = parseInt(sw.getAttribute('data-rule-sw'), 10);
        DEF_RULES[i].on = !DEF_RULES[i].on;
        var on = DEF_RULES.filter(function (r) { return r.on; }).length;
        if (on < 3) {
          DEF_RULES[i].on = true;
          A().toast('一数一标准须不少于 3 项，无法再停用', 'err');
          return;
        }
        A().render();
        A().toast('规则「' + DEF_RULES[i].f + '」已' + (DEF_RULES[i].on ? '启用' : '停用') +
          '，当前启用 ' + on + ' 项', 'ok');
      };
    });
    document.querySelectorAll('[data-del-rule]').forEach(function (a) {
      a.onclick = function () {
        var i = parseInt(a.getAttribute('data-del-rule'), 10);
        var on = DEF_RULES.filter(function (r) { return r.on; }).length;
        if (on <= 3) { A().toast('一数一标准须不少于 3 项，无法删除', 'err'); return; }
        var name = DEF_RULES[i].f;
        DEF_RULES.splice(i, 1);
        A().render();
        A().toast('规则「' + name + '」已删除', 'ok');
      };
    });
    var ar = document.getElementById('btn-add-rule');
    if (ar) ar.onclick = function () { openAddRule(); };
    var al = document.getElementById('btn-add-rule-lib');
    if (al) al.onclick = function () { openAddRule(); };
    document.querySelectorAll('[data-edit-rule]').forEach(function (a) {
      a.onclick = function () {
        var i = parseInt(a.getAttribute('data-edit-rule'), 10);
        A().openDrawer('编辑规则 · ' + A().esc(DEF_RULES[i].f),
          '<div class="fgrid c2">' +
          '<div class="fi"><label>数据字段</label><div class="ctl ro"><span>' +
            A().esc(DEF_RULES[i].f) + '</span></div></div>' +
          '<div class="fi"><label>治理模式</label><div class="ctl ro"><span>一数一标准</span></div></div>' +
          '<div class="fi"><label>关联治理规则</label><div class="ctl ro"><span>' +
            A().esc(DEF_RULES[i].r) + '</span></div></div>' +
          '<div class="fi"><label>使用状态</label><div class="ctl ro"><span>' +
            (DEF_RULES[i].on ? '使用' : '不使用') + '</span></div></div>' +
          '</div><div class="mut sm" style="margin-top:10px">规则内容来自内置规则库，' +
          '如需变更请通过「新增规则」新建一条并停用本条。</div>',
          '<span class="btn" data-close="1">关闭</span>');
      };
    });
    /* 异常处理策略提示：随所选策略变化（保留原值 / 转换为权威数据） */
    var applyStratTip = function () {
      var v = (document.querySelector('input[name=g-strat]:checked') || {}).value || '保留原值';
      var conv = v === '转换为权威数据';
      var t = document.getElementById('strat-tip');
      if (t) {
        t.textContent = '本次选择「' + v + '」；' + (conv
          ? '不一致的数据按权威数据源替换，原始值留存备查'
          : '不一致的数据保留业务系统原值，记入待整改') + '　两种策略系统均须具备';
      }
      var h = document.getElementById('hit-tip');
      if (h) {
        h.textContent = '本数据集将命中 ' + window.DATA.stats.by_type['保留原值'] +
          ' 条与权威数据源不一致的记录，' + (conv
            ? '将替换为权威数据源的值，原始值留存备查。'
            : '按策略保留原值处置，记入问题清单待整改。');
      }
    };
    [].slice.call(document.querySelectorAll('input[name=g-strat]'))
      .forEach(function (r) { r.onchange = applyStratTip; });
    applyStratTip();

    var relTxt = function () {
      var t1 = document.getElementById('rel-main-txt'), t2 = document.getElementById('rel-verify-txt');
      if (t1) { t1.textContent = (document.getElementById('g-main') || {}).value || ''; }
      if (t2) {
        var vs = [].slice.call(document.querySelectorAll('input[name="g-verify-cb"]:checked'))
          .map(function (e) { return e.value; });
        t2.textContent = vs.join('、') || '—';
      }
    };
    var gm = document.getElementById('g-main');
    if (gm) { gm.onchange = relTxt; }
    [].slice.call(document.querySelectorAll('input[name="g-verify-cb"]'))
      .forEach(function (e) { e.onchange = relTxt; });
    relTxt();
    var ft = document.getElementById('ftoggle');
    if (ft) ft.onclick = function () {
      var f = ft.parentNode; f.classList.toggle('open');
      ft.textContent = f.classList.contains('open') ? '收起 ▴' : '展开 ▾';
    };
    document.querySelectorAll('[data-view]').forEach(function (a) {
      a.onclick = function () { A().toast('规则详情'); };
    });
  };

  var initApprove = function () {
    ['btn-rappr', 'btn-rappr2'].forEach(function (id) {
      var e = document.getElementById(id); if (e) e.onclick = doApprove;
    });
    var g = document.getElementById('go-task');
    if (g) g.onclick = function () { A().go('s7'); };
  };

  window.SCREENS.s6 = { render: render, init: init, submitRule: submitRule, setWizard: function (s) { wizardOpen = true; step = s; } };
  window.SCREENS.s6b = { render: renderApprove, init: initApprove, doApprove: doApprove };
})();

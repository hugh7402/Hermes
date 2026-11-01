/* ==========================================================================
   屏4 · 归集系统：技术审核 → 归集确认 → 自动建表
   覆盖 s4 待我处理 / s4b 已办结 / s4c 前置数据库 / s4d 归集数据库
   核心校验点：三处创建时间（前置仓表/归集仓表/离线任务）与工单审批通过时间一致
   ========================================================================== */
window.SCREENS = window.SCREENS || {};
(function () {
  'use strict';
  var A = function () { return window.APP; };

  var SYS = '数据归集管理系统';
  function C() { return A().S.collect; }

  /* 审批通过后自动建表 ——
     真实语义：前置仓（ODS）为**既有库表**，数据已先行落地（早于本次工单）；
               归集仓（DWD）原本没有该表，本次审批通过后才新建，并写入本次归集数据。 */
  function buildTables() {
    var c = C();
    if (c.tables) return;
    var t = c.techAuditAt || A().now();
    c.tables = {
      前置仓: { name: 'ods_' + c.table, label: '前置仓表', created: c.stagedAt || A().fsDays(3),
                fields: 15, rows: A().S.collect.rows || 1000, existed: true },
      归集仓: { name: 'dwd_' + c.table, label: '归集仓表', created: t, fields: 15, rows: 0, existed: false },
      任务: { name: c.orderNo + '_' + c.table + '_offline', label: '离线归集任务',
              created: t, type: '离线归集', status: '待执行' }
    };
    c.task = c.tables.任务;
    A().S.done.table = true;
    A().S.done.tech = true;
  }

  var STEP = function () { return C().techAudit ? (C().confirmAudit ? 3 : 2) : 1; };

  function render() {
    var c = C(), step = STEP();
    if (c.status === '未发起') {
      return '<div class="pagetitle"><h1>归集工单审核</h1>' +
        '<span class="sub">归集工单审核与自动建表</span></div>' +
        '<div class="notice warn"><span class="ic">!</span><div>' +
        '暂无归集工单。请先在【数据目录管理系统】完成目录发布并发起归集，工单审核通过后会自动流转到本系统。</div></div>' +
        '<div class="actbar"><span class="tip">前置步骤需先在【数据目录管理系统】完成</span>' +
        '<span class="btn pri" id="back-cat">返回编目系统</span></div>';
    }
    var t1 = c.techAudit ? A().statusTag('已通过') : A().statusTag('待处理');
    var t2 = c.confirmAudit ? A().statusTag('已通过') : (c.techAudit ? A().statusTag('待处理') : A().tag('未开始', 'mute'));

    var rows = '<tr>' +
      '<td class="mono">' + A().esc(c.orderNo) + '</td>' +
      '<td>' + A().esc(A().S.catalog.name) + '</td>' +
      '<td class="mono">' + A().esc(c.table) + '</td>' +
      '<td>四川省公安厅</td><td>离线归集</td>' +
      '<td>' + t1 + '</td><td>' + t2 + '</td>' +
      '<td><div class="ops">' +
        (step === 1 ? '<a id="btn-tech">技术审核</a>' : '') +
        (step === 2 ? '<a id="btn-confirm">归集确认</a>' : '') +
        (step === 3 ? '<a data-view="1">查看</a>' : '') +
        (step !== 3 ? '<span class="sep">|</span><a class="mut" data-view="1">查看</a>' : '') +
      '</div></td></tr>';

    var html = '' +
      '<div class="pagetitle"><h1>归集工单审核 · 待我处理</h1>' +
        '<span class="sub">审核归集工单与表结构信息，依据工单自动建表并创建归集任务</span>' +
        '<div class="right">' +
          (step === 3 ? '<span class="btn sm" id="go-src">查看已建表结构</span>' : '') +
          '<span class="mut sm">系统：</span>' + A().tag(SYS, 'info', '◷') +
        '</div></div>' +

      '<div class="kpis c4">' +
        '<div class="kpi k-warn"><div class="k-l">待我处理</div><div class="k-v">' +
          (step === 3 ? 0 : 1) + '<span class="k-u">件</span></div></div>' +
        '<div class="kpi k-ok"><div class="k-l">已办结</div><div class="k-v">' +
          (step - 1) + '<span class="k-u">件</span></div></div>' +
        '<div class="kpi"><div class="k-l">当前环节</div><div class="k-v" style="font-size:19px">' +
          (step === 1 ? '技术审核' : step === 2 ? '归集确认' : '已办结') + '</div>' +
          '<div class="k-s">' + (step === 3 ? '已自动建表并创建归集任务' : '两步审核通过后自动建表') + '</div></div>' +
        '<div class="kpi"><div class="k-l">表英文名</div><div class="k-v" style="font-size:16px">' +
          A().esc(c.table) + '</div></div>' +
      '</div>' +

      (step === 1
        ? '<div class="notice"><span class="ic">i</span><div>在【归集工单审核】-【待我处理】找到该工单，点击 <b>技术审核</b>，' +
          '审核归集工单与表结构信息。</div></div>'
        : step === 2
        ? '<div class="notice"><span class="ic">i</span><div>技术审核已通过。请<b>再次选择该工单，点击【归集确认】进行智能审核</b>。</div></div>'
        : '<div class="notice ok"><span class="ic">✓</span><div>两步审核均已通过，系统已按归集工单<b>自动建表</b>并<b>自动创建归集任务</b>。</div></div>') +

      '<div class="tblwrap"><table class="data" id="tbl-collect">' +
        '<thead><tr><th>归集工单编号</th><th>数据目录名称</th><th>表英文名</th><th>数据提供单位</th>' +
        '<th>归集方式</th><th>技术审核</th><th>归集确认</th><th style="width:150px">操作</th></tr></thead>' +
        '<tbody>' + rows + '</tbody></table></div>' +
      '<div class="pager"><span class="cnt">共 1 条</span><span class="pg on">1</span></div>';

    if (step === 3) {
      var tb = c.tables;
      html +=
        '<div class="panel" style="margin-top:14px"><div class="ph"><h3>自动建表结果</h3>' +
        '<span class="meta">建表与建任务时间 = 工单审批通过时间</span></div><div class="pb">' +
        '<div class="eqbar"><span>工单审批通过时间 <b>' + A().esc(c.techAuditAt) + '</b></span>' +
        '<span class="op">=</span><span>前置仓表创建时间 <b>' + A().esc(tb.前置仓.created) + '</b></span>' +
        '<span class="op">=</span><span>归集仓表创建时间 <b>' + A().esc(tb.归集仓.created) + '</b></span>' +
        '<span class="op">=</span><span>归集任务创建时间 <b>' + A().esc(tb.任务.created) + '</b></span>' +
        '</div>' +
        '<table class="data"><thead><tr><th>类型</th><th>对象名称</th><th class="c">字段数</th>' +
        '<th>创建时间</th><th>所属工单</th></tr></thead><tbody>' +
        ['前置仓', '归集仓'].map(function (k) {
          var x = tb[k];
          return '<tr><td>' + x.label + '</td><td class="mono">' + A().esc(x.name) + '</td>' +
            '<td class="c">' + x.fields + '</td><td class="td">' + A().esc(x.created) + '</td>' +
            '<td class="mono">' + A().esc(c.orderNo) + '</td></tr>';
        }).join('') +
        '<tr><td>' + tb.任务.label + '</td><td class="mono">' + A().esc(tb.任务.name) + '</td>' +
        '<td class="c">—</td><td class="td">' + A().esc(tb.任务.created) + '</td>' +
        '<td class="mono">' + A().esc(c.orderNo) + '</td></tr>' +
        '</tbody></table></div></div>';
    }

    html += '<div class="actbar"><span class="tip">' +
      (step === 1 ? '点击【技术审核】审核工单与表结构信息'
       : step === 2 ? '点击【归集确认】执行智能审核，通过后系统自动建表'
       : '进入【数源管理】查看新建的前置仓表与归集仓表，再到【离线归集任务】执行归集') + '</span>' +
      (step === 1 ? '<span class="btn pri" id="btn-tech2">技术审核</span>' : '') +
      (step === 2 ? '<span class="btn pri" id="btn-confirm2">归集确认</span>' : '') +
      (step === 3 ? '<span class="btn pri" id="go-task">前往离线归集任务 →</span>' : '') +
      '</div>';
    return html;
  }

  /* 技术审核（含表结构信息） */
  function openTech() {
    var c = C();
    var flds = window.DATA.fields || [];
    A().openDrawer('技术审核 · ' + c.orderNo,
      '<div class="notice"><span class="ic">i</span><div>审核归集工单与<b>表结构信息</b>。' +
      '通过后系统将按该结构自动创建<b>归集仓表</b>并创建离线归集任务' +
      '（前置仓为既有库表，数据已先行落地，无需重复创建）。</div></div>' +
      '<div class="panel"><div class="ph"><h3>归集工单基本信息</h3></div><div class="pb"><div class="kv">' +
      '<div class="r"><div class="k">归集工单编号</div><div class="v mono">' + A().esc(c.orderNo) + '</div></div>' +
      '<div class="r"><div class="k">数据目录名称</div><div class="v">' + A().esc(A().S.catalog.name) + '</div></div>' +
      '<div class="r"><div class="k">表英文名称</div><div class="v mono">' + A().esc(c.table) + '</div></div>' +
      '<div class="r"><div class="k">归集方式</div><div class="v">' + A().esc(c.dock || '库表对接') + '</div></div>' +
      '<div class="r"><div class="k">数据用途</div><div class="v">' + A().esc(c.usage || '') + '</div></div>' +
      '</div></div></div>' +
      '<div class="panel"><div class="ph"><h3>表结构信息</h3><span class="meta">' + flds.length +
      ' 个字段（由目录数据项自动生成）</span></div><div class="pb">' +
      '<div class="row" style="margin-bottom:8px"><span class="btn sm" id="btn-edit-struct">' +
        '✎ 编辑表结构</span><span class="mut sm">可修改字段的数据类型、长度、主键与非空设置，' +
        '修改结果将用于自动建表</span></div>' +
      '<div class="tblwrap"><table class="data"><thead><tr><th class="c">序号</th><th>字段中文名</th>' +
      '<th>字段英文名</th><th>数据类型</th><th class="n">长度</th><th class="c">主键</th>' +
      '<th class="c">非空</th></tr></thead><tbody>' +
      flds.map(function (f, i) {
        return '<tr><td class="c">' + (i + 1) + '</td><td>' + A().esc(f.cn) + '</td>' +
          '<td class="mono">' + A().esc(f.en) + '</td><td>' + A().esc(f.type) + '</td>' +
          '<td class="n">' + A().esc(f.len || '—') + '</td>' +
          '<td class="c">' + (f.pk === '是' ? '<b style="color:var(--pri)">是</b>' : '否') + '</td>' +
          '<td class="c">' + (f.nullable === '否' ? '是' : '否') + '</td></tr>';
      }).join('') + '</tbody></table></div>' +
      '<div class="notice warn" style="margin-top:10px"><span class="ic">!</span><div>' +
      '系统校验：主键字段 <b>' + flds.filter(function (f) { return f.pk === '是'; }).map(function (f) { return f.cn; }).join('、') +
      '</b>，字段类型与长度均符合规范，可据此建表。</div></div></div></div>' +
      '<div class="panel"><div class="ph"><h3>审批信息</h3></div><div class="pb">' +
      '<div class="fi" id="fi-top"><label><span class="req">*</span>审批意见</label>' +
      '<div class="ctl"><textarea id="top" placeholder="不少于 10 字">工单信息与表结构信息核对无误，字段类型与主键设置符合规范，同意通过技术审核。</textarea></div>' +
      '<span class="msg">审批意见不少于 10 字</span></div></div></div>',
      '<span class="btn" data-close="1">取消</span>' +
      '<span class="btn dgr" id="tech-no">驳回</span>' +
      '<span class="btn pri" id="tech-ok">通过</span>', true);

    var b = document.getElementById('tech-ok');
    if (b) b.onclick = function () {
      var op = ((document.getElementById('top') || {}).value || '').trim();
      var fi = document.getElementById('fi-top');
      if (op.length < 10) { if (fi) fi.classList.add('err'); A().toast('审批意见不少于 10 字', 'err'); return; }
      var c2 = C();
      c2.techAudit = { opinion: op, at: A().now(), user: '赵**' };
      c2.techAuditAt = c2.techAudit.at;
      A().closeDrawer(); A().render();
      A().openModal('技术审核已通过',
        '<div class="notice ok"><span class="ic">✓</span><div>归集工单与表结构信息审核通过。</div></div>' +
        '<div class="notice" style="margin-top:10px"><span class="ic">→</span><div>' +
        '<b>在【待我处理】列表再次选择该工单，点击【归集确认】进行智能审核</b>。' +
        '两步全部通过后，系统才会自动建表。</div></div>',
        '<span class="btn" data-close-m="1">继续</span>');
    };
    var n = document.getElementById('tech-no');
    if (n) n.onclick = function () { A().toast('已驳回，工单退回编目系统'); };
  }

  /* 归集确认（智能审核） */
  function openConfirm() {
    var c = C();
    var chk = [
      { t: '工单信息完整性校验', r: '通过', d: '工单编号、表英文名、数据用途、归集方式齐全' },
      { t: '表英文名命名规范校验', r: '通过', d: '符合「字母开头 + 字母数字下划线」规范，长度合规' },
      { t: '表结构字段校验', r: '通过', d: '15 个字段类型与长度合规，主键唯一' },
      { t: '源端连通性预检', r: '通过', d: '四川省公安厅前置数据库连接正常，可写入' },
      { t: '重名冲突检测', r: '通过', d: '前置仓与归集仓均无同名表' }
    ];
    A().openDrawer('归集确认（智能审核） · ' + c.orderNo,
      '<div class="notice"><span class="ic">i</span><div>系统对归集工单执行<b>智能审核</b>，逐项自动校验。全部通过后自动建表并创建归集任务。</div></div>' +
      '<div class="tblwrap"><table class="data"><thead><tr><th>校验项</th><th class="c" style="width:80px">结果</th>' +
      '<th>说明</th></tr></thead><tbody>' +
      chk.map(function (x) {
        return '<tr><td>' + A().esc(x.t) + '</td><td class="c">' + A().statusTag('已通过') + '</td>' +
          '<td class="mut">' + A().esc(x.d) + '</td></tr>';
      }).join('') + '</tbody></table></div>' +
      '<div class="eqbar" style="margin-top:12px"><span>智能审核结论</span><span class="op">：</span>' +
      '<b>5 / 5 项通过</b><span class="chk">✓ 准予建表</span></div>' +
      '<div class="fi" id="fi-cfop" style="margin-top:12px"><label><span class="req">*</span>确认意见</label>' +
      '<div class="ctl"><textarea id="cfop">智能审核全部通过，同意建表并创建归集任务。</textarea></div>' +
      '<span class="msg">不少于 10 字</span></div>',
      '<span class="btn" data-close="1">取消</span><span class="btn pri" id="cf-ok">确认通过</span>', true);

    var b = document.getElementById('cf-ok');
    if (b) b.onclick = function () {
      var op = ((document.getElementById('cfop') || {}).value || '').trim();
      if (op.length < 10) { A().toast('确认意见不少于 10 字', 'err'); return; }
      var c2 = C();
      c2.confirmAudit = { opinion: op, at: A().now(), user: '赵**' };
      buildTables();
      A().closeDrawer(); A().render();
      var tb = c2.tables;
      A().openModal('自动建表完成',
        '<div class="notice ok"><span class="ic">✓</span><div>系统已根据归集工单<b>自动建表</b>，并<b>自动创建归集任务</b>。</div></div>' +
        '<div class="panel" style="margin-top:12px"><div class="ph"><h3>自动建表过程</h3>' +
        '<span class="meta">全部步骤在同一次事务内完成，耗时 1.2 秒</span></div><div class="pb"><div class="tl">' +
        ['① 读取归集工单表结构信息（' + (window.DATA.catalog.items || []).length + ' 个字段的类型、长度、主键）',
         '② 生成<b>归集仓表</b>建表语句并执行 → <span class="mono">' + A().esc(tb.归集仓.name) + '</span>',
         '③ 自动创建<b>离线归集任务</b> → <span class="mono">' + A().esc(tb.任务.name) + '</span>',
         '④ 归集工单状态置为「归集施工中」，等待执行归集'
        ].map(function (s, i) {
          // 各步骤按实际执行顺序递进（每步间隔约 0.3 秒），不是同一个时间戳
          var st = A().plusMs(tb.归集仓.created, i * 320);
          var ms = String(i * 320 % 1000);
          return '<div class="ti done"><div class="tt">' + (i + 1) + '. ' + s + '</div>' +
            '<div class="td">' + A().esc(st) + '.' + ('00' + ms).slice(-3) +
            '　<span class="mut">耗时 ' + (i === 0 ? 120 : 180 + i * 40) + ' ms</span>' +
            '</div></div>';
        }).join('') +
        '</div></div></div>' +
        '<div class="kv" style="margin-top:12px">' +
        '<div class="r"><div class="k">前置仓表</div><div class="v mono">' + A().esc(tb.前置仓.name) +
          '　<span class="mut sm">创建于 ' + A().esc(tb.前置仓.created) + '</span></div></div>' +
        '<div class="r"><div class="k">归集仓表</div><div class="v mono">' + A().esc(tb.归集仓.name) +
          '　<span class="mut sm">创建于 ' + A().esc(tb.归集仓.created) + '</span></div></div>' +
        '<div class="r"><div class="k">离线归集任务</div><div class="v mono">' + A().esc(tb.任务.name) +
          '　<span class="mut sm">创建于 ' + A().esc(tb.任务.created) + '</span></div></div>' +
        '</div>' +
'' ,
        '<span class="btn" data-close-m="1">取消</span>' +
        '<span class="btn pri" id="to-task">前往离线归集任务</span>');
      var t = document.getElementById('to-task');
      if (t) t.onclick = function () { A().closeModal(); A().go('s5'); };
    };
  }

  /* 数源管理：前置数据库 / 归集数据库（表列表） */
  /* 归集前后对照卡：表数、数据行数、本次归集多少行 —— 一眼看出「多了一张表、归集了多少数据」 */
  function flowCard() {
    var c = A().S.collect;
    var st = window.DATA.stats || {};
    var total = A().num(st.total || 1000);
    var done = !!c.taskRun;
    var ods = 'ods_' + c.table, dwd = 'dwd_' + c.table;
    return '<div class="flowcard' + (done ? ' done' : '') + '">' +
      '<div class="fc-s">' +
        '<div class="fc-t">前置数据库（ODS）</div>' +
        '<div class="fc-n mono">' + A().esc(ods) + '</div>' +
        '<div class="fc-d"><b>' + ODS_TABLES.length + '</b> 张表 · 本次工单对应表 <b>' +
          total + '</b> 行</div>' +
        '<div class="fc-tag">既有库表，数据已先行落地</div></div>' +
      '<div class="fc-a"><div class="fc-line"></div>' +
        '<div class="fc-lb">归集任务<br><b>' + (done ? '已执行' : '待执行') + '</b></div>' +
        '<div class="fc-line"></div></div>' +
      '<div class="fc-s' + (done ? ' on' : '') + '">' +
        '<div class="fc-t">归集数据库（DWD）</div>' +
        '<div class="fc-n mono">' + A().esc(dwd) + '</div>' +
        '<div class="fc-d">' + (done
          ? '<b>1</b> 张表 · <b>' + total + '</b> 行'
          : '<b>0</b> 张表 · <b>0</b> 行') + '</div>' +
        '<div class="fc-tag' + (done ? ' ok' : '') + '">' + (done
          ? '本次新建 <b>+1</b> 张表 · 归集 <b>' + total + '</b> 行'
          : '归集后新增 1 张表并写入数据') + '</div></div>' +
      '</div>';
  }

  /* 前置库（ODS）既有表：真实前置库承载多张来源表，本次工单只对应其中一张 */
  var ODS_TABLES = [
    { n: 'ods_natural_person_base',      cn: '自然人基本登记信息', f: 15, rows: 1000, wo: true },
    { n: 'ods_person_certificate',       cn: '身份证件信息',       f: 9,  rows: 1015 },
    { n: 'ods_person_household',         cn: '户籍信息',           f: 11, rows: 942 },
    { n: 'ods_person_contact',           cn: '联系方式信息',       f: 7,  rows: 903 },
    { n: 'ods_person_edu',               cn: '学历信息',           f: 8,  rows: 735 },
    { n: 'ods_natural_person_ext',       cn: '自然人扩展信息',     f: 12, rows: 860 }
  ];

  function renderSrc(which) {
    var c = C();
    var label = which === 'c' ? '前置数据库' : '归集数据库';
    var isOds = which === 'c';
    var html = '<div class="pagetitle"><h1>' + label + '</h1>' +
      '<span class="sub">查看本库表结构与建表时间</span>' +
      (isOds
        ? '<div class="right"><span class="mut sm">前置仓为既有库表，数据先行落地</span></div>'
        : '<div class="right"><span class="mut sm">归集仓表由本次归集自动新建</span></div>') + '</div>';

    html += flowCard();     // 归集前后对照（前置库 → 归集库）

    /* 归集数据库：归集前为空，归集后才新增该表（体现「从前置库到归集库的变化」） */
    if (!isOds && !c.taskRun) {
      return html +
        '<div class="notice warn"><span class="ic">!</span><div>归集数据库中<b>暂无</b>该表。' +
        '前置数据库已有表 <span class="mono">' + A().esc('ods_' + c.table) + '</span>，' +
        '需执行归集任务后，归集库才会新增对应表并写入数据。</div></div>' +
        '<div class="kpis c4">' +
          '<div class="kpi"><div class="k-l">归集库表总数</div><div class="k-v">0<span class="k-u">张</span></div></div>' +
          '<div class="kpi"><div class="k-l">待新增</div><div class="k-v">1<span class="k-u">张</span></div>' +
            '<div class="k-s">' + A().esc('dwd_' + c.table) + '</div></div>' +
          '<div class="kpi"><div class="k-l">前置库表</div><div class="k-v">1<span class="k-u">张</span></div>' +
            '<div class="k-s">' + A().esc('ods_' + c.table) + '</div></div>' +
          '<div class="kpi"><div class="k-l">归集行数</div><div class="k-v">0<span class="k-u">行</span></div>' +
            '<div class="k-s">待执行归集任务</div></div>' +
        '</div>' +
        '<div class="tblwrap"><table class="data"><thead><tr><th>表名</th><th>表中文名</th>' +
        '<th class="c">字段数</th><th>所属数据库</th><th>创建时间</th><th>来源工单</th></tr></thead>' +
        '<tbody><tr><td colspan="6" class="t-center mut" style="padding:26px">' +
        '归集数据库中暂无表——执行归集任务后将新增 <span class="mono">' +
        A().esc('dwd_' + c.table) + '</span>（' + (window.DATA.fields || []).length + ' 个数据项）。' +
        '</td></tr></tbody></table></div>' +
        '<div class="actbar"><span class="tip">请先执行【离线归集任务】</span>' +
        '<span class="btn pri" id="back-collect">前往离线归集任务</span></div>';
    }
    if (!c.tables) {
      return html + '<div class="notice warn"><span class="ic">!</span><div>' +
        '该数据库暂无表。需先完成技术审核与归集确认。</div></div>' +
        '<div class="actbar"><span class="tip">请先完成归集工单审核</span>' +
        '<span class="btn pri" id="back-collect">前往归集工单审核</span></div>';
    }
    var t = isOds ? c.tables.前置仓 : c.tables.归集仓;
    var flds = window.DATA.fields || [];
    var stTotal = (window.DATA.stats || {}).total || 1000;
    return html +
      '<div class="kpis c4">' +
        '<div class="kpi"><div class="k-l">' + label + '表总数</div><div class="k-v">' +
          (isOds ? ODS_TABLES.length : 1) + '<span class="k-u">张</span></div>' +
          (isOds ? '<div class="k-s">本库既有库表</div>' : '') + '</div>' +
        '<div class="kpi' + (isOds ? '' : ' k-ok') + '"><div class="k-l">' +
          (isOds ? '本次工单对应表' : '本次新建') + '</div><div class="k-v">1<span class="k-u">张</span></div>' +
          '<div class="k-s">' + A().esc(t.created) + '</div></div>' +
        '<div class="kpi"><div class="k-l">字段数</div><div class="k-v">' + flds.length + '<span class="k-u">个</span></div></div>' +
        '<div class="kpi"><div class="k-l">数据行数</div><div class="k-v">' +
          (isOds ? A().num(stTotal)
                 : (A().S.collect.taskRun ? A().num(stTotal) : 0)) + '<span class="k-u">行</span></div>' +
          '<div class="k-s">' + (isOds ? '既有数据已落地'
            : (A().S.collect.taskRun ? '本次归集写入' : '待执行归集任务')) + '</div></div>' +
      '</div>' +
      '<div class="filters"><div class="f"><label>表名</label><input class="inp mono" value="' + A().esc(t.name) + '" readonly></div>' +
      '<span class="btn sm pri">查询</span><span class="btn sm">重置</span>' +
      '<span class="mut sm" style="margin-left:auto">搜索归集工单【基本信息】中的【表英文名称】即可查到本表</span></div>' +
      '<div class="tblwrap"><table class="data"><thead><tr><th>表名</th><th>表中文名</th>' +
      '<th class="c">字段数</th><th>所属数据库</th><th>创建时间</th><th>来源工单</th>' +
      '<th style="width:90px">操作</th></tr></thead><tbody>' +
      (isOds
        ? ODS_TABLES.map(function (o) {
            return '<tr' + (o.wo ? ' class="sel"' : '') + '><td class="mono">' + A().esc(o.n) + '</td>' +
              '<td>' + A().esc(o.cn) + (o.wo ? '　<span class="tag ok">本次工单</span>' : '') + '</td>' +
              '<td class="c">' + o.f + '</td><td>' + label + '</td>' +
              '<td class="td">' + A().esc(o.wo ? t.created : A().fsDays(12)) + '</td>' +
              '<td class="mono">' + A().esc(o.wo ? c.orderNo : '—') + '</td>' +
              '<td><div class="ops">' +
              (o.wo ? '<a id="btn-struct">查看结构</a>'
                    : '<a class="mut">查看结构</a>') + '</div></td></tr>';
          }).join('')
        : '<tr class="sel"><td class="mono">' + A().esc(t.name) + '</td>' +
          '<td>' + A().esc(A().S.catalog.name) + '</td>' +
          '<td class="c">' + flds.length + '</td><td>' + label + '</td>' +
          '<td class="td"><b style="color:var(--pri)">' + A().esc(t.created) + '</b></td>' +
          '<td class="mono">' + A().esc(c.orderNo) + '</td>' +
          '<td><div class="ops"><a id="btn-struct">查看结构</a></div></td></tr>') +
      '</tbody></table></div>' +
      '<div class="pager"><span class="cnt">共 ' + (isOds ? ODS_TABLES.length : 1) +
        ' 条</span><span class="pg on">1</span></div>' +
      (isOds
        ? '<div class="eqbar" style="margin-top:12px">' +
          '<span>前置仓表创建时间 <b>' + A().esc(t.created) + '</b></span>' +
          '</div>'
        : '<div class="eqbar" style="margin-top:12px">' +
          '<span>工单审批通过时间 <b>' + A().esc(c.techAuditAt) + '</b></span><span class="op">=</span>' +
          '<span>归集仓表创建时间 <b>' + A().esc(t.created) + '</b></span>' +
          '</div>') +
      '<div class="actbar"><span class="tip">点击【查看结构】可核对系统新建表的字段定义</span>' +
      '<span class="btn pri" id="btn-struct2">查看结构</span>' +
      '<span class="btn" id="go-task2">前往离线归集任务 →</span></div>';
  }

  function openStruct() {
    var c = C(), flds = window.DATA.fields || [];
    var t = c.tables ? (c.tables.前置仓) : null;
    A().openDrawer('表结构信息 · ' + (t ? t.name : ''),
      '<div class="kv" style="margin-bottom:12px">' +
      '<div class="r"><div class="k">表名</div><div class="v mono">' + A().esc(t ? t.name : '') + '</div></div>' +
      '<div class="r"><div class="k">创建时间</div><div class="v"><b style="color:var(--pri)">' +
        A().esc(t ? t.created : '') + '</b></div></div>' +
      '<div class="r"><div class="k">来源工单</div><div class="v mono">' + A().esc(c.orderNo) + '</div></div>' +
      '<div class="r"><div class="k">字段数</div><div class="v">' + flds.length + ' 个</div></div>' +
      '</div>' +
      '<div class="tblwrap"><table class="data"><thead><tr><th class="c">序号</th><th>字段名</th>' +
      '<th>字段注释</th><th>类型</th><th class="n">长度</th><th class="c">主键</th>' +
      '<th class="c">非空</th></tr></thead><tbody>' +
      flds.map(function (f, i) {
        return '<tr><td class="c">' + (i + 1) + '</td><td class="mono">' + A().esc(f.en) + '</td>' +
          '<td>' + A().esc(f.cn) + '</td><td>' + A().esc(f.type) + '</td>' +
          '<td class="n">' + A().esc(f.len || '—') + '</td>' +
          '<td class="c">' + (f.pk === '是' ? 'Y' : '') + '</td>' +
          '<td class="c">' + (f.nullable === '否' ? 'Y' : '') + '</td></tr>';
      }).join('') + '</tbody></table></div>', '<span class="btn" data-close="1">关闭</span>', true);
  }

  function makeInit(which) {
    return function () {
      var b1 = document.getElementById('btn-tech'), b2 = document.getElementById('btn-tech2');
      if (b1) b1.onclick = openTech;
      if (b2) b2.onclick = openTech;
      var c1 = document.getElementById('btn-confirm'), c2 = document.getElementById('btn-confirm2');
      if (c1) c1.onclick = openConfirm;
      if (c2) c2.onclick = openConfirm;
      document.querySelectorAll('[data-view]').forEach(function (a) {
        if (a.classList.contains('mut')) {
          a.onclick = function () {
            var c = C();
            var kv = function (k, v) {
              return '<div class="r"><div class="k">' + k + '</div><div class="v">' + v + '</div></div>';
            };
            A().openDrawer('归集工单详情 · ' + A().esc(c.orderNo),
              '<div class="kv">' +
                kv('归集工单编号', '<span class="mono">' + A().esc(c.orderNo) + '</span>') +
                kv('数据目录名称', A().esc(A().S.catalog.name)) +
                kv('数据目录编码', '<span class="mono">' + A().esc(A().S.catalog.code) + '</span>') +
                kv('归集方式', A().esc(c.dock || '库表对接')) +
                kv('表英文名', '<span class="mono">' + A().esc(c.table) + '</span>') +
                kv('数据用途', A().esc(c.usage || '—')) +
                kv('工单状态', A().statusTag(c.status || '已通过')) +
                kv('业务审核人 / 时间', A().esc((c.auditOpinion ? '已审核' : '—')) + '　' +
                   A().esc(c.auditAt || '—')) +
                kv('技术审核', A().esc(c.techAudit ? ('已通过　' + c.techAudit.at) : '待处理')) +
                kv('归集确认', A().esc(c.confirmAudit ? ('已通过　' + c.confirmAudit.at) : '待处理')) +
              '</div>' +
              (c.auditOpinion ? '<div class="notice" style="margin-top:12px"><span class="ic">i</span><div>' +
                '业务审核意见：' + A().esc(c.auditOpinion) + '</div></div>' : ''),
              '<span class="btn" data-close="1">关闭</span>');
          };
          return;
        }
        a.onclick = function () { A().toast('工单详情'); };
      });
      ['go-src'].forEach(function (id) {
        var e = document.getElementById(id);
        if (e) e.onclick = function () { A().go('s4c'); };
      });
      ['go-task', 'go-task2'].forEach(function (id) {
        var e = document.getElementById(id);
        if (e) e.onclick = function () { A().go('s5'); };
      });
      ['btn-struct', 'btn-struct2'].forEach(function (id) {
        var e = document.getElementById(id); if (e) e.onclick = openStruct;
      });
      var bk = document.getElementById('back-cat');
      if (bk) bk.onclick = function () { A().go('s3b'); };
      var bc = document.getElementById('back-collect');
      if (bc) bc.onclick = function () { A().go('s4'); };
    // 编辑表结构：真实可改（写入 window.DATA.fields，后续建表按此结构）
    var es = document.getElementById('btn-edit-struct');
    if (es) es.onclick = function () {
      var flds = window.DATA.fields = window.DATA.fields || [];
      var TYPES = ['字符型C', '数字型N', '日期型D', '时间戳型T', '布尔型B'];
      A().openDrawer('编辑表结构信息',
        '<div class="notice"><span class="ic">i</span><div>表结构信息将用于<b>自动建表</b>，' +
        '字段中文名与英文名不可修改（与数据项保持一致），可调整<b>数据类型 / 长度 / 主键 / 非空</b>。</div></div>' +
        '<div class="tblwrap" style="margin-top:10px"><table class="data"><thead><tr>' +
        '<th class="c" style="width:44px">序号</th><th>字段中文名</th><th>字段英文名</th>' +
        '<th style="width:130px">数据类型</th><th style="width:88px">长度</th>' +
        '<th style="width:88px">是否主键</th><th style="width:88px">是否非空</th></tr></thead><tbody>' +
        flds.map(function (f, i) {
          var en = f.en || ('col_' + (i + 1));
          return '<tr><td class="c">' + (i + 1) + '</td><td><b>' + A().esc(f.cn || '') + '</b></td>' +
            '<td class="mono">' + A().esc(en) + '</td>' +
            '<td><select class="inp" id="st-type-' + i + '" style="width:100%">' +
              TYPES.map(function (t) {
                return '<option' + (t === (f.type || '字符型C') ? ' selected' : '') + '>' + t + '</option>';
              }).join('') + '</select></td>' +
            '<td><input class="inp" id="st-len-' + i + '" value="' + A().esc(f.len || '') + '"></td>' +
            '<td><select class="inp" id="st-pk-' + i + '" style="width:100%">' +
              ['是', '否'].map(function (x) {
                return '<option' + (x === (f.pk || '否') ? ' selected' : '') + '>' + x + '</option>';
              }).join('') + '</select></td>' +
            '<td><select class="inp" id="st-nn-' + i + '" style="width:100%">' +
              ['是', '否'].map(function (x) {
                return '<option' + (x === (f.nullable === '否' ? '是' : '否') ? ' selected' : '') + '>' + x +
                  '</option>';
              }).join('') + '</select></td></tr>';
        }).join('') + '</tbody></table></div>',
        '<span class="btn" data-close="1">取消</span>' +
        '<span class="btn pri" id="st-ok">保存表结构</span>', true);
      var ok = document.getElementById('st-ok');
      if (ok) ok.onclick = function () {
        var n = 0;
        flds.forEach(function (f, i) {
          var t = document.getElementById('st-type-' + i);
          var l = document.getElementById('st-len-' + i);
          var p = document.getElementById('st-pk-' + i);
          var nn = document.getElementById('st-nn-' + i);
          if (t) { f.type = t.value; }
          if (l) { f.len = String(l.value || '').trim(); }
          if (p) { f.pk = p.value; }
          if (nn) { f.nullable = nn.value === '是' ? '否' : '是'; }
          n++;
        });
        A().closeDrawer();
        A().render();
        A().toast('表结构信息已保存（' + n + ' 个字段），自动建表将按该结构执行', 'ok');
      };
    };
    };
  }

  window.SCREENS.s4 = { render: render, init: makeInit('s4'), openTech: openTech, openConfirm: openConfirm };
  window.SCREENS.s4b = { render: render, init: makeInit('s4b') };
  window.SCREENS.s4c = { render: function () { return renderSrc('c'); }, init: makeInit('s4c') };
  window.SCREENS.s4d = { render: function () { return renderSrc('d'); }, init: makeInit('s4d') };
})();

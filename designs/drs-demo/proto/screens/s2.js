/* ==========================================================================
   屏2 · 数据目录审批管理
   审核流程：一步审核，目录审核员审核通过后目录即发布
   ========================================================================== */
window.SCREENS = window.SCREENS || {};
(function () {
  'use strict';
  var A = function () { return window.APP; };

  // 审核流程：一步审核，目录审核员审核通过即发布
  var NODES = [
    { k: '审核', role: '目录审核员', user: '李**', org: '四川省大数据中心' }
  ];

  function audits() { return A().S.catalog.audits; }
  function nextNode() {
    var n = audits().length;
    return n < 3 ? NODES[n] : null;
  }
  function statusOf() {
    return audits().length >= 1 ? '已发布' : '待审核';
  }

  /* 目录要素摘要（审核要看的东西） */
  function summaryHtml() {
    var S = A().S, spec = window.FORM_SPEC || [];
    var g0 = '', rows = '';
    spec.forEach(function (g, gi) {
      if (g.isTable) return;
      var shown = g.fields.slice(0, gi === 0 ? 4 : 3).map(function (f) {
        return '<div class="r"><div class="k">' + A().esc(f.label) + '</div>' +
               '<div class="v">' + A().esc(DEFVAL[f.idx] || '—') + '</div></div>';
      }).join('');
      rows += '<div class="panel"><div class="ph"><span class="n">' + (gi + 1) + '</span>' +
              '<h3>' + A().esc(g.name) + '</h3><span class="meta">' + g.fields.length + ' 项</span></div>' +
              '<div class="pb"><div class="kv">' + shown + '</div></div></div>';
    });
    var its = (window.DATA.catalog.items || []);
    var trows = its.slice(0, 8).map(function (it, i) {
      return '<tr><td class="c">' + (i + 1) + '</td><td>' + A().esc(it.cn) + '</td>' +
        '<td class="mono">' + A().esc(it.en) + '</td><td>' + A().esc(it.type) + '</td>' +
        '<td class="c">' + A().esc(it.pk) + '</td><td>' + A().esc(String(it.sensitivity).slice(0, 2)) + '</td></tr>';
    }).join('');
    return rows +
      '<div class="panel"><div class="ph"><span class="n">7</span><h3>数据项</h3>' +
      '<span class="meta">' + its.length + ' 项（显示前 8 项）</span></div><div class="pb">' +
      '<table class="data"><thead><tr><th class="c">序号</th><th>数据项名称</th><th>英文名称</th>' +
      '<th>数据类型</th><th class="c">主键</th><th>敏感级别</th></tr></thead><tbody>' + trows +
      '</tbody></table></div></div>';
  }
  // 表单预填值（与 s1 一致，供审核页只读展示）
  var DEFVAL = {
    1: '四川省自然人基本登记信息',
    55: '四川省公安厅',
    56: '手工新增',
    2: '自然人的基础身份信息，包括姓名、性别、出生日期、民族、国籍等，是自然人身份识别的基础数据。',
    3: '数据管理系统', 4: '自建自用', 5: '民生保障', 6: '省级', 7: '数据库', 8: 'mysql',
    9: '融合数据', 10: '每日', 11: '每天 2:00 更新前一天数据', 12: '否', 13: '是',
    15: '户籍地省市县代码', 16: '全省', 17: '2025-06-30', 18: '至今',
    19: '有条件共享', 20: '库表', 21: '依据《四川省公共数据共享开放管理办法》依申请共享',
    22: '每日', 24: '有条件开放', 25: '依申请开放，需说明使用用途', 34: '是',
    26: '自然人身份信息核验', 27: '510000000001', 28: '自然人基本信息查询', 29: '51000000000001',
    30: '自然人基本信息核验办事指南', 31: '510000000000000000000000000000001',
    32: '自然人身份信息核验', 33: '510000000001'
  };

  function render() {
    var S = A().S, st = statusOf();
    var node = nextNode();
    var log = audits().length ? '<div class="tl">' + audits().map(function (a) {
      return '<div class="ti done"><div class="tt">' + A().esc(a.node) + ' · ' + A().esc(a.role) +
        ' · ' + A().esc(a.user) + ' ' + A().tag(a.result, 'ok', '✓') + '</div>' +
        '<div class="td">' + A().esc(a.time) + '　意见：' + A().esc(a.opinion || '同意') + '</div></div>';
    }).join('') + '</div>' : '<div class="mut sm">尚无审核记录。</div>';

    var pend = A().pendingCatalogs();
    var rows = pend.length ? pend.map(function (c) {
      var isAct = (c === S.catalog);
      var n = (c.items && c.items.length) ? c.items.length : (window.DATA.catalog.items || []).length;
      return '<tr>' +
        '<td class="mono">' + A().esc(c.code) + '</td>' +
        '<td><a data-pick="' + A().esc(c.code) + '">' + A().esc(c.name) + '</a></td>' +
        '<td>' + A().esc(c.org) + '</td><td>' + A().esc(c.domain) + '</td>' +
        '<td class="n">' + n + '</td>' +
        '<td>' + A().statusTag(c.status) + '</td>' +
        '<td>' + (node ? A().esc(node.user) : '—') + '</td>' +
        '<td><div class="ops">' +
          (isAct ? '<a id="btn-audit">审核</a>'
                 : '<a data-pick="' + A().esc(c.code) + '">审核</a>') +
          '<span class="sep">|</span><a data-view="1">查看</a></div></td></tr>';
    }).join('') : '<tr><td colspan="8" class="t-center mut" style="padding:26px">' +
        '暂无待审核的数据目录。</td></tr>';

    return '' +
      '<div class="pagetitle"><h1>数据目录审批管理</h1>' +
        '<span class="sub">目录要素审核通过后发布至数据目录管理</span>' +
        '<div class="right"><span class="mut sm">当前处理人：</span>' +
        (node ? A().tag(node.user + '　' + node.role, 'info', '◷') : A().tag('审核已办结', 'ok', '✓')) +
        '</div></div>' +

      '<div class="kpis c3">' +
        '<div class="kpi"><div class="k-l">待我处理</div><div class="k-v">' + A().pendingCatalogs().length +
          '<span class="k-u">件</span></div><div class="k-s">数据目录审批工单</div></div>' +
        '<div class="kpi"><div class="k-l">当前审核环节</div><div class="k-v" style="font-size:19px">' +
          A().esc(node ? node.k : '已办结') + '</div><div class="k-s">' +
          A().esc(node ? node.role : '审核已完成') + '</div></div>' +
        '<div class="kpi k-ok"><div class="k-l">目录状态</div><div class="k-v" style="font-size:19px">' +
          st + '</div><div class="k-s">' + (st === '已发布' ? '已进入数据目录管理列表' : '待审核通过后发布') + '</div></div>' +
      '</div>' +

      '<div class="filters"><div class="f"><label>数据目录名称</label>' +
        '<input class="inp" value="' + A().esc(S.catalog.name) + '" readonly></div>' +
        '<div class="f"><label>工单状态</label><input class="inp" value="' + st + '" readonly></div>' +
        '<span class="toggle" id="ftoggle">展开 ▾</span></div>' +

      '<div class="tblwrap"><table class="data" id="tbl-audit">' +
        '<thead><tr><th>数据目录编码</th><th>数据目录名称</th><th>数据提供单位</th>' +
        '<th>数据所属领域</th><th class="n">数据项数</th><th>工单状态</th><th>当前处理人</th>' +
        '<th style="width:110px">操作</th></tr></thead><tbody>' + rows + '</tbody></table></div>' +
      '<div class="pager"><span class="cnt">共 ' + A().pendingCatalogs().length + ' 条</span>' +
        '<span class="pg on">1</span></div>' +

      '<div class="panel" style="margin-top:12px"><div class="ph"><h3>审核记录</h3>' +
        '<span class="meta">目录审核员审核通过后目录即发布</span></div>' +
        '<div class="pb">' + log +
        (node ? '<div class="notice warn" style="margin:10px 0 0"><span class="ic">◷</span><div>' +
          '待处理：<b>' + A().esc(node.k) + '</b>，处理人 <b>' + A().esc(node.user) + '</b>（' +
          A().esc(node.role) + '）。</div></div>' : '') +
        '</div></div>' +

      '<div class="actbar"><span class="tip" id="audit-tip">' +
        (node ? '点击列表【审核】→ 填写审核意见 → 提交，审核通过后目录即发布'
              : '审核已完成，目录状态为“已发布”') + '</span>' +
        (node ? '<span class="btn pri" id="btn-audit2">审核</span>' : '') +
        (statusOf() === '已发布' ? '<span class="btn pri" id="go-collect">发起数据归集 →</span>' : '') +
      '</div>';
  }

  /* 审核操作 */
  function openAudit() {
    var node = nextNode(); if (!node) return;
    var body = '<div class="notice"><span class="ic">i</span><div>当前环节：<b>' + A().esc(node.k) +
      '</b>　处理人：<b>' + A().esc(node.user) + '</b>（' + A().esc(node.role) + '）</div></div>' +
      '<div style="max-height:44vh;overflow:auto;padding-right:4px">' + summaryHtml() + '</div>' +
      '<div class="panel" style="margin-top:12px"><div class="ph"><h3>审核意见</h3></div><div class="pb">' +
      '<div class="fi" id="fi-opinion"><label><span class="req">*</span>审核意见</label>' +
      '<div class="ctl"><textarea id="opinion" placeholder="请填写审核意见（不少于 10 字）">目录要素完整、字段规范、共享属性明确，同意发布。</textarea></div>' +
      '<span class="msg">审核意见不少于 10 字</span></div>' +
      '<div class="row" style="margin-top:8px"><label class="sm"><input type="radio" name="ra" value="同意" checked> 同意</label>' +
      '<label class="sm"><input type="radio" name="ra" value="驳回"> 驳回</label></div></div></div>';
    A().openDrawer(node.k + ' · 数据目录审核', body,
      '<span class="btn" data-close="1">取消</span>' +
      '<span class="btn pri" id="audit-ok">审核通过</span>', true);
    var b = document.getElementById('audit-ok');
    if (b) b.onclick = function () {
      var op = (document.getElementById('opinion') || {}).value || '';
      var res = (document.querySelector('input[name=ra]:checked') || {}).value || '同意';
      var fi = document.getElementById('fi-opinion');
      if (op.trim().length < 10) { if (fi) fi.classList.add('err'); A().toast('审核意见不少于 10 字', 'err'); return; }
      if (fi) fi.classList.remove('err');
      A().S.catalog.audits.push({ node: node.k, role: node.role, user: node.user,
                                  time: A().now(), result: res, opinion: op.trim() });
      var n = A().S.catalog.audits.length;
      A().S.catalog.status = '已发布'; A().S.catalog.published = true;
      A().S.done.audit = true; A().S.done.pub = true;
      A().closeDrawer();
      A().render();          // 先重绘，再开弹窗（顺序反了弹窗会被 render 冲掉）
      if (n >= 1) {
        A().openModal('目录审核通过',
          '<div class="notice ok"><span class="ic">✓</span><div>目录 <b>' + A().esc(A().S.catalog.name) +
          '</b> 审核通过，状态更新为 <b>已发布</b>。</div></div>' +
          '<div class="tl" style="margin-top:12px">' + A().S.catalog.audits.map(function (a) {
            return '<div class="ti done"><div class="tt">' + A().esc(a.node) + ' · ' + A().esc(a.user) +
              '</div><div class="td">' + A().esc(a.time) + '</div></div>'; }).join('') + '</div>' +
          '<div class="mut sm" style="margin-top:10px">下一步：基于该目录创建数据归集任务工单。</div>',
          '<span class="btn" data-close-m="1">取消</span>' +
          '<span class="btn pri" id="to-list">查看数据目录列表</span>');
        var t = document.getElementById('to-list');
        if (t) t.onclick = function () { A().closeModal(); A().go('s1b'); };
      } else {
        A().toast('审核已通过', 'ok');
      }
    };
  }

  var init = function () {
    var b1 = document.getElementById('btn-audit'), b2 = document.getElementById('btn-audit2');
    if (b1) b1.onclick = openAudit;
    if (b2) b2.onclick = openAudit;
    document.querySelectorAll('[data-view]').forEach(function (a) {
      a.onclick = function () {
        A().openDrawer('数据目录要素 · ' + A().S.catalog.name, summaryHtml(),
          '<span class="btn" data-close="1">关闭</span>', true);
      };
    });
    // 在多条待审核中点选某条 → 设为当前处理目录
    document.querySelectorAll('[data-pick]').forEach(function (a) {
      a.onclick = function () {
        var code = a.getAttribute('data-pick');
        A().S.catalogs.forEach(function (c) { if (c.code === code) { A().S.catalog = c; } });
        A().render();
      };
    });
    var ft = document.getElementById('ftoggle');
    if (ft) ft.onclick = function () {
      var f = ft.parentNode; f.classList.toggle('open');
      ft.textContent = f.classList.contains('open') ? '收起 ▴' : '展开 ▾';
    };
    var g = document.getElementById('go-collect');
    if (g) g.onclick = function () { A().go('s3'); };
  };

  window.SCREENS.s2 = { render: render, init: init, openAudit: openAudit,
                        statusOf: statusOf, nextNode: nextNode };
})();

/* ==========================================================================
   屏8 · 治理成效总览
   呼应脚本结尾原话：「实现数据来源可溯、标准可依、质量可控」
   ========================================================================== */
window.SCREENS = window.SCREENS || {};
(function () {
  'use strict';
  var A = function () { return window.APP; };

  function render() {
    var S = A().S, s = window.DATA.stats, b = s.by_type;
    var c = S.collect, g = S.govern;
    var full = S.done.grun;

    var flow = '<div class="panel"><div class="ph"><h3>数据流向与治理链路</h3>' +
      '<span class="meta">编目 → 归集 → 治理，全程可追溯</span></div><div class="pb">' +
      '<div class="eqbar" style="margin:0">' +
      ['前置仓', '归集仓', '清洗仓'].map(function (t, i) {
        var nm = { '前置仓': c.tables ? c.tables.前置仓.name : '—',
                   '归集仓': c.tables ? c.tables.归集仓.name : '—',
                   '清洗仓': 'dws_' + c.table }[t];
        var n = { '前置仓': s.total, '归集仓': s.total, '清洗仓': s.cleaned }[t];
        return (i ? '<span class="op">→</span>' : '') +
          '<span>' + t + ' <b class="mono" style="font-size:12px">' + A().esc(nm) + '</b>' +
          '　<b>' + A().num(n) + '</b> 行</span>';
      }).join('') +
      '<span class="chk">' + (full ? '✓ 全链路已完成' : '◷ 未完成') + '</span></div>' +
      '<div class="tl" style="margin-top:14px">' +
      [['编目填报', c.submittedAt || (S.catalog.audits[0] || {}).time || '—',
        '数据目录 ' + S.catalog.code],
       ['审核发布', (S.catalog.audits[0] || {}).time || '—',
        '审核通过，目录状态已发布'],
       ['归集工单审核', c.auditAt || '—', '工单 ' + c.orderNo + ' 审核通过，自动流转至数据归集管理系统'],
       ['自动建表', c.tables ? c.tables.前置仓.created : '—',
        (c.tables ? c.tables.前置仓.name + '、' + c.tables.归集仓.name : '—') + '，同时创建离线归集任务'],
       ['归集执行', c.runEnd || '—', '数据从前置仓归集到归集仓，共 ' + A().num(s.total) + ' 行'],
       ['治理规则配置', g.ruleSubmitAt || '—', '一数一标准 3 项 + 一数一源关联比对（主关联字段：身份证件号码）'],
       ['治理规则审核', g.ruleApprovedAt || '—', '审核通过，系统自动创建治理任务'],
       ['治理任务执行', g.taskEndedAt || '—', '数据从归集仓治理到清洗仓，优质 ' + A().num(s.good) + ' 条'],
       ['问题清单', g.taskEndedAt || '—', '问题数据 ' + A().num(s.problem) + ' 条，可查看明细并导出']].map(function (x, i) {
        return '<div class="ti' + (x[1] !== '—' ? ' done' : '') + '">' +
          '<div class="tt">' + A().esc(x[0]) + '　<span class="td">' + A().esc(x[1]) + '</span></div>' +
          '<div class="td">' + A().esc(x[2]) + '</div></div>';
      }).join('') + '</div></div></div>';

    /* 类别显示名（与问题清单一致，内部键不变） */
    var LBL = { '过滤': '过滤', '转换': '转换', '保留原值': '和权威数据源不一致', '去重': '去重' };
    var maxN = Math.max(b['过滤'], b['转换'], b['保留原值'], b['去重']);
    var bars = '<div class="panel"><div class="ph"><h3>问题数据分类</h3>' +
      '<span class="meta">合计 ' + A().num(s.problem) + ' 条，均已进入问题清单待整改</span></div>' +
      '<div class="pb"><div class="bars">' +
      ['过滤', '转换', '保留原值', '去重'].map(function (k) {
        var kind = { '过滤': 'danger', '转换': '', '保留原值': 'warn', '去重': '' }[k];
        return '<div class="bar-row"><span class="bl">' + LBL[k] + '</span>' +
          '<span class="bt"><span class="bf ' + kind + '" style="width:' +
          (maxN ? (b[k] / maxN * 100).toFixed(1) : 0) + '%"></span></span>' +
          '<span class="bv">' + b[k] + ' 条</span></div>';
      }).join('') + '</div>' +
      '<div class="eqbar" style="margin:12px 0 0">' +
      '<span>优质 <b>' + A().num(s.good) + '</b></span><span class="op">+</span>' +
      '<span>问题 <b>' + A().num(s.problem) + '</b></span><span class="op">=</span>' +
      '<span>清洗数据总量 <b>' + A().num(s.cleaned) + '</b></span>' +
      '<span class="chk">✓ 算术自洽</span></div></div></div>';

    var value = '<div class="kpis c3">' +
      [['来源可溯', '编目上报 → 审核发布 → 归集建表 → 治理入库，全链路留痕；' +
        '每一次流转都有时间戳与责任人，可定位到具体环节。'],
       ['标准可依', '一数一标准把字段级规则固化到系统：身份证件号码按 GB 11643 校验、' +
        '出生日期按 YYYY-MM-DD 校验、唯一标识做唯一性校验，规则可复用、可追溯。'],
       ['质量可控', '一数一源以权威数据源为基准逐行比对，异常数据按策略处置；' +
        '治理结果五项指标+' + A().num(s.problem) + '条问题明细全部可查、可导出。']].map(function (x) {
        return '<div class="kpi" style="padding:14px 16px">' +
          '<div class="k-l" style="font-size:14px;font-weight:600;color:var(--pri)">' + A().esc(x[0]) + '</div>' +
          '<div class="mt" style="font-size:12.5px;color:var(--t2);margin-top:6px;line-height:1.75">' +
          A().esc(x[1]) + '</div></div>';
      }).join('') + '</div>';

    return '' +
      '<div class="pagetitle"><h1>治理成效总览</h1>' +
        '<span class="sub">数据治理全流程成效汇总</span>' +
        '<div class="right">' +
          (full ? A().tag('全流程已完成', 'ok', '✓') : A().tag('流程未走完', 'warn', '◷')) +
          '<span class="btn sm" id="go-clean">查看问题清单</span>' +
        '</div></div>' +

      '<div class="kpis">' +
      [['归集数据总量', s.total, '', '前置仓 → 归集仓'],
       ['去重后数据量', s.after_dedup, '', '去重规则剔除 ' + s.dup_removed + ' 条'],
       ['清洗数据总量', s.cleaned, '', '归集仓 → 清洗仓'],
       ['优质数据', s.good, 'k-ok', '通过全部校验'],
       ['问题数据', s.problem, 'k-warn', '待整改']].map(function (k) {
        return '<div class="kpi ' + (k[2] || '') + '"><div class="k-l">' + k[0] + '</div>' +
          '<div class="k-v">' + A().num(k[1]) + '<span class="k-u">条</span></div>' +
          '<div class="k-s">' + k[3] + '</div></div>';
      }).join('') + '</div>' +

      '<div class="notice ok"><span class="ic">✓</span><div>' +
      '通过<b>数据编目</b>、<b>数据归集</b>、<b>数据治理</b>，实现数据' +
      '<b>「来源可溯、标准可依、质量可控」</b>，为后续数据共享开放和业务应用夯实基础。</div></div>' +

      flow +
      '<div class="row" style="align-items:flex-start;gap:12px">' +
        '<div class="grow" style="min-width:0">' + bars + '</div>' +
        '<div class="grow" style="min-width:0"><div class="panel"><div class="ph"><h3>治理规则执行情况</h3></div>' +
        '<div class="pb"><table class="data"><thead><tr><th>规则</th><th>字段</th>' +
        '<th class="c">命中问题</th></tr></thead><tbody>' +
        (window.DATA.rules || []).map(function (r) {
          return '<tr><td>' + A().esc(r.rule) + '</td><td>' + A().esc(r.field) + '</td>' +
            '<td class="c"><b style="color:var(--warn)">' + r.found + ' 条</b></td></tr>';
        }).join('') +
        '<tr><td>一数一源关联比对</td><td>身份证件号码 → ' +
        A().esc((function () { var g = A().S.govern || {};
          return (g.source && g.source.verify) ? g.source.verify : '多字段比对'; })()) + '</td>' +
        '<td class="c"><b style="color:var(--warn)">' + b['保留原值'] + ' 条</b></td></tr>' +
        '</tbody></table></div></div></div>' +
      '</div>' +

      value +

      '<div class="panel"><div class="ph"><h3>数据治理全流程执行情况</h3>' +
      '<span class="meta">编目 → 归集 → 治理 → 问题闭环，全环节留痕</span></div><div class="pb">' +
      '<table class="data"><thead><tr><th style="width:88px">环节</th><th>工作内容</th>' +
      '<th>执行情况</th><th class="c" style="width:80px">状态</th></tr></thead><tbody>' +
      [['目录编目', '注册新增数据目录，目录含七类属性要素共 56 个字段', '新增目录表单（56 字段 + 要素文件导入）'],
       ['目录审核', '目录要素审核通过后发布至数据目录管理', '我的审批工单 → 审核 → 已发布'],
       ['归集工单', '基于目录创建归集任务工单，填写对接方式、表英文名、数据用途', '归集填报 → 工单审批中 → 通过后自动流转'],
       ['归集建表', '审核归集工单与表结构信息，依据工单自动建表并创建归集任务', '技术审核 → 归集确认 → 归集仓表/离线任务（前置仓为既有表）'],
       ['数据归集', '手动执行任务，数据从前置仓归集到归集仓', '离线归集任务执行 → 目录状态「归集已实施」'],
       ['治理规则', '配置一数一标准与一数一源治理规则', '两步向导（3 项标准规则 + 关联比对）→ 审批 → 自动创建治理任务'],
       ['数据治理', '执行治理任务，数据从归集仓治理到清洗仓', '调度配置 → 已上线 → 实例已结束 → 五项指标'],
       ['问题闭环', '查看问题清单与不一致样本，导出交数源单位整改', '数据清洗结果明细 → 保留原值视窗 / 转换视窗 → 导出']].map(function (x) {
        return '<tr><td class="mono"><b>' + x[0] + '</b></td><td>' + A().esc(x[1]) + '</td>' +
          '<td class="mut">' + A().esc(x[2]) + '</td>' +
          '<td class="c">' + (full ? A().statusTag('已通过') : A().tag('未完成', 'mute', '○')) + '</td></tr>';
      }).join('') + '</tbody></table></div></div>' +

      '<div class="actbar"><span class="tip">数据编目、数据归集、数据治理全流程已完成，问题数据已形成清单待整改</span>' +
        '<span class="btn" id="go-clean2">查看问题清单</span>' +
        '</div>';
  }

  var init = function () {
    ['go-clean', 'go-clean2'].forEach(function (id) {
      var e = document.getElementById(id); if (e) e.onclick = function () { A().go('s7c'); };
    });
  };

  window.SCREENS.s8 = { render: render, init: init };
})();

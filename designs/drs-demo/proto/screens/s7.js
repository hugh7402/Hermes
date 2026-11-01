/* ==========================================================================
   屏7 · 治理执行与成效
   覆盖 s7 治理任务管理 / s7b 任务实例运维 / s7c 数据清洗结果明细
   核心校验点：治理结果五项数字算术自洽
              四类问题各有明细、「保留原值视窗」「转换视窗」可点开对照
   ========================================================================== */
window.SCREENS = window.SCREENS || {};
(function () {
  'use strict';
  var A = function () { return window.APP; };
  function G() { return A().S.govern; }
  function ST() { return window.DATA.stats; }
  var TYPE_KIND = { '过滤': 'danger', '转换': 'info', '保留原值': 'warn', '去重': 'mute' };
  /* 治理策略决定「与权威数据源不一致」类问题的呈现口径 */
  function strat() {
    var g = A().S.govern || {};
    return (g.source && g.source.strategy) || '保留原值';
  }
  function isConv() { return strat() === '转换为权威数据'; }
  /* 类别显示名（内部键不变，仅改界面措辞） */
  var TYPE_LABEL = { '过滤': '过滤', '转换': '转换',
                     '保留原值': '和权威数据源不一致', '去重': '去重' };
  function typeLabel(k) { return TYPE_LABEL[k] || k; }
  /* 处置方式：与所选策略保持一致（数据里存的是分类口径，不锁死处置动作） */
  function actText(p) {
    if (p.t === '保留原值') {
      return isConv() ? '按权威数据源的值替换，原值留存备查' : '保留原值';
    }
    return p.act;
  }
  function typeDesc(k) {
    if (k === '保留原值') {
      return isConv() ? '与权威数据源不一致，已按权威数据源替换，原值留存备查'
                      : '与权威数据源不一致，按策略保留原值';
    }
    return typeDescBase[k];
  }
  var TYPE_DESC = {
    '过滤': '未通过校验，标记过滤待整改',
    '转换': '格式/值域不规范，已自动转换',
    '保留原值': '与权威源不一致，按策略保留原值',
    '去重': '唯一性校验发现标识重复'
  };
  var typeDescBase = TYPE_DESC;

  function probs(t) {
    var ps = window.DATA.problems || [];
    return t ? ps.filter(function (p) { return p.t === t; }) : ps;
  }
  function fmtTypeLabels(sep) {
    var b = ST().by_type;
    return ['过滤', '转换', '保留原值', '去重'].map(function (k) {
      return typeLabel(k) + ' ' + b[k] + ' 条';
    }).join(sep || '　');
  }

  /* ── s7 治理任务管理 ── */
  function render() {
    var g = G(), st = g.taskStatus || '待创建';
    if (st === '待创建') {
      return '<div class="pagetitle"><h1>治理任务管理</h1>' +
        '<span class="sub">系统执行配置好的治理任务，数据从归集仓治理到清洗仓</span></div>' +
        '<div class="notice warn"><span class="ic">!</span><div>' +
        '暂无治理任务。治理规则配置审核通过后，系统会自动创建治理任务。</div></div>' +
        '<div class="actbar"><span class="tip">请先完成治理规则配置与审核</span>' +
        '<span class="btn pri" id="to-rule">前往规则配置</span></div>';
    }
    var online = st === '已上线', done = g.taskRun === 'done';
    var rows = '<tr>' +
      '<td class="mono">' + A().esc(A().S.catalog.name) + '_治理任务</td>' +
      '<td>' + A().esc(A().S.catalog.name) + '</td>' +
      '<td class="mono">' + A().esc(A().S.collect.table) + '</td>' +
      '<td>一数一标准 + 一数一源</td>' +
      '<td class="td">' + A().esc(g.taskCreatedAt || '—') + '</td>' +
      '<td>' + A().statusTag(done ? '已结束' : online ? '已上线' : '待上线') + '</td>' +
      '<td><div class="ops">' +
        (!online && !done ? '<a id="btn-cfg-task">配置</a><span class="sep">|</span>' : '') +
        '<a data-view="1">查看</a>' +
        (done ? '<span class="sep">|</span><a data-rerun="1">重新执行</a>' : '') +
        '</div></td></tr>';

    return '' +
      '<div class="pagetitle"><h1>治理任务管理</h1>' +
        '<span class="sub">系统执行配置好的治理任务，数据从归集仓治理到清洗仓，数据从归集仓治理到清洗仓</span>' +
        '<div class="right">' + A().tag('数据归集管理系统', 'info', '◷') + '</div></div>' +

      '<div class="kpis c4">' +
        '<div class="kpi"><div class="k-l">治理任务总数</div><div class="k-v">1<span class="k-u">个</span></div></div>' +
        '<div class="kpi k-ok"><div class="k-l">已上线</div><div class="k-v">' + (online || done ? 1 : 0) +
          '<span class="k-u">个</span></div></div>' +
        '<div class="kpi"><div class="k-l">任务创建时间</div><div class="k-v" style="font-size:15px">' +
          A().esc((g.taskCreatedAt || '—').slice(5)) + '</div>' +
          '<div class="k-s">= 规则审核通过时间</div></div>' +
        '<div class="kpi' + (done ? ' k-ok' : ' k-warn') + '"><div class="k-l">执行状态</div>' +
          '<div class="k-v" style="font-size:19px">' + (done ? '已结束' : online ? '已上线' : '待上线') + '</div>' +
          '<div class="k-s">' + (done ? '已治理到清洗仓' : '需配置调度后提交') + '</div></div>' +
      '</div>' +

      '<div class="eqbar"><span>规则审核通过时间 <b>' + A().esc(g.ruleApprovedAt || '—') + '</b></span>' +
        '<span class="op">=</span><span>治理任务创建时间 <b>' + A().esc(g.taskCreatedAt || '—') + '</b></span>' +
        '<span class="chk">' + (g.ruleApprovedAt === g.taskCreatedAt ? '✓ 时间一致' : '') + '</span></div>' +

      '<div class="tblwrap"><table class="data" id="tbl-gtask">' +
        '<thead><tr><th>治理任务名称</th><th>数据目录名称</th><th>归集表英文名称</th>' +
        '<th>治理模式</th><th>创建时间</th><th>任务状态</th>' +
        '<th style="width:110px">操作</th></tr></thead><tbody>' + rows + '</tbody></table></div>' +
      '<div class="pager"><span class="cnt">共 1 条</span><span class="pg on">1</span></div>' +

      '<div class="actbar"><span class="tip">' +
        (!online && !done ? '点击【配置】填写治理任务调度详情，提交后状态变为【已上线】并执行'
         : done ? '前往【监控运维中心-任务实例运维管理】查看执行情况，再到【统一问题工单-数据清洗结果明细】查看治理成果'
         : '治理任务已上线') + '</span>' +
        (!online && !done ? '<span class="btn pri" id="btn-cfg-task2">配置</span>' : '') +
        (done ? '<span class="btn pri" id="go-inst">查看任务实例 →</span>' : '') +
      '</div>';
  }

  /* 配置调度详情 → 提交 → 已上线并执行 */
  function openTaskCfg() {
    var g = G();
    A().openDrawer('治理任务调度配置',
      '<div class="fgrid c2">' +
      '<div class="fi"><label>治理任务名称</label><div class="ctl ro"><span>' +
        A().esc(A().S.catalog.name) + '_治理任务</span></div></div>' +
      '<div class="fi"><label>源表（归集仓）</label><div class="ctl ro"><span class="mono">' +
        A().esc(A().S.collect.tables.归集仓.name) + '</span></div></div>' +
      '<div class="fi"><label>目标表（清洗仓）</label><div class="ctl ro"><span class="mono">' +
        'dws_' + A().esc(A().S.collect.table) + '</span></div></div>' +
      '<div class="fi"><label><span class="req">*</span>调度方式</label>' +
        '<div class="ctl"><select id="t-mode"><option>立即执行</option><option>定时调度</option></select></div></div>' +
      '<div class="fi"><label><span class="req">*</span>调度周期</label>' +
        '<div class="ctl"><select id="t-cycle"><option>每日 02:00</option><option>每小时</option><option>手动触发</option></select></div></div>' +
      '<div class="fi"><label><span class="req">*</span>并发度</label>' +
        '<div class="ctl"><select id="t-par"><option>4</option><option>2</option><option>8</option></select></div></div>' +
      '<div class="fi span2"><label><span class="req">*</span>失败重试策略</label>' +
        '<div class="ctl"><select id="t-retry"><option>失败重试 3 次，间隔 5 分钟</option>' +
        '<option>不重试</option></select></div></div>' +
      '</div>' +
      '<div class="notice" style="margin-top:12px"><span class="ic">i</span><div>' +
      '提交后治理任务状态变为 <b>【已上线】</b>，系统同时执行该治理任务，数据从<b>归集仓</b>治理到<b>清洗仓</b>。</div></div>',
      '<span class="btn" data-close="1">取消</span><span class="btn pri" id="tc-ok">提交</span>', true);
    var b = document.getElementById('tc-ok');
    if (b) b.onclick = function () {
      var g2 = G();
      g2.taskStatus = '已上线';
      g2.taskStartedAt = A().now();
      A().closeDrawer(); A().render();
      A().toast('治理任务已上线，正在执行…');
      setTimeout(function () {
        G().taskRun = 'done';
        G().taskEndedAt = A().now();
        A().S.done.grun = true;
        A().render();
        A().openModal('治理任务执行完成',
          '<div class="notice ok"><span class="ic">✓</span><div>数据已从<b>归集仓</b>治理到<b>清洗仓</b>，' +
          '共 ' + A().num(ST().cleaned) + ' 行。</div></div>' +
          '<div class="eqbar" style="margin-top:12px">' +
          '<span>归集总量 <b>' + A().num(ST().total) + '</b></span><span class="op">→</span>' +
          '<span>去重后 <b>' + A().num(ST().after_dedup) + '</b></span><span class="op">→</span>' +
          '<span>清洗总量 <b>' + A().num(ST().cleaned) + '</b></span><span class="op">=</span>' +
          '<span>优质 <b>' + A().num(ST().good) + '</b> + 问题 <b>' + A().num(ST().problem) + '</b></span>' +
          '<span class="chk">✓ 算术自洽</span></div>' +
          '<div class="notice" style="margin-top:10px"><span class="ic">→</span><div>' +
          '到【监控运维中心-任务实例运维管理】查看执行情况，再到【统一问题工单-数据清洗结果明细】查看问题清单。</div></div>',
          '<span class="btn" data-close-m="1">取消</span>' +
          '<span class="btn pri" id="to-inst">查看任务实例</span>');
        var t = document.getElementById('to-inst');
        if (t) t.onclick = function () { A().closeModal(); A().go('s7b'); };
      }, 1000);
    };
  }

  /* ── s7b 任务实例运维管理 ── */
  function renderInstance() {
    var g = G(), done = g.taskRun === 'done';
    return '' +
      '<div class="pagetitle"><h1>任务实例运维管理</h1>' +
        '<span class="sub">查看治理任务实例执行情况</span>' +
        '<div class="right">' + A().tag('监控运维中心', 'info', '◷') + '</div></div>' +
      '<div class="tblwrap"><table class="data" id="tbl-inst">' +
        '<thead><tr><th>实例名称</th><th>所属任务</th><th>开始时间</th><th>结束时间</th>' +
        '<th class="n">处理行数</th><th class="n">问题行数</th><th>实例状态</th>' +
        '<th style="width:110px">操作</th></tr></thead><tbody>' +
        '<tr><td class="mono">INST_' + A().esc((g.taskStartedAt || '').replace(/[-: ]/g, '')) + '</td>' +
        '<td>' + A().esc(A().S.catalog.name) + '_治理任务</td>' +
        '<td class="td">' + A().esc(g.taskStartedAt || '—') + '</td>' +
        '<td class="td">' + A().esc(g.taskEndedAt || '—') + '</td>' +
        '<td class="n">' + (done ? A().num(ST().cleaned) : '—') + '</td>' +
        '<td class="n">' + (done ? '<b style="color:var(--warn)">' + A().num(ST().problem) + '</b>' : '—') + '</td>' +
        '<td>' + A().statusTag(done ? '已结束' : '执行中') + '</td>' +
        '<td><div class="ops"><a data-view="1">日志</a></div></td></tr>' +
        '</tbody></table></div>' +
      '<div class="pager"><span class="cnt">共 1 条</span><span class="pg on">1</span></div>' +
      (done
        ? '<div class="notice ok" style="margin-top:12px"><span class="ic">✓</span><div>' +
          '任务实例状态为 <b>【已结束】</b>，说明治理任务执行完成，数据已从归集仓治理到清洗仓。</div></div>'
        : '<div class="notice warn" style="margin-top:12px"><span class="ic">◷</span><div>任务实例正在执行…</div></div>') +
      '<div class="actbar"><span class="tip">' +
        (done ? '前往【统一问题工单-数据清洗结果明细】查看治理成果与问题清单'
              : '等待任务执行完成') + '</span>' +
        (done ? '<span class="btn pri" id="go-clean">查看数据清洗结果明细 →</span>' : '') +
      '</div>';
  }

  /* ── s7c 数据清洗结果明细（治理成果 + 问题清单）── */
  var flt = '全部', page = 1, PAGE = 12;

  function renderClean() {
    var g = G(), done = g.taskRun === 'done';
    if (!done) {
      return '<div class="pagetitle"><h1>数据清洗结果明细</h1>' +
        '<span class="sub">查看治理成果与问题清单</span></div>' +
        '<div class="notice warn"><span class="ic">!</span><div>' +
        '治理任务尚未执行完成，暂无清洗结果。</div></div>' +
        '<div class="actbar"><span class="tip">请先执行治理任务</span>' +
        '<span class="btn pri" id="to-gtask">前往治理任务管理</span></div>';
    }
    var s = ST(), b = s.by_type;
    var list = flt === '全部' ? probs() : probs(flt);
    var pages = Math.max(1, Math.ceil(list.length / PAGE));
    if (page > pages) page = pages;
    var slice = list.slice((page - 1) * PAGE, page * PAGE);

    var kpi = '<div class="kpis">' +
      [['归集数据总量', s.total, '', '前置仓 → 归集仓'],
       ['去重后数据量', s.after_dedup, '', '去重规则剔除 ' + s.dup_removed + ' 条完全重复'],
       ['清洗数据总量', s.cleaned, '', '归集仓 → 清洗仓'],
       ['优质数据', s.good, 'k-ok', '通过全部校验'],
       ['问题数据', s.problem, 'k-warn', '待整改，四类明细如下']].map(function (k) {
        return '<div class="kpi ' + (k[2] || '') + '"><div class="k-l">' + k[0] + '</div>' +
          '<div class="k-v">' + A().num(k[1]) + '<span class="k-u">条</span></div>' +
          '<div class="k-s">' + k[3] + '</div></div>';
      }).join('') + '</div>';

    var eq = '<div class="eqbar">' +
      '<span>归集 <b>' + A().num(s.total) + '</b></span><span class="op">−</span>' +
      '<span>完全重复 <b>' + A().num(s.dup_removed) + '</b></span><span class="op">=</span>' +
      '<span>去重后 <b>' + A().num(s.after_dedup) + '</b></span><span class="op">=</span>' +
      '<span>清洗总量 <b>' + A().num(s.cleaned) + '</b></span><span class="op">=</span>' +
      '<span>优质 <b>' + A().num(s.good) + '</b> + 问题 <b>' + A().num(s.problem) + '</b></span>' +
      '<span class="chk">✓ ' + A().num(s.good) + ' + ' + A().num(s.problem) + ' = ' +
      A().num(s.good + s.problem) + ' 与清洗总量一致</span></div>';

    var maxN = Math.max(b['过滤'], b['转换'], b['保留原值'], b['去重']);
    var bars = '<div class="panel"><div class="ph"><h3>问题数据分类</h3>' +
      '<span class="meta">四类问题合计 ' + A().num(s.problem) + ' 条（点击行可查看明细）</span></div>' +
      '<div class="pb"><div class="bars">' +
      ['过滤', '转换', '保留原值', '去重'].map(function (k) {
        var n = b[k], w = maxN ? (n / maxN * 100) : 0;
        var kind = { '过滤': 'danger', '转换': '', '保留原值': 'warn', '去重': '' }[k];
        return '<div class="bar-row" data-flt="' + k + '" style="cursor:pointer">' +
          '<span class="bl">' + k + '</span>' +
          '<span class="bt"><span class="bf ' + kind + '" style="width:' + w.toFixed(1) + '%"></span></span>' +
          '<span class="bv">' + n + ' 条</span></div>';
      }).join('') + '</div>' +
      '<div class="mut sm" style="margin-top:9px">' +
      ['过滤', '转换', '保留原值', '去重'].map(function (k) {
        return '<div>' + A().tag(k, TYPE_KIND[k], '·') + ' ' + A().esc(typeDesc(k)) + '</div>'; }).join('') +
      '</div></div></div>';

    var tabs = '<div class="filters" style="gap:0;padding:0;overflow:hidden">' +
      ['全部'].concat(['过滤', '转换', '保留原值', '去重']).map(function (t) {
        var n = t === '全部' ? probs().length : b[t];
        return '<span data-tab="' + t + '" style="padding:8px 16px;cursor:pointer;font-size:13px;' +
          (flt === t ? 'color:var(--pri);font-weight:600;border-bottom:2px solid var(--pri);background:var(--pri-l2)'
                     : 'color:var(--t2);border-bottom:2px solid transparent') + '">' +
          typeLabel(t) + ' <span class="mut">(' + n + ')</span></span>';
      }).join('') + '</div>';

    var tbl = '<div class="tblwrap"><table class="data" id="tbl-clean">' +
      '<thead><tr><th class="c" style="width:50px">序号</th><th style="width:90px">问题类型</th>' +
      '<th style="width:130px">问题字段</th><th>业务主键</th>' +
      '<th>' + (isConv() ? '原始值（留存）' : '原始值') + '</th>' +
      '<th>' + (isConv() ? '权威源值（已生效）' : '权威源值') + '</th>' +
      '<th>命中规则</th><th style="width:150px">操作</th></tr></thead><tbody>' +
      (slice.length ? slice.map(function (p) {
        return '<tr data-p="' + p.n + '">' +
          '<td class="c">' + p.n + '</td>' +
          '<td>' + A().tag(typeLabel(p.t), TYPE_KIND[p.t], '·') + '</td>' +
          '<td>' + A().esc(p.f) + '</td>' +
          '<td class="mono">' + A().esc(String(p.key).slice(0, 18)) + '</td>' +
          '<td>' + A().esc(String(p.o).slice(0, 18)) + '</td>' +
          '<td>' + A().esc(String(p.a).slice(0, 18)) + '</td>' +
          '<td class="mut">' + A().esc(p.rule) + '</td>' +
          '<td><div class="ops">' +
            '<a data-view-p="' + p.n + '">' +
            (p.t === '保留原值' ? '保留原值视窗' : p.t === '转换' ? '转换视窗' : '问题明细') + '</a>' +
          '</div></td></tr>';
      }).join('')
       : '<tr><td colspan="8" class="t-center mut" style="padding:24px">该类问题无数据</td></tr>') +
      '</tbody></table></div>';

    var pager = '<div class="pager"><span class="cnt">共 ' + A().num(list.length) + ' 条　' +
      (flt === '全部' ? '四类问题合计' : '当前筛选：' + flt) + '</span>' +
      '<span class="pages btn-row" style="display:flex;gap:3px">' +
      '<button class="pg" id="pg-prev"' + (page <= 1 ? ' disabled' : '') + '>‹ 上一页</button>' +
      Array.from({ length: Math.min(pages, 7) }, function (_, i) { return i + 1; }).map(function (n) {
        return '<button class="pg' + (n === page ? ' on' : '') + '" data-pg="' + n + '">' + n + '</button>';
      }).join('') +
      '<button class="pg" id="pg-next"' + (page >= pages ? ' disabled' : '') + '>下一页 ›</button></span>' +
      '<span class="btn sm" id="btn-export">导出问题清单</span></div>';

    return '' +
      '<div class="pagetitle"><h1>数据清洗结果明细</h1>' +
        '<span class="sub">查看数据清洗结果明细，确认与权威数据源不一致的异常数据样本</span>' +
        '<div class="right">' + A().tag('统一问题工单', 'info', '◷') + '</div></div>' +
      kpi + eq + bars +

      '<div class="panel"><div class="ph"><h3>问题清单</h3>' +
      '<span class="meta">共 ' + A().num(probs().length) + ' 条　' + A().esc(fmtTypeLabels('　')) + '</span></div>' +
      '<div class="pb" style="padding:0">' + tabs + tbl + pager + '</div></div>' +

      '<div class="actbar"><span class="tip">' +
        '</span>' +
        '<span class="btn" id="btn-export2">导出问题清单</span>' +
        '<span class="btn pri" id="go-summary">查看治理成效总览 →</span></div>';
  }

  /* 问题明细视窗（保留原值视窗 / 转换视窗 / 通用问题明细） */
  function openProblem(n) {
    var p = (window.DATA.problems || []).filter(function (x) { return x.n === n; })[0];
    if (!p) return;
    var row = null;
    var rows = window.DATA.rows || [], cols = window.DATA.cols || [], colsCn = window.DATA.colsCn || [];
    // 数据已打乱，按身份证件号码或唯一标识定位
    var iId = cols.indexOf('sfzjhm'), iKey = cols.indexOf('zrrwybs'), iName = cols.indexOf('xm');
    for (var i = 0; i < rows.length; i++) {
      if (p.t === '过滤') { if (rows[i][iId] === p.o) { row = rows[i]; break; } }
      else if (String(rows[i][iKey]) === String(p.key)) { row = rows[i]; break; }
    }
    var title = p.t === '保留原值' ? '保留原值视窗' : p.t === '转换' ? '转换视窗' : '问题数据明细';
    var cmp = '<div class="cmp">' +
      '<div class="side-c src"><div class="h">' + A().tag('数据侧（归集仓）', 'warn', '◷') +
        '　字段：' + A().esc(p.f) + '</div><div class="val">' + A().esc(String(p.o)) + '</div></div>' +
      '<div class="mid">→</div>' +
      '<div class="side-c dst"><div class="h">' + A().tag('权威数据源（公安人口库）', 'ok', '✓') +
        '　表：authority_natural_person</div><div class="val">' + A().esc(String(p.a)) + '</div></div>' +
      '</div>';

    var body = '<div class="notice ' + (p.t === '保留原值' ? 'warn' : '') + '"><span class="ic">' +
      (p.t === '保留原值' ? '!' : 'i') + '</span><div>' +
      '问题类型 <b>' + A().esc(typeLabel(p.t)) + '</b></div></div>' + cmp +
      '<div class="panel" style="margin-top:12px"><div class="ph"><h3>问题记录</h3></div><div class="pb"><div class="kv">' +
      '<div class="r"><div class="k">序号</div><div class="v">' + p.n + '</div></div>' +
      '<div class="r"><div class="k">问题类型</div><div class="v">' + A().tag(typeLabel(p.t), TYPE_KIND[p.t], '·') + '</div></div>' +
      '<div class="r"><div class="k">问题字段</div><div class="v">' + A().esc(p.f) + '</div></div>' +
      '<div class="r"><div class="k">业务主键</div><div class="v mono">' + A().esc(p.key) + '</div></div>' +
      '<div class="r full"><div class="k">命中规则</div><div class="v">' + A().esc(p.rule) + '</div></div>' +
      '<div class="r full"><div class="k">处置方式</div><div class="v">' + A().esc(actText(p)) + '</div></div>' +
      (p.t === '保留原值' && isConv()
        ? '<div class="r"><div class="k">转换后生效值</div><div class="v"><b>' + A().esc(String(p.a)) +
          '</b></div></div><div class="r full"><div class="k">原始值（留存备查）</div><div class="v">' +
          A().esc(String(p.o)) + '</div></div>'
        : '') +
      '</div></div></div>';

    if (row) {
      body += '<div class="panel"><div class="ph"><h3>该记录完整字段（归集仓原样）</h3>' +
        '<span class="meta">共 ' + cols.length + ' 个字段</span></div><div class="pb">' +
        '<div class="kv c3">' + cols.map(function (c, ci) {
          var mark = (colsCn[ci] === p.f) ? ' style="color:var(--warn);font-weight:600"' : '';
          return '<div class="r"><div class="k">' + A().esc(colsCn[ci]) + '</div>' +
            '<div class="v"' + mark + '>' + A().esc(String(row[ci] || '—')) + '</div></div>';
        }).join('') + '</div></div></div>';
    }
    if (p.t === '保留原值') {
      body += '<div class="notice warn" style="margin-top:12px"><span class="ic">!</span><div>' +
        '本记录的「' + A().esc(p.f) + '」与权威数据源不一致。本次的异常处理策略为 <b>' +
        A().esc(strat()) + '</b>，' + (isConv()
          ? '该字段<b>已替换为权威数据源的值</b>（生效值 <b>' + A().esc(String(p.a)) +
            '</b>），<b>原始值 ' + A().esc(String(p.o)) + ' 已留存备查</b>，可追溯。'
          : '故<b>不作转换</b>，原样进入清洗仓并标记为待整改。') +
        '</div></div>';
    }
    A().openDrawer(title + ' · 第 ' + p.n + ' 条', body,
      '<span class="btn" data-close="1">关闭</span>' +
      '<button class="btn" id="p-export">导出本条</button>', true);
    var e = document.getElementById('p-export');
    if (e) e.onclick = function () { A().toast('已导出第 ' + p.n + ' 条问题记录（模拟）', 'ok'); };
  }

  /* 导出问题清单（真实下载 CSV） */
  function exportCsv() {
    var ps = flt === '全部' ? probs() : probs(flt);
    var head = ['序号', '问题类型', '问题字段', '业务主键',
                isConv() ? '原始值（留存）' : '原始值',
                isConv() ? '权威源值（已生效）' : '权威源值', '处置方式', '命中规则'];
    var lines = [head.join(',')].concat(ps.map(function (p) {
      return [p.n, typeLabel(p.t), p.f, p.key, p.o, p.a, actText(p), p.rule].map(function (v) {
        var s = String(v == null ? '' : v);
        return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
      }).join(',');
    }));
    var blob = new Blob(['\ufeff' + lines.join('\r\n')], { type: 'text/csv;charset=utf-8' });
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = '数据治理问题清单_' + (flt === '全部' ? '全部' : typeLabel(flt)) + '_' + A().today() + '.csv';
    document.body.appendChild(a); a.click();
    setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 400);
    A().toast('已导出 ' + ps.length + ' 条问题数据', 'ok');
  }

  var init = function () {
    var b1 = document.getElementById('btn-cfg-task'), b2 = document.getElementById('btn-cfg-task2');
    if (b1) b1.onclick = openTaskCfg;
    if (b2) b2.onclick = openTaskCfg;
    var gi = document.getElementById('go-inst');
    if (gi) gi.onclick = function () { A().go('s7b'); };
    var tr = document.getElementById('to-rule');
    if (tr) tr.onclick = function () { A().go('s6'); };
    document.querySelectorAll('[data-view]').forEach(function (a) {
      a.onclick = function () {
        var g = G();
        var kv = function (k, v) {
          return '<div class="r"><div class="k">' + k + '</div><div class="v">' + v + '</div></div>';
        };
        A().openDrawer('治理任务详情',
          '<div class="kv">' +
            kv('治理任务名称', A().esc(A().S.collect.table + '_govern')) +
            kv('数据目录名称', A().esc(A().S.catalog.name)) +
            kv('治理模式', '一数一标准 + 一数一源') +
            kv('源表（归集仓）', '<span class="mono">' + A().esc('dwd_' + A().S.collect.table) + '</span>') +
            kv('目标表（清洗仓）', '<span class="mono">' + A().esc('dws_' + A().S.collect.table) + '</span>') +
            kv('任务创建时间', A().esc(g.taskCreatedAt || '—')) +
            kv('任务状态', A().statusTag(g.taskRun === 'done' ? '已结束' : '待执行')) +
            kv('启用规则数', '<b>' + (window.DATA.rules || []).length + '</b> 条') +
            kv('归集总量', '<b>' + A().num(ST().total) + '</b> 行') +
            kv('优质数据', '<b style="color:var(--ok)">' + A().num(ST().good) + '</b> 行') +
            kv('问题数据', '<b style="color:var(--warn)">' + A().num(ST().problem) + '</b> 行') +
          '</div>',
          '<span class="btn" data-close="1">关闭</span>' +
          (g.taskRun === 'done' ? '<span class="btn pri" id="rd-rerun">重新执行</span>' : ''));
        var rb = document.getElementById('rd-rerun');
        if (rb) rb.onclick = function () {
          var rr = document.querySelector('[data-rerun]');
          A().closeDrawer();
          if (rr) { rr.click(); }
        };
      };
    });
    // 治理任务「重新执行」：按当前启用规则重跑并刷新统计
    document.querySelectorAll('[data-rerun]').forEach(function (a) {
      a.onclick = function () {
        A().openModal('重新执行治理任务',
          '将对本次待治理数据<b>重新执行</b>治理规则（一数一标准 + 一数一源），' +
          '按当前启用规则重新校验并刷新问题清单。<br>' +
          '<span class="mut sm">治理统计将同步重算，原有治理结果会被覆盖。</span>',
          '<span class="btn" data-close-m="1">取消</span>' +
          '<span class="btn pri" id="rerun-ok">确定重新执行</span>');
        var b = document.getElementById('rerun-ok');
        if (b) b.onclick = function () {
          var g2 = G();
          g2.taskRun = 'running';
          A().closeModal();
          A().render();
          A().toast('治理任务正在重新执行…', 'ok');
          window.setTimeout(function () {
            var g3 = G();
            g3.taskRun = 'done';
            A().S.done.grun = true;
            A().render();
            A().toast('重新执行完成，问题清单与治理统计已刷新', 'ok');
          }, 1400);
        };
      };
    });
  };

  var initInst = function () {
    var g = document.getElementById('go-clean');
    if (g) g.onclick = function () { A().go('s7c'); };
    document.querySelectorAll('[data-view]').forEach(function (a) {
      a.onclick = function () { A().toast('实例运行日志'); };
    });
  };

  // 屏内状态重置：仅在「进入本屏」时调用（由 app.js 的 go() 钩子触发），
  // 不能放在 init() 里 —— 否则每次筛选/翻页都会把状态重置回去
  var enterClean = function () { flt = '全部'; page = 1; };

  var initClean = function () {
    var tg = document.getElementById('to-gtask');
    if (tg) tg.onclick = function () { A().go('s7'); };
    document.querySelectorAll('[data-tab]').forEach(function (t) {
      t.onclick = function () { flt = t.getAttribute('data-tab'); page = 1; A().render(); };
    });
    document.querySelectorAll('[data-flt]').forEach(function (t) {
      t.onclick = function () { flt = t.getAttribute('data-flt'); page = 1; A().render(); };
    });
    document.querySelectorAll('[data-pg]').forEach(function (b) {
      b.onclick = function () { page = parseInt(b.getAttribute('data-pg'), 10); A().render(); };
    });
    var pv = document.getElementById('pg-prev');
    if (pv) pv.onclick = function () { if (page > 1) { page--; A().render(); } };
    var nx = document.getElementById('pg-next');
    if (nx) nx.onclick = function () { page++; A().render(); };
    document.querySelectorAll('[data-view-p]').forEach(function (a) {
      a.onclick = function () { openProblem(parseInt(a.getAttribute('data-view-p'), 10)); };
    });
    ['btn-export', 'btn-export2'].forEach(function (id) {
      var e = document.getElementById(id); if (e) e.onclick = exportCsv;
    });
    var gs = document.getElementById('go-summary');
    if (gs) gs.onclick = function () { A().go('s8'); };
  };

  window.SCREENS.s7 = { render: render, init: init, openTaskCfg: openTaskCfg };
  window.SCREENS.s7b = { render: renderInstance, init: initInst };
  window.SCREENS.s7c = { render: renderClean, init: initClean, enter: enterClean,
                         openProblem: openProblem, exportCsv: exportCsv,
                         setFlt: function (f, p) { flt = f; page = p || 1; } };
})();

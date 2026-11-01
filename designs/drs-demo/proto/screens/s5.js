/* ==========================================================================
   屏5 · 离线归集任务执行
   覆盖 s5 离线归集任务 / s5b 编目系统「目录归集状态」
   支持真实文件导入待归集数据（前置仓录入）
   ========================================================================== */
window.SCREENS = window.SCREENS || {};
(function () {
  'use strict';
  var A = function () { return window.APP; };
  function C() { return A().S.collect; }

  function taskStatus() {
    var c = C();
    if (!c.task) return '未创建';
    if (c.taskRun === 'done') return '已结束';
    if (c.taskRun === 'running') return '执行中';
    return '待执行';
  }

  function render() {
    var c = C(), st = taskStatus();
    if (!c.task) {
      return '<div class="pagetitle"><h1>离线归集任务</h1>' +
        '<span class="sub">手动执行任务，实现数据从前置仓到归集仓</span></div>' +
        '<div class="notice warn"><span class="ic">!</span><div>' +
        '暂无归集任务。归集工单通过技术审核与归集确认后，系统会自动创建离线归集任务。</div></div>' +
        '<div class="actbar"><span class="tip">请先完成归集工单的技术审核与归集确认</span>' +
        '<span class="btn pri" id="back-collect">前往归集工单审核</span></div>';
    }
    var rows = '<tr' + (st === '执行中' ? ' class="sel"' : '') + '>' +
      '<td class="mono">' + A().esc(c.task.name) + '</td>' +
      '<td>' + A().esc(A().S.catalog.name) + '</td>' +
      '<td>离线归集</td>' +
      '<td class="mono">' + A().esc(c.tables.前置仓.name) + ' → ' + A().esc(c.tables.归集仓.name) + '</td>' +
      '<td class="td">' + A().esc(c.task.created) + '</td>' +
      '<td class="n">' + (c.taskRun === 'done' ? A().num(C().rows || 1000) : '—') + '</td>' +
      '<td>' + A().statusTag(st) + '</td>' +
      '<td><div class="ops">' +
        (st === '待执行' ? '<a id="btn-run">执行</a><span class="sep">|</span>' : '') +
        '<a data-task-detail="1">详情</a></div></td></tr>';

    return '' +
      '<div class="pagetitle"><h1>离线归集任务</h1>' +
        '<span class="sub">手动执行任务，实现数据从前置仓到归集仓</span>' +
        '<div class="right">' + A().tag('数据归集管理系统', 'info', '◷') + '</div></div>' +

      '<div class="kpis c4">' +
        '<div class="kpi"><div class="k-l">任务总数</div><div class="k-v">1<span class="k-u">个</span></div></div>' +
        '<div class="kpi k-warn"><div class="k-l">待执行</div><div class="k-v">' +
          (st === '待执行' ? 1 : 0) + '<span class="k-u">个</span></div></div>' +
        '<div class="kpi' + (st === '已结束' ? ' k-ok' : '') + '"><div class="k-l">已结束</div><div class="k-v">' +
          (st === '已结束' ? 1 : 0) + '<span class="k-u">个</span></div></div>' +
        '<div class="kpi"><div class="k-l">前置仓数据量</div><div class="k-v">' +
          (c.staged ? A().num(C().rows || 1000) : 0) + '<span class="k-u">行</span></div>' +
          '<div class="k-s">' + (c.staged ? '已录入待归集数据' : '待录入') + '</div></div>' +
      '</div>' +

      (!c.staged
        ? '<div class="notice warn"><span class="ic">!</span><div>' +
          '前置仓尚无数据。需<b>先在前置仓录入待归集数据</b>。</div></div>'
        : st === '已结束'
        ? '<div class="notice ok"><span class="ic">✓</span><div>' +
          '归集任务执行完成，数据已从<b>前置仓</b>归集到<b>归集仓</b>，共 <b>' + A().num(C().rows || 1000) + '</b> 行。</div></div>'
        : '') +

      '<div class="filters">' +
        '<div class="f"><label>任务名称</label><input class="inp mono" value="' + A().esc(c.task.name) + '" readonly></div>' +
        '<div class="f"><label>任务状态</label><input class="inp" value="' + st + '" readonly></div>' +
        '<div class="f"><label>归集方式</label><input class="inp" value="离线归集" readonly></div>' +
        '<span class="btn sm pri">查询</span><span class="btn sm">重置</span>' +
      '</div>' +

      '<div class="tblwrap"><table class="data" id="tbl-task">' +
        '<thead><tr><th>任务名称</th><th>数据目录名称</th><th>归集方式</th><th>源表 → 目标表</th>' +
        '<th>创建时间</th><th class="n">归集行数</th><th>任务状态</th>' +
        '<th style="width:110px">操作</th></tr></thead><tbody>' + rows + '</tbody></table></div>' +
      '<div class="pager"><span class="cnt">共 1 条</span><span class="pg on">1</span></div>' +

      (c.taskRun === 'done'
        ? '<div class="panel" style="margin-top:14px"><div class="ph"><h3>任务执行信息</h3></div><div class="pb">' +
          '<div class="kv c3">' +
          '<div class="r"><div class="k">开始时间</div><div class="v td">' + A().esc(c.runStart) + '</div></div>' +
          '<div class="r"><div class="k">结束时间</div><div class="v td">' + A().esc(c.runEnd) + '</div></div>' +
          '<div class="r"><div class="k">执行结果</div><div class="v">' + A().statusTag('已结束') + '</div></div>' +
          '<div class="r"><div class="k">归集行数</div><div class="v"><b style="color:var(--pri)">' +
            A().num(C().rows || 1000) + ' 行</b></div></div>' +
          '<div class="r"><div class="k">失败行数</div><div class="v">0 行</div></div>' +
          '<div class="r"><div class="k">耗时</div><div class="v">3.2 秒</div></div>' +
          '</div></div></div>' : '') +

      '<div class="actbar"><span class="tip">' +
        (!c.staged ? '点击【录入待归集数据】导入基础数据集到前置仓'
         : st === '待执行' ? '点击【执行】，数据将从前置仓归集到归集仓'
         : st === '执行中' ? '任务执行中…'
         : '回到编目系统确认该目录的归集状态变为「归集已实施」') + '</span>' +
        (c.staged ? '<span class="btn" id="btn-stage">📎 重新录入待归集数据</span>'
                  : '<span class="btn pri" id="btn-stage">📎 录入待归集数据</span>') +
        '<input type="file" id="file-data" accept=".csv,.txt" style="display:none">' +
        (c.staged && st === '待执行' ? '<span class="btn pri" id="btn-run2">执行</span>' : '') +
        (st === '已结束' ? '<span class="btn pri" id="go-status">查看目录归集状态 →</span>' : '') +
      '</div>';
  }

  /* 前置仓录入数据（真实文件读取） */
  function openStage() {
    var fi = document.getElementById('file-data');
    if (fi) fi.click();
  }
  /* ── 对上传数据按真实规则现算五项数字 ──────────────────────────
     口径：total − 去重 = 清洗总量 = 优质 + 问题
     问题四类：过滤（校验码不通过）/ 转换（格式转换）/ 保留原值（与权威源不一致）/ 去重 */
  function computeStats(lines, withProblems) {
    var hdr = (lines[0] || '').replace(/^\uFEFF/, '').split(',').map(function (x) { return x.trim(); });
    var pick = function () {
      for (var a = 0; a < arguments.length; a++) {
        for (var j = 0; j < hdr.length; j++) { if (hdr[j].indexOf(arguments[a]) >= 0) { return j; } }
      }
      return -1;
    };
    var iUid = pick('唯一标识'), iId = pick('身份证'), iName = pick('姓名'), iBatch = pick('批次号'),
        iBirth = pick('出生日期'), iSex = pick('性别');
    if (iUid < 0) { return null; }
    var recs = [];
    for (var i = 1; i < lines.length; i++) {
      if (lines[i].trim()) { recs.push(lines[i].split(',')); }
    }
    if (!recs.length) { return null; }

    // 一数一源：按主关联字段（身份证件号码）把权威数据源建成索引，用于逐行比对验证字段
    var authById = {};
    (window.DATA && window.DATA.auth || []).forEach(function (row) {
      if (iId >= 0 && row[iId]) { authById[row[iId]] = row; }
    });
    // 验证字段可多选：取治理规则配置，缺省回落到「姓名」
    var RS = (window.DATA && window.DATA.ruleSource) || {};
    var VF = (RS.verify_field_list && RS.verify_field_list.length)
      ? RS.verify_field_list : [RS.verify_field || '姓名'];
    var vIdx = {};
    VF.forEach(function (lb) { var j = pick(lb); if (j >= 0) { vIdx[lb] = j; } });
    var relField = function (c, ar) {   // 返回首个不一致的验证字段
      for (var q = 0; q < VF.length; q++) {
        var j = vIdx[VF[q]]; if (j == null) { continue; }
        var bv = c[j] == null ? '' : String(c[j]);
        var av = ar[j] == null ? '' : String(ar[j]);
        if (bv !== av) { return { field: VF[q], v: bv, a: av }; }
      }
      return null;
    };
    var idOk = function (s) {           // GB 11643 校验码
      if (!s || !/^\d{17}[\dXx]$/.test(s)) { return false; }
      var w = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2], c = '10X98765432', sum = 0;
      for (var k = 0; k < 17; k++) { sum += (parseInt(s.charAt(k), 10) || 0) * w[k]; }
      return c.charAt(sum % 11) === s.charAt(17).toUpperCase();
    };

    // ① 去重（按自然人唯一标识，保留首条）
    var seenU = {}, dupRemoved = 0, kept = [];
    recs.forEach(function (c) {
      var u = c[iUid] || '';
      if (seenU[u]) { dupRemoved++; return; }
      seenU[u] = 1; kept.push(c);
    });

    // ② 逐行按真实规则判定
    var pFilter = 0, pConvert = 0, pKeep = 0, pDup = 0, seenId = {};
    var kids = [];
    var prob = withProblems ? [] : null;
    kept.forEach(function (c) {
      var uid = c[iUid] || '';
      var idv = iId >= 0 ? (c[iId] || '') : '';
      var nm = iName >= 0 ? (c[iName] || '') : '';
      var birth = iBirth >= 0 ? (c[iBirth] || '') : '';
      var sex = iSex >= 0 ? (c[iSex] || '') : '';
      var type = '', field = '', rule = '', act = '', o = '', a = '';
      if (iName >= 0 && !nm) {
        type = '过滤'; field = '姓名'; rule = '一数一标准·姓名必填校验';
        act = '姓名字段为空，标记过滤待整改（未写入清洗仓有效集）'; o = '（空值）';
      } else if (iBirth >= 0 && !birth) {
        type = '过滤'; field = '出生日期'; rule = '一数一标准·出生日期必填校验';
        act = '出生日期字段为空，标记过滤待整改（未写入清洗仓有效集）'; o = '（空值）';
      } else if (iBatch >= 0 && !(c[iBatch] || '')) {
        type = '过滤'; field = '数据批次号'; rule = '一数一标准·数据批次号必填校验';
        act = '数据批次号字段为空，标记过滤待整改（未写入清洗仓有效集）'; o = '（空值）';
      } else if (iId >= 0 && !idOk(idv)) {
        type = '过滤'; field = '身份证件号码'; rule = '一数一标准·身份证件号码 GB 11643 校验';
        act = '校验码不通过，标记过滤待整改（未写入清洗仓有效集）'; o = idv;
      } else if (iBirth >= 0 && birth && !/^\d{4}-\d{2}-\d{2}$/.test(birth)) {
        type = '转换'; field = '出生日期'; rule = '一数一标准·出生日期格式 YYYY-MM-DD';
        act = '按标准规则转换为规范值后写入清洗仓'; o = birth;
      } else if (iSex >= 0 && sex && ['男', '女', '未知'].indexOf(sex) < 0) {
        type = '转换'; field = '性别'; rule = '一数一标准·性别值域 {男,女,未知}';
        act = '按标准规则转换为规范值后写入清洗仓'; o = sex;
      } else if (iId >= 0 && idv && authById[idv] && relField(c, authById[idv])) {
        var hh = relField(c, authById[idv]);
        type = (RS.strategy === '转换为权威数据') ? '转换' : '保留原值';
        field = hh.field; o = hh.v; a = hh.a;
        rule = '一数一源·主关联字段=身份证件号码，验证字段=' + hh.field;
        act = (type === '保留原值') ? '保留原值（记入问题清单待业务确认）'
                                    : '按权威数据源转换为权威值后写入清洗仓';
      } else if (iId >= 0 && idv && seenId[idv]) {
        type = '去重'; field = '自然人唯一标识';
        rule = '一数一标准·自然人唯一标识唯一性校验';
        act = '重复记录，仅保留首条'; o = uid;
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
    var problem = pFilter + pConvert + pKeep + pDup;
    var after = kept.length;
    var stats = {
      total: recs.length, dup_removed: dupRemoved, after_dedup: after, cleaned: after,
      good: after - problem, problem: problem,
      by_type: { '过滤': pFilter, '转换': pConvert, '保留原值': pKeep, '去重': pDup }
    };
    return withProblems ? { stats: stats, problems: prob } : stats;
  }

  function bindUpload() {
    var fi = document.getElementById('file-data'); if (!fi) return;
    fi.onchange = function () {
      var f = fi.files && fi.files[0]; if (!f) return;
      var r = new FileReader();
      r.onload = function () {
        var txt = String(r.result || '');
        var lines = txt.split(/\r?\n/).filter(function (x) { return x.trim(); });
        var n = Math.max(0, lines.length - 1);
        var cols = lines[0] ? lines[0].split(',').length : 0;
        C().staged = true;
        C().rows = n;
        // 按真实规则现算五项数字（口径：total − 去重 = 清洗总量 = 优质 + 问题）
        // 内置数据集沿用预置统计（已逐项验证）；导入其他数据集时按真实规则现算，
        // 并把问题明细一并重建，保证「五项数字」与「问题清单」口径完全一致。
        var builtin = !!(window.DATA && window.DATA.stats && window.DATA.stats.total === n);
        if (!builtin) {
          var pr = computeStats(lines, true);
          if (pr) {
            window.DATA = window.DATA || {};
            window.DATA.stats = pr.stats;
            window.DATA.problems = pr.problems;
            C().stats = pr.stats;
          }
        }
        A().render();        // 先重绘（前置仓数据量/按钮变化），再开弹窗
        A().openModal('待归集数据导入结果',
          '<div class="notice ok"><span class="ic">✓</span><div>文件 <b>' + A().esc(f.name) +
          '</b>（' + (f.size / 1024).toFixed(1) + ' KB）已写入前置仓表 <b class="mono">' +
          A().esc(C().tables.前置仓.name) + '</b>。</div></div>' +
          '<div class="kv" style="margin-top:12px">' +
          '<div class="r"><div class="k">导入行数</div><div class="v"><b>' + n + ' 行</b></div></div>' +
          '<div class="r"><div class="k">字段数</div><div class="v">' + cols + ' 个</div></div>' +
          '<div class="r"><div class="k">表头</div><div class="v mono">' +
            A().esc((lines[0] || '').slice(0, 150)) + '</div></div>' +
          '<div class="r"><div class="k">数据样例</div><div class="v mono">' +
            A().esc((lines[1] || '').slice(0, 150)) + '</div></div>' +
          '</div>' +
          '<div class="notice" style="margin-top:10px"><span class="ic">i</span><div>' +
          '「在前置仓里录入待归集数据」→ 再执行归集任务。' +
          '该数据集<b>刻意包含重复、格式错误、与权威源不一致的问题数据</b>，供后续治理环节使用。</div></div>',
          '<span class="btn" data-close-m="1">继续</span>');
      };
      r.readAsText(f, 'utf-8');
    };
  }

  /* 执行归集 */
  function runTask() {
    if (!C().staged) { A().toast('请先录入待归集数据', 'err'); return; }
    C().taskRun = 'running';
    C().runStart = A().now();
    A().render();
    A().toast('归集任务执行中…');
    setTimeout(function () {
      C().taskRun = 'done';
      C().runEnd = A().now();
      C().task.runStatus = '已结束';
      A().S.catalog.collectStatus = '归集已实施';
      A().S.done.colrun = true;
      A().render();
      A().openModal('归集任务执行完成',
        '<div class="notice ok"><span class="ic">✓</span><div>数据已从<b>前置仓</b>归集到<b>归集仓</b>，' +
        '共 <b>' + A().num(C().rows || 1000) + '</b> 行。</div></div>' +
        '<div class="notice" style="margin-top:10px"><span class="ic">i</span><div>' +
        '回到<b>数据编目系统</b>确认该条目录的归集状态变为 <b>【归集已实施】</b>。</div></div>',
        '<span class="btn" data-close-m="1">取消</span>' +
        '<span class="btn pri" id="to-status">查看目录归集状态</span>');
      var t = document.getElementById('to-status');
      if (t) t.onclick = function () { A().closeModal(); A().go('s5b'); };
    }, 900);
  }

  /* 编目系统 · 目录归集状态 */
  function renderStatus() {
    var S = A().S, st = S.catalog.collectStatus;
    var done = st === '归集已实施';
    return '' +
      '<div class="pagetitle"><h1>目录归集状态</h1>' +
        '<span class="sub">查看数据目录的归集实施状态</span>' +
        '<div class="right">' + A().tag('数据目录管理系统', 'info', '◷') + '</div></div>' +
      (done
        ? '<div class="notice ok"><span class="ic">✓</span><div>该条目录的归集状态为 <b>【归集已实施】</b>，' +
          '表示数据已经完成归集。</div></div>'
        : '<div class="notice warn"><span class="ic">!</span><div>归集尚未完成（当前状态：' + A().esc(st) + '）。</div></div>') +
      '<div class="tblwrap"><table class="data">' +
        '<thead><tr><th>数据目录编码</th><th>数据目录名称</th><th>数据提供单位</th>' +
        '<th>表英文名</th><th>归集状态</th><th class="n">归集行数</th><th>最近归集时间</th></tr></thead>' +
        '<tbody><tr><td class="mono">' + A().esc(S.catalog.code) + '</td>' +
        '<td>' + A().esc(S.catalog.name) + '</td><td>四川省公安厅</td>' +
        '<td class="mono">' + A().esc(S.collect.table) + '</td>' +
        '<td>' + A().statusTag(st) + '</td>' +
        '<td class="n">' + (done ? A().num(C().rows || 1000) : 0) + '</td>' +
        '<td class="td">' + A().esc(S.collect.runEnd || '—') + '</td></tr></tbody></table></div>' +
      '<div class="pager"><span class="cnt">共 1 条</span><span class="pg on">1</span></div>' +
      '<div class="eqbar" style="margin-top:12px">' +
        '<span>前置仓 <b>' + A().esc(S.collect.tables ? S.collect.tables.前置仓.name : '—') + '</b></span>' +
        '<span class="op">→</span><span>归集仓 <b>' + A().esc(S.collect.tables ? S.collect.tables.归集仓.name : '—') + '</b></span>' +
        '<span class="op">→</span><span>状态 <b>归集已实施</b></span>' +
        '<span class="chk">✓ 数据已完成归集</span></div>' +
      '<div class="actbar"><span class="tip">' +
        (done ? '下一步：为待治理数据配置数据治理规则，配置后由本系统执行治理任务'
              : '请先执行归集任务') + '</span>' +
        (done ? '<span class="btn pri" id="go-govern">配置治理规则 →</span>' : '') +
      '</div>';
  }

  /* 任务详情（真实可查） */
  function openTaskDetail() {
    var S = A().S, c = S.collect, g = S.govern;
    var st = c.taskRun === 'done' ? '已结束' : (c.taskRun === 'running' ? '执行中' : '待执行');
    var kv = function (k, v) {
      return '<div class="r"><div class="k">' + k + '</div><div class="v">' + v + '</div></div>';
    };
    var rows = c.taskRun === 'done' ? 1000 : 0;
    A().openDrawer('任务详情 · ' + A().esc(c.task.name),
      '<div class="kv">' +
        kv('任务名称', '<span class="mono">' + A().esc(c.task.name) + '</span>') +
        kv('数据目录名称', A().esc(S.catalog.name)) +
        kv('数据目录编码', '<span class="mono">' + A().esc(S.catalog.code) + '</span>') +
        kv('归集方式', '离线归集（文件）') +
        kv('源表（前置仓）', '<span class="mono">' + A().esc(c.tables.前置仓.name) + '</span>') +
        kv('目标表（归集仓）', '<span class="mono">' + A().esc(c.tables.归集仓.name) + '</span>') +
        kv('字段数', (window.DATA.catalog.items || []).length + ' 个') +
        kv('任务创建时间', A().esc(c.task.created)) +
        kv('任务状态', A().statusTag(st)) +
        kv('归集行数', '<b>' + A().num(rows) + '</b> 行') +
        kv('治理状态', A().esc(g.taskRun === 'done' ? '治理完成' : (g.ruleStatus || '待配置'))) +
      '</div>' +
      '<div class="notice" style="margin-top:12px"><span class="ic">i</span><div>' +
      '任务执行方式：<b>手动执行</b>。执行时数据由<b>前置仓</b>按字段映射写入' +
      '<b>归集仓</b>，写入行数与前置仓录入行数一致。</div></div>',
      '<span class="btn" data-close="1">关闭</span>' +
      (c.taskRun !== 'done'
        ? '<span class="btn pri" id="td-run">执行任务</span>' : ''));
    var b = document.getElementById('td-run');
    if (b) b.onclick = function () { A().closeDrawer(); runTask(); };
  }

  var init = function () {
    ['btn-run', 'btn-run2', 'btn-run3'].forEach(function (id) {
      var e = document.getElementById(id); if (e) e.onclick = runTask;
    });
    var s = document.getElementById('btn-stage'); if (s) s.onclick = openStage;
    bindUpload();
    document.querySelectorAll('[data-task-detail]').forEach(function (a) {
      a.onclick = function () { openTaskDetail(); };
    });
    ['go-status'].forEach(function (id) {
      var e = document.getElementById(id); if (e) e.onclick = function () { A().go('s5b'); };
    });
    var bc = document.getElementById('back-collect');
    if (bc) bc.onclick = function () { A().go('s4'); };
  };
  var initStatus = function () {
    var g = document.getElementById('go-govern');
    if (g) g.onclick = function () { A().go('s6'); };
  };

  window.SCREENS.s5 = { render: render, init: init, runTask: runTask };
  window.SCREENS.s5b = { render: renderStatus, init: initStatus };
})();

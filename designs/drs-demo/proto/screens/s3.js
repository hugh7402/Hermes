/* ==========================================================================
   屏3 · 数据归集工单
   ========================================================================== */
window.SCREENS = window.SCREENS || {};
(function () {
  'use strict';
  var A = function () { return window.APP; };

  function render() {
    var S = A().S, c = S.collect;
    var st = c.status === '未发起' ? '未发起' : (c.status === '审批中' ? '审批中' : '已通过');
    var rows = c.status === '未发起' ? '<tr><td colspan="9" class="t-center mut" style="padding:26px">' +
        '暂无归集工单。请先在【数据目录管理系统】的目录列表中，对已发布目录发起【归集】。</td></tr>' :
      '<tr>' +
        '<td class="mono">' + A().esc(c.orderNo) + '</td>' +
        '<td>' + A().esc(S.catalog.name) + '</td>' +
        '<td>四川省公安厅</td>' +
        '<td>' + A().esc(c.dock || '库表对接') + '</td>' +
        '<td class="mono">' + A().esc(c.table) + '</td>' +
        '<td>离线归集</td>' +
        '<td>' + A().statusTag(st) + '</td>' +
        '<td class="td">' + A().esc(c.submittedAt || '—') + '</td>' +
        '<td><div class="ops">' +
          (st === '审批中' ? '<a id="btn-appr">审核</a><span class="sep">|</span>' : '') +
          '<a data-view="1">查看</a></div></td></tr>';

    return '' +
      '<div class="pagetitle"><h1>数据归集工单</h1>' +
        '<span class="sub">工单审核通过后自动进入技术审核与归集确认环节</span>' +
        '<div class="right">' +
          (st === '已通过'
            ? '<span class="btn pri sm" id="go-sys">前往归集工单审核 →</span>' : '') +
        '</div></div>' +

      '<div class="kpis c4">' +
        '<div class="kpi"><div class="k-l">归集工单总数</div><div class="k-v">' +
          (c.status === '未发起' ? 0 : 1) + '<span class="k-u">件</span></div></div>' +
        '<div class="kpi k-warn"><div class="k-l">审批中</div><div class="k-v">' +
          (st === '审批中' ? 1 : 0) + '<span class="k-u">件</span></div></div>' +
        '<div class="kpi k-ok"><div class="k-l">已通过</div><div class="k-v">' +
          (st === '已通过' ? 1 : 0) + '<span class="k-u">件</span></div></div>' +
        '<div class="kpi"><div class="k-l">目录归集状态</div><div class="k-v" style="font-size:19px">' +
          A().esc(S.catalog.collectStatus) + '</div><div class="k-s">归集完成后变为「归集已实施」</div></div>' +
      '</div>' +

      '<div class="filters">' +
        '<div class="f"><label>归集工单编号</label><input class="inp" value="' + A().esc(c.orderNo) + '" readonly></div>' +
        '<div class="f"><label>工单状态</label><input class="inp" value="' + st + '" readonly></div>' +
        '<div class="f"><label>归集方式</label><input class="inp" value="离线归集" readonly></div>' +
        '<span class="btn sm pri">查询</span><span class="btn sm">重置</span>' +
      '</div>' +

      '<div class="tblwrap"><table class="data" id="tbl-wo">' +
        '<thead><tr><th>归集工单编号</th><th>数据目录名称</th><th>数据提供单位</th><th>归集方式</th>' +
        '<th>表英文名</th><th>归集方式</th><th>工单状态</th><th>提交时间</th>' +
        '<th style="width:110px">操作</th></tr></thead><tbody>' + rows + '</tbody></table></div>' +
      '<div class="pager"><span class="cnt">共 ' + (c.status === '未发起' ? 0 : 1) + ' 条</span>' +
        '<span class="pg on">1</span></div>' +

      (st === '已通过'
        ? '<div class="notice ok" style="margin-top:12px"><span class="ic">✓</span><div>' +
          '审批通过，工单已<b>进入技术审核环节</b>。下一步完成【技术审核】与【归集确认】。</div></div>'
        : st === '审批中'
        ? '<div class="notice warn" style="margin-top:12px"><span class="ic">◷</span><div>' +
          '工单状态为 <b>审批中</b>，进入【数据归集审批管理】点击【审核】完成审批。</div></div>'
        : '') +

      '<div class="actbar"><span class="tip">' +
        (st === '审批中' ? '点击【审核】→ 通过，工单将进入技术审核环节'
         : st === '已通过' ? '工单已进入技术审核环节'
         : '请先发起归集工单') + '</span>' +
        (st === '审批中' ? '<span class="btn pri" id="btn-appr2">审核</span>' : '') +
        (st === '已通过' ? '<span class="btn pri" id="go-sys2">前往归集工单审核 →</span>' : '') +
      '</div>';
  }

  function openApprove() {
    var c = A().S.collect;
    A().openDrawer('归集工单审核 · ' + c.orderNo,
      '<div class="kv">' +
        '<div class="r"><div class="k">归集工单编号</div><div class="v mono">' + A().esc(c.orderNo) + '</div></div>' +
        '<div class="r"><div class="k">数据目录名称</div><div class="v">' + A().esc(A().S.catalog.name) + '</div></div>' +
        '<div class="r"><div class="k">数据提供单位</div><div class="v">四川省公安厅</div></div>' +
        '<div class="r"><div class="k">归集方式</div><div class="v">' + A().esc(c.dock || '库表对接') + '</div></div>' +
        '<div class="r"><div class="k">表英文名</div><div class="v mono">' + A().esc(c.table) + '</div></div>' +
        '<div class="r"><div class="k">归集方式</div><div class="v">离线归集</div></div>' +
        '<div class="r"><div class="k">数据用途</div><div class="v">' + A().esc(c.usage || '') + '</div></div>' +
        '<div class="r"><div class="k">工单状态</div><div class="v">' + A().statusTag('审批中') + '</div></div>' +
      '</div>' +
      '<div class="panel" style="margin-top:12px"><div class="ph"><h3>审核意见</h3></div><div class="pb">' +
      '<div class="fi" id="fi-aop"><label><span class="req">*</span>审核意见</label>' +
      '<div class="ctl"><textarea id="aop" placeholder="请填写审核意见（不少于 10 字）">' +
      '归集信息完整，归集方式与表英文名符合命名规范，同意归集。</textarea></div>' +
      '<span class="msg">审核意见不少于 10 字</span></div></div></div>' +
      '<div class="notice" style="margin-top:12px"><span class="ic">i</span><div>' +
      '审核通过后，工单将<b>自动进入技术审核环节</b>。</div></div>',
      '<span class="btn" data-close="1">取消</span>' +
      '<span class="btn pri" id="appr-ok">审核通过</span>', true);
    var b = document.getElementById('appr-ok');
    if (b) b.onclick = function () {
      var op = ((document.getElementById('aop') || {}).value || '').trim();
      var fi = document.getElementById('fi-aop');
      if (op.length < 10) { if (fi) fi.classList.add('err'); A().toast('审核意见不少于 10 字', 'err'); return; }
      A().S.collect.status = '已通过';
      A().S.done.col = true;
      A().S.done.biz = true;
      A().S.collect.auditAt = A().now();
      A().S.collect.auditOpinion = op;
      A().closeDrawer();
      A().render();          // 必须先重绘再开弹窗，否则 render 会把刚开的弹窗覆盖掉
      A().openModal('工单已流转',
        '<div class="notice ok"><span class="ic">✓</span><div>归集工单 <b>' + A().esc(A().S.collect.orderNo) +
        '</b> 审核通过，已<b>进入技术审核环节</b>。</div></div>' +
        '<div class="mut sm" style="margin-top:10px">下一步：完成技术审核与归集确认，系统将根据工单自动建表。</div>',
        '<span class="btn" data-close-m="1">取消</span>' +
        '<span class="btn pri" id="go-sys-m">前往归集工单审核</span>');
      var g = document.getElementById('go-sys-m');
      if (g) g.onclick = function () { A().closeModal(); A().go('s4'); };
    };
  }

  var init = function () {
    ['btn-appr', 'btn-appr2'].forEach(function (id) {
      var e = document.getElementById(id); if (e) e.onclick = openApprove;
    });
    ['go-sys', 'go-sys2'].forEach(function (id) {
      var e = document.getElementById(id); if (e) e.onclick = function () { A().go('s4'); };
    });
    document.querySelectorAll('[data-view]').forEach(function (a) {
      a.onclick = function () {
        var c = A().S.collect;
        var kv = function (k, v) {
          return '<div class="r"><div class="k">' + k + '</div><div class="v">' + v + '</div></div>';
        };
        A().openDrawer('数据归集工单详情 · ' + A().esc(c.orderNo),
          '<div class="kv">' +
            kv('归集工单编号', '<span class="mono">' + A().esc(c.orderNo) + '</span>') +
            kv('数据目录名称', A().esc(A().S.catalog.name)) +
            kv('数据目录编码', '<span class="mono">' + A().esc(A().S.catalog.code) + '</span>') +
            kv('数据提供单位', A().esc(A().S.catalog.org || '四川省公安厅')) +
            kv('归集方式', A().esc(c.dock || '库表对接')) +
            kv('表英文名', '<span class="mono">' + A().esc(c.table) + '</span>') +
            kv('数据用途', A().esc(c.usage || '—')) +
            kv('工单状态', A().statusTag(c.status || '未发起')) +
            kv('提交时间', A().esc(c.submittedAt || '—')) +
            kv('业务审核时间', A().esc(c.auditAt || '—')) +
            kv('业务审核意见', A().esc(c.auditOpinion || '—')) +
          '</div>' +
          '<div class="panel" style="margin-top:12px"><div class="ph"><h3>工单字段映射</h3>' +
          '<span class="meta">' + (window.DATA.fields || []).length + ' 个字段</span></div>' +
          '<div class="pb"><div class="tblwrap"><table class="data"><thead><tr>' +
          '<th class="c">序号</th><th>字段中文名</th><th>字段英文名</th><th>数据类型</th>' +
          '<th class="c">主键</th></tr></thead><tbody>' +
          (window.DATA.fields || []).slice(0, 20).map(function (f, i) {
            return '<tr><td class="c">' + (i + 1) + '</td><td>' + A().esc(f.cn || '') + '</td>' +
              '<td class="mono">' + A().esc(f.en || '') + '</td><td>' + A().esc(f.type || '') +
              '</td><td class="c">' + A().esc(f.pk || '否') + '</td></tr>';
          }).join('') + '</tbody></table></div></div></div>',
          '<span class="btn" data-close="1">关闭</span>');
      };
    });
  };

  window.SCREENS.s3 = { render: render, init: init, openApprove: openApprove };
  window.SCREENS.s3b = window.SCREENS.s3;   // 同一张单，两个入口
})();

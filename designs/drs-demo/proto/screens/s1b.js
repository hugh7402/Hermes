/* ==========================================================================
   屏1b · 数据目录列表
   ========================================================================== */
window.SCREENS = window.SCREENS || {};
(function () {
  'use strict';
  var A = function () { return window.APP; };

  /* 列表来自目录集合（手工新增 / 数据目录导入均会累积在此） */
  function catRows() {
    var S = A().S;
    return S.catalogs.map(function (c) {
      var n = (c.items && c.items.length) ? c.items.length : (window.DATA.catalog.items || []).length;
      return { code: c.code, name: c.name, org: c.org || '四川省公安厅',
               domain: c.domain || '民生保障', level: c.level || '省级', items: n,
               share: c.share || '有条件共享', status: c.status,
               collect: c.collectStatus || '未归集', method: c.method || '手工新增',
               active: c === S.catalog, rec: c };
    });
  }

  function render() {
    var rows0 = catRows();
    var st = (A().S.catalog && A().S.catalog.status) || '待审核';
    var rs = rows0.length ? rows0.map(function (r) {
      var collA = r.status === '已发布'
        ? (r.active ? '<a id="btn-collect">创建归集任务工单</a>'
                    : '<a data-coll="' + A().esc(r.code) + '">创建归集任务工单</a>')
        : '<a class="mut" title="目录未发布，不能创建归集任务工单">创建归集任务工单</a>';
      return '<tr>' +
        '<td class="mono">' + A().esc(r.code) + '</td>' +
        '<td><a data-view="1">' + A().esc(r.name) + '</a></td>' +
        '<td>' + A().esc(r.org) + '</td><td>' + A().esc(r.domain) + '</td>' +
        '<td class="c">' + A().esc(r.level) + '</td>' +
        '<td class="n">' + r.items + '</td>' +
        '<td>' + A().esc(r.method) + '</td>' +
        '<td>' + A().statusTag(r.share) + '</td>' +
        '<td>' + A().statusTag(r.status) + '</td>' +
        '<td>' + A().statusTag(r.collect) + '</td>' +
        '<td><div class="ops">' + collA + '<span class="sep">|</span>' +
          '<a data-view="1">查看</a><span class="sep">|</span>' +
          '<a class="mut">变更</a></div></td></tr>';
    }).join('') : '<tr><td colspan="11" class="t-center mut" style="padding:26px">' +
        '暂无数据目录。请点击右上角【新增目录】手工编目，或使用【数据目录导入】批量导入。</td></tr>';

    return '' +
      '<div class="pagetitle"><h1>数据目录管理</h1>' +
        '<span class="sub">基于已发布目录创建数据归集任务工单</span>' +
        '<div class="right"><span class="btn sm" id="btn-new">＋ 新增目录</span></div></div>' +

      (st !== '已发布'
        ? '<div class="notice warn"><span class="ic">!</span><div>当前目录状态为 <b>' + st +
          '</b>，需审核通过并发布后才能发起归集。</div></div>'
        : '<div class="notice ok"><span class="ic">✓</span><div>目录已发布，可基于该目录发起数据归集任务。</div></div>') +

      '<div class="filters">' +
        '<div class="f"><label>数据目录名称</label><input class="inp" placeholder="请输入"></div>' +
        '<div class="f"><label>数据提供单位</label><input class="inp" value="四川省公安厅" readonly></div>' +
        '<div class="f"><label>目录状态</label><input class="inp" value="' + st + '" readonly></div>' +
        '<span class="btn sm pri" style="margin-left:6px">查询</span>' +
        '<span class="btn sm">重置</span>' +
        '<span class="toggle" id="ftoggle">展开 ▾</span>' +
        '<div class="more f"><label>数据所属领域</label><input class="inp" placeholder="请选择"></div>' +
        '<div class="more f"><label>共享属性</label><input class="inp" placeholder="请选择"></div>' +
        '<div class="more f"><label>归集状态</label><input class="inp" value="' + A().S.catalog.collectStatus + '" readonly></div>' +
      '</div>' +

      '<div class="tblwrap"><table class="data" id="tbl-cat">' +
        '<thead><tr><th style="min-width:210px">数据目录编码</th><th>数据目录名称</th><th>数据提供单位</th>' +
        '<th>数据所属领域</th><th class="c">数据所在层级</th><th class="n">数据项数</th>' +
        '<th>来源方式</th><th>共享属性</th><th>目录状态</th><th>归集状态</th>' +
        '<th style="width:190px">操作</th></tr></thead>' +
        '<tbody>' + rs + '</tbody></table></div>' +
      '<div class="pager"><span class="cnt">共 ' + rows0.length + ' 条</span>' +
        '<span class="pg" disabled>‹</span><span class="pg on">1</span><span class="pg">›</span></div>' +

      '<div class="actbar"><span class="tip">目录发布后，在列表【操作】列点击 <b>创建归集任务工单</b> 发起归集</span>' +
        (st === '已发布' ? '<span class="btn pri" id="btn-collect2">创建归集任务工单</span>' : '') +
        (A().S.collect.status !== '未发起'
          ? '<span class="btn" id="go-orders">查看数据归集工单 →</span>' : '') + '</div>';
  }

  /* 归集信息填报表单（归集方式 / 表英文名 / 数据用途） */
  function openCollect() {
    var S = A().S;
    if (S.catalog.status !== '已发布') { A().toast('目录未发布，不能发起归集', 'err'); return; }
    var body =
      '<div class="notice"><span class="ic">i</span><div>为目录 <b>' + A().esc(S.catalog.name) +
      '</b> 创建归集任务工单。提交后工单进入审核，<b>审核通过后自动流转到数据归集管理系统</b>。</div></div>' +
      '<div class="fgrid c2">' +
        '<div class="fi"><label>数据目录名称</label><div class="ctl ro"><span>' +
          A().esc(S.catalog.name) + '</span></div></div>' +
        '<div class="fi"><label>数据目录编码</label><div class="ctl ro"><span class="mono">' +
          A().esc(S.catalog.code) + '</span></div></div>' +
        '<div class="fi" id="fi-dock"><label><span class="req">*</span>访问方式</label>' +
          '<div class="ctl"><select id="c-dock">' +
            ['库表对接', '接口对接', '文件对接'].map(function (v) {
              return '<option' + (v === '库表对接' ? ' selected' : '') + '>' + v + '</option>'; }).join('') +
          '</select></div><span class="msg">必填</span></div>' +
        '<div class="fi" id="fi-table"><label><span class="req">*</span>表英文名</label>' +
          '<div class="ctl"><input id="c-table" value="db_natural_person_base"></div>' +
          '<span class="tl">归集后系统将以该名称自动创建前置仓表与归集仓表</span>' +
          '<span class="msg">必填，且只能由字母、数字、下划线组成</span></div>' +
        '<div class="fi span2" id="dock-cfg-wrap"><label>归集接入配置</label>' +
          '<div id="dock-cfg"></div></div>' +
        '<div class="fi span2" id="fi-usage"><label><span class="req">*</span>数据用途</label>' +
          '<div class="ctl"><textarea id="c-usage">用于自然人身份信息核验、政务服务事项材料免提交，支撑一网通办。</textarea></div>' +
          '<span class="msg">必填，不少于 10 字</span></div>' +
        '<div class="fi"><label>数据提供单位</label><div class="ctl ro"><span>四川省公安厅</span></div></div>' +
        '<div class="fi"><label>归集方式</label><div class="ctl ro"><span id="sync-mode">实时归集（库表直连）</span></div></div>' +
      '</div>' +
      '<div class="panel" style="margin-top:12px"><div class="ph"><h3>归集工单流转路径</h3></div><div class="pb">' +
      '<div class="tl">' +
        (function () {
          var c = A().S.collect;
          // 未走到的节点置灰；进行中的节点高亮
          var n1 = c.status !== '未发起';                 // 已创建工单
          var n2 = c.status === '已通过';                  // 业务审核通过
          var n3 = !!c.confirmAudit;                       // 归集确认完成
          var cur = !n1 ? 1 : (!n2 ? 2 : (!n3 ? 3 : 0));
          var cls = function (i, done) {
            return 'ti' + (done ? ' done' : '') + (cur === i ? ' now' : (done ? '' : ' todo'));
          };
          var mark = function (i, done) {
            return '<div class="tt">' + (done ? '✓ ' : (cur === i ? '◷ ' : '○ ')) + '' ;
          };
          return [
            { i: 1, d: n1, t: '数据目录管理系统 · 创建归集任务工单',
              s: n1 ? '已完成：工单 ' + A().esc(c.orderNo) + ' 已创建（状态：审批中）' : '未开始：在目录列表点【创建归集任务工单】' },
            { i: 2, d: n2, t: '数据目录管理系统 · 业务审核归集工单',
              s: n2 ? '已完成：' + A().esc(c.auditAt || '已审核') + ' 审核通过' : '未开始：业务审核通过后流转至数据归集管理系统' },
            { i: 3, d: n3, t: '数据归集管理系统 · 技术审核 + 归集确认',
              s: n3 ? '已完成：自动建表并自动创建归集任务' : '未开始：技术审核通过后自动建表、自动创建归集任务' }
          ].map(function (x) {
            return '<div class="' + cls(x.i, x.d) + '"><div class="tt">' +
              (x.d ? '✓ ' : (cur === x.i ? '◷ ' : '○ ')) + A().esc(x.t) + '</div>' +
              '<div class="td">' + A().esc(x.s) + '</div></div>';
          }).join('');
        })() +
      '</div></div></div>';
    /* 归集方式不同 → 后续接入配置不同（真实分支） */
    function applyDock() {
      var box = document.getElementById('dock-cfg'); if (!box) return;
      var v = (document.getElementById('c-dock') || {}).value || '库表对接';
      var F = 'background:#fff;';
      /* 归集方式随访问方式联动（文件对接=离线归集，库表/接口=实时归集） */
      var sm = document.getElementById('sync-mode');
      if (sm) {
        sm.textContent = v === '文件对接' ? '离线归集'
          : (v === '接口对接' ? '实时归集（接口拉取）' : '实时归集（库表直连）');
      }
      if (v === '库表对接') {
        box.innerHTML = '<div class="fgrid c2" style="' + F + '">' +
          '<div class="fi"><label><span class="req">*</span>数据库类型</label><div class="ctl">' +
            '<select id="d-type"><option>Oracle</option><option>MySQL</option>' +
            '<option>PostgreSQL</option><option>达梦 DM</option><option>人大金仓 KingBase</option>' +
            '</select></div></div>' +
          '<div class="fi"><label><span class="req">*</span>主机地址</label>' +
            '<div class="ctl"><input id="d-host" value="10.212.8.31"></div></div>' +
          '<div class="fi"><label><span class="req">*</span>端口</label>' +
            '<div class="ctl"><input id="d-port" value="1521"></div></div>' +
          '<div class="fi"><label><span class="req">*</span>数据库名 / 服务名</label>' +
            '<div class="ctl"><input id="d-db" value="PERSONDB"></div></div>' +
          '<div class="fi"><label>Schema</label>' +
            '<div class="ctl"><input id="d-schema" value="GA_RK"></div></div>' +
          '<div class="fi"><label><span class="req">*</span>连接账号</label>' +
            '<div class="ctl"><input id="d-user" value="drs_collect"></div></div>' +
          '<div class="fi"><label>密码</label>' +
            '<div class="ctl"><input id="d-pwd" type="password" value="********"></div></div>' +
          '</div>' +
          '<div class="row" style="margin-top:8px"><span class="btn sm" id="d-test">测试连接</span>' +
          '<span class="mut sm">库表对接：系统按连接信息直连业务库抽取数据，需保证网络可达与只读权限</span></div>';
      } else if (v === '接口对接') {
        box.innerHTML = '<div class="fgrid c2" style="' + F + '">' +
          '<div class="fi"><label><span class="req">*</span>接口地址</label>' +
            '<div class="ctl"><input id="d-url" value="https://api.scga.gov.cn/drs/v1/person/list"></div></div>' +
          '<div class="fi"><label><span class="req">*</span>请求方式</label>' +
            '<div class="ctl"><select id="d-method"><option>GET</option><option>POST</option></select></div></div>' +
          '<div class="fi"><label><span class="req">*</span>认证方式</label>' +
            '<div class="ctl"><select id="d-auth"><option>Bearer Token</option><option>AK/SK 签名</option>' +
            '<option>OAuth2.0 客户端凭证</option></select></div></div>' +
          '<div class="fi"><label>Token / 密钥</label>' +
            '<div class="ctl"><input id="d-token" type="password" value="********"></div></div>' +
          '<div class="fi"><label>分页参数</label>' +
            '<div class="ctl"><input id="d-page" value="pageNo=1&amp;pageSize=500"></div></div>' +
          '<div class="fi"><label>数据格式</label>' +
            '<div class="ctl"><select id="d-fmt"><option>JSON</option><option>XML</option></select></div></div>' +
          '</div>' +
          '<div class="row" style="margin-top:8px"><span class="btn sm" id="d-test">测试连通</span>' +
          '<span class="mut sm">接口对接：系统按接口协议拉取数据，需保证接口鉴权信息有效</span></div>';
      } else {
        box.innerHTML = '<div style="' + F + 'padding:10px 12px;border:1px solid var(--bd);' +
          'border-radius:var(--r)">' +
          '<div class="row"><span class="btn sm" id="d-pick">📎 选择离线数据文件</span>' +
          '<input type="file" id="d-file" accept=".csv,.txt" style="display:none">' +
          '<span class="mut sm" id="d-file-name">未选择文件（.csv，须与数据项字段一致）</span></div>' +
          '<div class="mut sm" style="margin-top:8px">文件对接：工单审核通过后，在【离线归集任务】中' +
          '录入该文件到前置仓，再执行归集写入归集仓。</div></div>';
        var pk = document.getElementById('d-pick'), df = document.getElementById('d-file');
        if (pk) pk.onclick = function () { df.click(); };
        if (df) df.onchange = function () {
          var f = df.files && df.files[0]; if (!f) return;
          A().S.collect.fileName = f.name;
          var nm = document.getElementById('d-file-name');
          if (nm) nm.textContent = '已选择：' + f.name + '（' + (f.size / 1024).toFixed(1) + ' KB）';
        };
      }
      var t = document.getElementById('d-test');
      if (t) t.onclick = function () {
        A().toast((v === '接口对接' ? '接口连通性测试通过' : '数据库连接测试通过') +
          '（' + v + '）', 'ok');
      };
    }

    A().openDrawer('发起数据归集任务', body,
      '<span class="btn" data-close="1">取消</span>' +
      '<span class="btn" id="c-save">保存草稿</span>' +
      '<span class="btn pri" id="c-submit">提交</span>', true);

    /* 访问方式 → 接入配置 & 归集方式联动：抽屉渲染完成后才能拿到 #c-dock */
    var dk0 = document.getElementById('c-dock');
    if (dk0) { dk0.onchange = applyDock; applyDock(); }

    var sv = document.getElementById('c-save');
    if (sv) sv.onclick = function () { A().toast('归集工单已保存草稿', 'ok'); };
    var sb = document.getElementById('c-submit');
    if (sb) sb.onclick = function () {
      var dock = (document.getElementById('c-dock') || {}).value || '';
      var tb = ((document.getElementById('c-table') || {}).value || '').trim();
      var us = ((document.getElementById('c-usage') || {}).value || '').trim();
      var bad = false;
      var mark = function (id, on) {
        var e = document.getElementById('fi-' + id); if (e) e.classList.toggle('err', on); return on; };
      bad = mark('dock', !dock) | bad;
      bad = mark('table', !tb || !/^[A-Za-z][A-Za-z0-9_]*$/.test(tb)) | bad;
      bad = mark('usage', us.length < 10) | bad;
      if (bad) { A().toast('请修正标红的必填项', 'err'); return; }
      var S2 = A().S;
      S2.collect.status = '审批中';
      S2.collect.table = tb;
      S2.collect.dock = dock;
      S2.collect.usage = us;
      S2.collect.submittedAt = A().now();
      S2.catalog.collectStatus = '归集中';
      S2.done.col = true;
      A().closeDrawer();
      A().render();          // 先重绘（进度条/列表状态更新），否则 render 会把刚开的弹窗覆盖掉
      A().openModal('归集工单已提交',
        '<div class="notice ok"><span class="ic">✓</span><div>归集工单 <b>' + A().esc(S2.collect.orderNo) +
        '</b> 已提交审核，在【数据归集工单】列表中状态为 <b>审批中</b>。</div></div>' +
        '<div class="kv" style="margin-top:12px">' +
        '<div class="r"><div class="k">归集方式</div><div class="v">' + A().esc(dock) + '</div></div>' +
        '<div class="r"><div class="k">表英文名</div><div class="v mono">' + A().esc(tb) + '</div></div>' +
        '<div class="r"><div class="k">数据用途</div><div class="v">' + A().esc(us) + '</div></div>' +
        '<div class="r"><div class="k">工单状态</div><div class="v">' + A().statusTag('审批中') + '</div></div>' +
        '</div>',
        '<span class="btn" data-close-m="1">取消</span>' +
        '<span class="btn pri" id="go-wo">查看数据归集工单</span>');
      var g = document.getElementById('go-wo');
      if (g) g.onclick = function () { A().closeModal(); A().go('s3'); };
    };
  }

  var init = function () {
    ['btn-collect', 'btn-collect2'].forEach(function (id) {
      var e = document.getElementById(id); if (e) e.onclick = openCollect;
    });
    // 其他已发布目录的【归集】：先切为当前操作目录，再发起
    document.querySelectorAll('[data-coll]').forEach(function (a) {
      a.onclick = function () {
        var code = a.getAttribute('data-coll');
        A().S.catalogs.forEach(function (c) { if (c.code === code) { A().S.catalog = c; } });
        A().render();
        var b = document.getElementById('btn-collect');
        if (b) { b.click(); }
      };
    });
    var b = document.getElementById('btn-new');
    if (b) b.onclick = function () { A().go('s1'); };
    document.querySelectorAll('[data-view]').forEach(function (a) {
      a.onclick = function () {
        var rows = catRows();
        var tr = a.closest ? a.closest('tr') : null;
        var code = tr ? (tr.querySelector('td') || {}).textContent : '';
        var r = rows.filter(function (x) { return x.code === (code || '').trim(); })[0] || rows[0];
        if (!r) { return; }
        var c = r.rec, flds = (c.items && c.items.length) ? c.items : (window.DATA.fields || []);
        var kv = function (k, v) {
          return '<div class="r"><div class="k">' + k + '</div><div class="v">' + v + '</div></div>';
        };
        A().openDrawer('数据目录详情 · ' + A().esc(c.name),
          '<div class="kv">' +
            kv('数据目录编码', '<span class="mono">' + A().esc(c.code) + '</span>') +
            kv('数据目录名称', A().esc(c.name)) +
            kv('数据提供单位', A().esc(c.org || '四川省公安厅')) +
            kv('数据所属领域', A().esc(c.domain || '民生保障')) +
            kv('数据所在层级', A().esc(c.level || '省级')) +
            kv('数据摘要', A().esc(c.summary || '—')) +
            kv('数据来源系统', A().esc(c.source || '—')) +
            kv('目录来源方式', A().esc(c.method || '手工新增')) +
            kv('目录状态', A().statusTag(c.status)) +
            kv('归集状态', A().statusTag(c.collectStatus || '未归集')) +
            kv('提交时间', A().esc(c.submitAt || '—')) +
            kv('数据项数量', '<b>' + flds.length + '</b> 项') +
          '</div>' +
          '<div class="panel" style="margin-top:12px"><div class="ph"><h3>数据项清单</h3>' +
          '<span class="meta">共 ' + flds.length + ' 项</span></div><div class="pb">' +
          '<div class="tblwrap"><table class="data"><thead><tr><th class="c">序号</th>' +
          '<th>数据项中文名称</th><th>英文名称</th><th>数据类型</th><th class="c">主键</th>' +
          '</tr></thead><tbody>' + flds.slice(0, 20).map(function (f, i) {
            var cn = f.cn || f.name || '', en = f.en || '', tp = f.type || '',
                pk = f.pk || (f.pk === '是' ? '是' : '否');
            return '<tr><td class="c">' + (i + 1) + '</td><td>' + A().esc(cn) + '</td>' +
              '<td class="mono">' + A().esc(en) + '</td><td>' + A().esc(tp) + '</td>' +
              '<td class="c">' + A().esc(pk) + '</td></tr>';
          }).join('') + '</tbody></table></div></div></div>',
          '<span class="btn" data-close="1">关闭</span>', true);
      };
    });
    var ft = document.getElementById('ftoggle');
    if (ft) ft.onclick = function () {
      var f = ft.parentNode; f.classList.toggle('open');
      ft.textContent = f.classList.contains('open') ? '收起 ▴' : '展开 ▾';
    };
    var dk = document.getElementById('c-dock');
    if (dk) { dk.onchange = applyDock; if (typeof applyDock === 'function') { applyDock(); } }
    var g = document.getElementById('go-orders');
    if (g) g.onclick = function () { A().go('s3'); };
  };

  window.SCREENS.s1b = { render: render, init: init, openCollect: openCollect };
})();

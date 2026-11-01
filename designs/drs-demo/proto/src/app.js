/* ==========================================================================
   应用骨架：状态机 + 两系统外壳 + 路由
   系统一 数据目录管理系统 —— 政务数据目录的编目、审核与发布
   系统二 数据归集管理系统 —— 数据归集与数据治理
   两个系统在顶部系统导航行切换（真实系统导航方式）
   ========================================================================== */
(function () {
  'use strict';

  /* ── 两个系统与各自模块 ──────────────────────────────────── */
  var SYSTEMS = {
    catalog: {
      key: 'catalog', name: '数据目录管理系统', home: 's1b',
      org: '四川省人民政府 · 四川省公安厅',
      side: [
        { g: '数据目录管理' },
        { k: 's1', t: '新增政务数据目录', ic: '▪' },
        { k: 's2', t: '数据目录审批管理', ic: '▪', badge: 'auto' },
        { k: 's1b', t: '数据目录列表', ic: '▪' },
        { g: '归集任务工单' },
        { k: 's3b', t: '数据归集工单', ic: '▪', badge: 'auto' },
        { k: 's5b', t: '目录归集状态', ic: '▪' }
      ]
    },
    collect: {
      key: 'collect', name: '数据归集管理系统', home: 's4',
      org: '四川省人民政府 · 四川省大数据中心',
      side: [
        { g: '归集工单审核' },
        { k: 's4', t: '待技术审核', ic: '▪', badge: 'auto' },
        { k: 's4b', t: '已办结', ic: '▪' },
        { g: '归集库表' },
        { k: 's4c', t: '前置数据库', ic: '▪' },
        { k: 's4d', t: '归集数据库', ic: '▪' },
        { g: '归集任务' },
        { k: 's5', t: '离线归集任务', ic: '▪' },
        { g: '数据治理' },
        { k: 's6', t: '数据治理规则配置', ic: '▪' },
        { k: 's6b', t: '治理规则配置审批', ic: '▪', badge: 'auto' },
        { k: 's7', t: '治理任务管理', ic: '▪' },
        { k: 's7b', t: '任务实例运维管理', ic: '▪' },
        { g: '问题与成效' },
        { k: 's7c', t: '数据清洗结果明细', ic: '▪' },
        { k: 's8', t: '治理成效总览', ic: '▪' }
      ]
    }
  };

  /* ── 版本号（界脚显示，便于评审核对版本）──────────────────── */
  var VERSION = 'V3.1';

  /* ── 业务进度条：两个系统各一段（真实系统能力）─────────────── */
  var LIFECYCLE = {
    // 数据目录管理系统 —— 编目 + 创建/业务审核归集任务工单（对应 215）
    catalog: {
      label: '编目与归集申请流程：',
      steps: [
        { k: 'cat', t: '编目填报' },
        { k: 'audit', t: '审核发布' },
        { k: 'pub', t: '已发布' },
        { k: 'col', t: '创建归集工单' },
        { k: 'biz', t: '业务审核' },
        { k: 'colrun', t: '归集已实施' }
      ]
    },
    // 数据归集管理系统 —— 技术审核、建表、归集、治理（对应 216）
    collect: {
      label: '归集与治理流程：',
      steps: [
        { k: 'tech', t: '技术审核' },
        { k: 'table', t: '自动建表' },
        { k: 'colrun', t: '归集已实施' },
        { k: 'gconf', t: '治理规则' },
        { k: 'grun', t: '治理完成' }
      ]
    }
  };

  /* ── 屏幕 → 元信息（面包屑 / 所属系统 / 进度条位置 / 左菜单&导航高亮）── */
  var META = {
    // ——— 数据目录管理系统 ———
    s1:  { sys: 'catalog', menu: 's1',  crumb: ['数据目录管理', '新增政务数据目录'],  title: '新增政务数据目录', stage: 'cat' },
    s1b: { sys: 'catalog', menu: 's1b', crumb: ['数据目录管理', '数据目录列表'],      title: '数据目录管理', stage: 'pub' },
    s2:  { sys: 'catalog', menu: 's2',  crumb: ['我的审批工单', '数据目录审批管理'],  title: '数据目录审批管理', stage: 'audit' },
    // ——— 数据归集管理系统 ———
    s3:  { sys: 'catalog',  menu: 's3b', crumb: ['归集任务工单', '归集工单业务审核'], title: '归集工单业务审核', stage: 'biz' },
    s3b: { sys: 'catalog',  menu: 's3b', crumb: ['归集任务工单', '数据归集工单'],       title: '数据归集工单', stage: 'col' },
    s5b: { sys: 'catalog',  menu: 's5b', crumb: ['归集任务工单', '目录归集状态'],       title: '目录归集状态', stage: 'colrun' },
    s4:  { sys: 'collect',  menu: 's4',  crumb: ['归集工单审核', '待技术审核'],         title: '归集工单审核 · 待技术审核', stage: 'tech' },
    s4b: { sys: 'collect',  menu: 's4b', crumb: ['归集工单审核', '已办结'],             title: '归集工单审核 · 已办结', stage: 'table' },
    s4c: { sys: 'collect',  menu: 's4c', crumb: ['归集库表', '前置数据库'],             title: '前置数据库', stage: 'table' },
    s4d: { sys: 'collect',  menu: 's4d', crumb: ['归集库表', '归集数据库'],             title: '归集数据库', stage: 'table' },
    s5:  { sys: 'collect',   menu: 's5',  crumb: ['离线归集任务', '任务列表'],            title: '离线归集任务', stage: 'colrun' },
    s6:  { sys: 'collect',   menu: 's6',  crumb: ['数据治理配置中心', '数据治理规则配置'], title: '数据治理规则配置', stage: 'gconf' },
    s6b: { sys: 'collect',   menu: 's6b', crumb: ['数据治理配置中心', '规则配置审批管理'], title: '数据治理规则配置审批管理', stage: 'gconf' },
    s7:  { sys: 'collect',    menu: 's7',  crumb: ['数据治理任务治理', '治理任务管理'],    title: '治理任务管理', stage: 'grun' },
    s7b: { sys: 'collect',   menu: 's7b', crumb: ['监控运维中心', '任务实例运维管理'],    title: '任务实例运维管理', stage: 'grun' },
    s7c: { sys: 'collect',  menu: 's7c', crumb: ['统一问题工单', '数据清洗结果明细'],    title: '数据清洗结果明细', stage: 'grun' },
    s8:  { sys: 'collect', menu: 's8',  crumb: ['监控运维大屏', '治理成效总览'],        title: '治理成效总览', stage: 'grun' }
  };

  /* ── 角色（姓名一律脱敏显示）─────────────────────────────── */
  // 姓名一律脱敏显示
  // 角色 = 真实业务岗位，名称互不相同才能看出「谁在办哪一步」
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

  /* ── 工具函数 ─────────────────────────────────────────────── */
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function tag(text, kind, icon) {
    return '<span class="tag ' + (kind || 'mute') + '">' +
           (icon ? '<span class="dot i">' + esc(icon) + '</span>' : '<span class="dot"></span>') +
           esc(text) + '</span>';
  }
  // 状态 → 标签样式/图标（不靠颜色单传信息：文字 + 图标冗余）
  var TAGMAP = {
    '已发布': ['ok', '✓'], '已通过': ['ok', '✓'], '已完成': ['ok', '✓'], '已结束': ['ok', '✓'],
    '归集已实施': ['ok', '✓'], '已启用': ['ok', '✓'], '已上线': ['ok', '✓'], '优质数据': ['ok', '✓'],
    '审批中': ['warn', '◷'], '审核中': ['warn', '◷'], '待审核': ['warn', '◷'],
    '待处理': ['warn', '◷'], '待执行': ['warn', '◷'], '待配置': ['warn', '◷'],
    '待上线': ['warn', '◷'], '有问题': ['danger', '!'], '不予共享': ['danger', '✕'],
    '执行中': ['info', '▸'], '草稿': ['mute', '○']
  };
  function statusTag(s) {
    var m = TAGMAP[s];
    return m ? tag(s, m[0], m[1]) : tag(s, 'mute', '○');
  }
  function now() {
    var d = new Date();
    function p(n) { return (n < 10 ? '0' : '') + n; }
    return d.getFullYear() + '-' + p(d.getMonth() + 1) + '-' + p(d.getDate()) + ' ' +
           p(d.getHours()) + ':' + p(d.getMinutes()) + ':' + p(d.getSeconds());
  }
  function today() { return now().slice(0, 10); }
  /* 在给定时刻上加 n 毫秒（用于自动建表等分步执行的耗时展示） */
  function plusMs(ts, ms) {
    var m = String(ts).match(/^(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2}):(\d{2})$/);
    if (!m) { return ts; }
    var d = new Date(+m[1], +m[2] - 1, +m[3], +m[4], +m[5], +m[6]);
    d = new Date(d.getTime() + ms);
    var p = function (x) { return (x < 10 ? '0' : '') + x; };
    return d.getFullYear() + '-' + p(d.getMonth() + 1) + '-' + p(d.getDate()) + ' ' +
           p(d.getHours()) + ':' + p(d.getMinutes()) + ':' + p(d.getSeconds());
  }

  /* n 天前的时刻（用于表示「既有表」的创建时间） */
  function fsDays(n) {
    var d = new Date(Date.now() - n * 86400000), p = function (x) { return (x < 10 ? '0' : '') + x; };
    return d.getFullYear() + '-' + p(d.getMonth() + 1) + '-' + p(d.getDate()) + ' ' +
           p(d.getHours()) + ':' + p(d.getMinutes()) + ':' + p(d.getSeconds());
  }
  function num(n) { return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ','); }

  /* ── 全局状态 ─────────────────────────────────────────────── */
  /* ── 数据目录集合 ──────────────────────────────────────────────
     真实系统行为：目录可不断建立（手工编目 / 文件导入），逐条独立审核发布；
     任一条发布后均可发起归集并走完治理流程。
     S.catalogs = 全部目录；S.catalog = 当前操作的目录（下游各屏沿用该引用）。 */
  var SEED_CATALOG = {
    code: 'R510000TAB' + today().replace(/-/g, '') + '00000001',
    name: '四川省自然人基本登记信息',
    org: '四川省公安厅',
    summary: '自然人的基础身份信息，包括姓名、性别、出生日期、民族、国籍等，是自然人身份识别的基础数据。',
    source: '四川省人口基础信息库',
    domain: '民生保障', level: '省级', share: '有条件共享',
    status: '已发布', published: true, collectStatus: '未归集',
    method: '手工新增', items: [], vals: {},
    audits: [{ node: '审核', role: '目录审核员', user: '李**',
               time: now(), opinion: '目录要素完整、属性填写规范，同意发布。' }],
    submitAt: now(), createdAt: now()
  };

  var S = {
    role: null,              // 当前办理角色（显式指定）
    sys: 'catalog',
    screen: 's1',
    catalogs: [SEED_CATALOG],
    catalog: SEED_CATALOG,
    seq: 1,
    collect: {
      // 前置仓（ODS）为既有库表：默认已存在表且数据已先行落地
      staged: true, stagedAt: fsDays(3), rows: 1000,
      orderNo: 'GJ' + today().replace(/-/g, '') + '0007',
      table: 'db_natural_person_base',
      status: '未发起',
      techAudit: null,
      confirmAudit: null,
      tables: null,
      task: null
    },
    govern: {
      ruleStatus: '待配置',
      rules: [],
      source: null,
      taskStatus: null,
      taskRun: null
    },
    // 各节点完成状态（业务进度条用）
    done: { cat: false, audit: false, pub: false, col: false, biz: false,
            tech: false, table: false, colrun: false, gconf: false, grun: false }
  };
  /* ── 目录集合操作（真实系统行为）────────────────────────────── */
  function newCatalogCode() {
    S.seq += 1;
    return 'R510000TAB' + today().replace(/-/g, '') + ('0000000' + S.seq).slice(-8);
  }

  /* 新建一条目录并设为当前操作目录；返回该目录 */
  function addCatalog(rec) {
    rec = rec || {};
    var c = {
      code: rec.code || newCatalogCode(),
      name: rec.name || '未命名数据目录',
      org: rec.org || '四川省公安厅',
      summary: rec.summary || '',
      source: rec.source || '暂无系统',
      domain: rec.domain || '民生保障',
      level: rec.level || '省级',
      share: rec.share || '有条件共享',
      status: rec.status || '待审核',
      published: false,
      collectStatus: '未归集',
      method: rec.method || '手工新增',
      items: rec.items || [],
      vals: rec.vals || {},
      audits: [],
      createdAt: now(),
      submitAt: rec.submitAt || now()
    };
    S.catalogs.push(c);
    S.catalog = c;
    return c;
  }

  function pendingCatalogs() {
    return S.catalogs.filter(function (c) { return c.status === '待审核'; });
  }
  function publishedCatalogs() {
    return S.catalogs.filter(function (c) { return c.status === '已发布'; });
  }
  /* 按要素名称取字段编号 —— 要素编号是内部编号（补录字段可能是 55/56），
     绝不能按显示顺序硬编码，否则会取错列。 */
  function idxOf(label) {
    var found = null;
    (window.FORM_SPEC || []).forEach(function (g) {
      (g.fields || []).forEach(function (f) {
        if (String(f.label).trim() === String(label).trim()) { found = f.idx; }
      });
    });
    return found;
  }

  /* 左侧菜单角标：按真实待办数显示 */
  function autoBadge(menu) {
    if (menu === 's2') return pendingCatalogs().length;
    if (menu === 's3b') return S.collect.status === '审批中' ? 1 : 0;
    if (menu === 's4') return (S.collect.status === '已通过' && !S.collect.confirmAudit) ? 1 : 0;
    if (menu === 's6b') return S.govern.ruleStatus === '审核中' ? 1 : 0;
    return 0;
  }


  /* ── 浏览器内解析 xlsx（零依赖：ZIP 目录 + DecompressionStream + DOMParser）──
     xlsx 就是 ZIP；只需支持 stored(0) 与 deflate(8)，Chrome 原生即可解压。 */
  function unzipEntries(buf) {
    var dv = new DataView(buf), u8 = new Uint8Array(buf), out = [], p = -1, i;
    for (i = buf.byteLength - 22; i >= 0 && i > buf.byteLength - 66000; i--) {
      if (dv.getUint32(i, true) === 0x06054b50) { p = i; break; }
    }
    if (p < 0) throw new Error('不是有效的 xlsx 文件（未找到 ZIP 目录）');
    var n = dv.getUint16(p + 10, true), off = dv.getUint32(p + 16, true);
    for (var k = 0; k < n; k++) {
      if (dv.getUint32(off, true) !== 0x02014b50) { break; }
      var method = dv.getUint16(off + 10, true);
      var csize = dv.getUint32(off + 20, true);
      var nlen = dv.getUint16(off + 28, true);
      var elen = dv.getUint16(off + 30, true);
      var clen = dv.getUint16(off + 32, true);
      var lho = dv.getUint32(off + 42, true);
      var name = new TextDecoder().decode(u8.subarray(off + 46, off + 46 + nlen));
      var lnlen = dv.getUint16(lho + 26, true), lelen = dv.getUint16(lho + 28, true);
      var st = lho + 30 + lnlen + lelen;
      out.push({ name: name, method: method, data: u8.subarray(st, st + csize) });
      off += 46 + nlen + elen + clen;
    }
    return out;
  }

  function entryText(buf, name) {
    var e = unzipEntries(buf).filter(function (x) { return x.name === name; })[0];
    if (!e) return Promise.resolve(null);
    if (e.method === 0) return Promise.resolve(new TextDecoder().decode(e.data));
    if (typeof DecompressionStream === 'undefined') {
      return Promise.reject(new Error('当前浏览器不支持解压，请使用 Chrome / Edge 打开'));
    }
    var st = new Blob([e.data]).stream().pipeThrough(new DecompressionStream('deflate-raw'));
    return new Response(st).text();
  }

  function sheetRows(xml, shared) {
    var doc = new DOMParser().parseFromString(xml, 'application/xml');
    var out = [], rl = doc.getElementsByTagName('row'), i, j, q;
    for (i = 0; i < rl.length; i++) {
      var row = [], cl = rl[i].getElementsByTagName('c');
      for (j = 0; j < cl.length; j++) {
        var c = cl[j], ref = c.getAttribute('r') || '', col = 0, m = ref.match(/^[A-Z]+/);
        if (m) { for (q = 0; q < m[0].length; q++) { col = col * 26 + (m[0].charCodeAt(q) - 64); } col -= 1; }
        var typ = c.getAttribute('t'), v = c.getElementsByTagName('v')[0], val = '';
        if (typ === 's' && v) { val = shared[parseInt(v.textContent, 10)] || ''; }
        else if (typ === 'inlineStr') {
          var is = c.getElementsByTagName('is')[0]; val = is ? is.textContent : '';
        } else if (v) { val = v.textContent; }
        row[col] = val;
      }
      out.push(row);
    }
    return out;
  }

  /* 读 xlsx 的全部工作表 —— 返回 [[[cell,...],...], ...] */
  function xlsxSheets(buf) {
    return entryText(buf, 'xl/sharedStrings.xml').then(function (ss) {
      var shared = [];
      if (ss) {
        var d = new DOMParser().parseFromString(ss, 'application/xml');
        var si = d.getElementsByTagName('si');
        for (var i = 0; i < si.length; i++) {
          var ts = si[i].getElementsByTagName('t'), s = '';
          for (var j = 0; j < ts.length; j++) { s += ts[j].textContent; }
          shared.push(s);
        }
      }
      var names = unzipEntries(buf).map(function (x) { return x.name; })
        .filter(function (n) { return /^xl\/worksheets\/sheet\d+\.xml$/.test(n); })
        .sort(function (a, b) {
          return parseInt(a.replace(/\D+/g, ''), 10) - parseInt(b.replace(/\D+/g, ''), 10);
        });
      if (!names.length) throw new Error('文件中未找到工作表');
      return Promise.all(names.map(function (n) { return entryText(buf, n); }))
        .then(function (xs) { return xs.map(function (x) { return x ? sheetRows(x, shared) : []; }); });
    });
  }

  window.S = S;

  /* ── 外壳渲染 ─────────────────────────────────────────────── */
  function renderTopbar(sys) {
    return '' +
      '<div class="topbar">' +
        '<div class="emblem"></div>' +
        '<div class="brand"><b>四川省一体化数据资源管理系统</b></div>' +
        '<div class="spacer"></div>' +
        '<div class="usertools">' +
          '<a>无障碍浏览</a><a>长者版</a><a>繁體</a><a>使用帮助</a>' +
          '<span class="who">' +
            '<b id="who-user">李**</b> · ' +
            '<span class="roledrop" id="btn-role" title="切换角色">' +
            '<span id="who-role">目录审核员</span><span class="cd">▾</span></span></span>' +
          '<a>退出</a>' +
        '</div>' +
      '</div>';
  }

  /* 系统导航行 —— 两个系统在此切换（真实系统导航方式，无专门切换按钮） */
  function renderSysNav(activeSys) {
    var h = '<div class="sysnav"><span class="sn-label">系统：</span>';
    for (var k in SYSTEMS) {
      h += '<span class="sn' + (k === activeSys ? ' on' : '') + '" data-sys="' + k + '">' +
           '<i class="dot"></i>' + esc(SYSTEMS[k].name) +
           (k === activeSys ? '<span class="cur">当前</span>' : '') + '</span>';
    }
    return h + '</div>';
  }

  function renderPipeline(sysKey, stage) {
    var flow = LIFECYCLE[sysKey] || LIFECYCLE.catalog;
    var steps = flow.steps;
    var idx = steps.findIndex(function (x) { return x.k === stage; });
    return '<div class="pipeline"><span class="pl-label">' + esc(flow.label) + '</span>' +
      steps.map(function (x, i) {
        var cls = S.done[x.k] ? 'done' : (i === idx ? 'now' : '');
        var mark = S.done[x.k] ? '✓' : String(i + 1);
        return '<span class="st ' + cls + '" data-stage="' + x.k + '"><i>' + mark + '</i>' + esc(x.t) + '</span>' +
               (i < steps.length - 1 ? '<span class="arw"></span>' : '');
      }).join('') + '</div>';
  }

  function renderSide(sys, active) {
    var h = '';
    sys.side.forEach(function (m) {
      if (m.g) { h += '<div class="grp">' + esc(m.g) + '</div>'; return; }
      var bd = m.badge === 'auto' ? autoBadge(m.k) : m.badge;
      h += '<div class="mi' + (m.k === active ? ' on' : '') + '" data-menu="' + m.k + '">' +
           '<span class="ic">' + esc(m.ic || '·') + '</span>' +
           '<span class="tx">' + esc(m.t) + '</span>' +
           (bd ? '<span class="bdg">' + bd + '</span>' : '') + '</div>';
    });
    return h;
  }

  /* 主渲染 */
  function render() {
    var meta = META[S.screen] || META.s1;
    var sys = SYSTEMS[meta.sys];
    S.sys = meta.sys;

    document.getElementById('root').innerHTML =
      renderTopbar(sys) +
      renderSysNav(meta.sys) +
      renderPipeline(meta.sys, meta.stage) +
      '<div class="wrap">' +
        '<div class="side">' + renderSide(sys, meta.menu) + '</div>' +
        (function () {
          var sp = splitActbar(screenHtml());
          return '<div class="main"' + (roleAllowed() ? '' : ' data-gated="1"') + '>' +
            '<div class="mainscroll">' +
              '<div class="crumb">当前位置：<b>' + esc(meta.crumb[0]) + '</b> &gt; <b>' + esc(meta.crumb[1]) + '</b></div>' +
              roleBar() +
              '<div class="screen on" id="screen-' + S.screen + '">' + sp.body + '</div>' +
            '</div>' +
            (sp.foot ? '<div class="mainfoot">' + sp.foot + '</div>' : '') +
          '</div>';
        })() +
      '</div>' +
      renderFooter() +
      '<div class="scrim" id="scrim"></div>' +
      '<div class="drawer" id="drawer"><div class="dh"><h3 id="drawer-title">详情</h3>' +
        '<span class="x" id="drawer-x">✕</span></div>' +
        '<div class="db" id="drawer-body"></div><div class="df" id="drawer-foot"></div></div>' +
      '<div class="modal" id="modal"><div class="mh" id="modal-title">提示</div>' +
        '<div class="mb" id="modal-body"></div><div class="mf" id="modal-foot"></div></div>' +
      '<div class="toast" id="toast"></div>' +
      '<div class="dbgbox" id="dbgbox" style="display:none">' +
        '<div class="dbgh">调试信息<span class="dbgcopy" id="dbgcopy">复制</span></div>' +
        '<div id="dbgtxt">把鼠标移到任意元素上，点击即可锁定并复制</div>' +
        '<textarea id="dbgraw" readonly rows="3" style="display:none;width:100%;box-sizing:border-box;' +
          'margin:0;padding:7px 12px;border:0;border-top:1px solid #24323f;resize:vertical;' +
          'background:#0a121a;color:#9fd0f0;font:11px/1.5 monospace"></textarea>' +
      '</div>';

    /* 受限标记同时挂到 body：抽屉/弹窗在 .main 之外，靠它才能覆盖到 */
    if (roleAllowed()) { document.body.removeAttribute('data-gated'); }
    else { document.body.setAttribute('data-gated', '1'); }
    markViewActs();
    bindShell();
    var wu = document.getElementById('who-user'), wr = document.getElementById('who-role');
    var wo = document.getElementById('who-org');
    var _rk = roleCurrent();
    var r = ROLES[_rk] || ROLES.editor;
    if (wu) wu.textContent = r.name;
    if (wr) wr.textContent = r.role.split('（')[0];
    if (wo) wo.textContent = r.org;
    var _br = document.getElementById('btn-role');
    if (_br) {
      _br.classList.toggle('deny', !roleAllowed());
      _br.onclick = openRoleSwitch;
    }
    var _bf = document.getElementById('btn-role-fix');
    if (_bf) { _bf.onclick = function () { setRole(roleFor(S.screen)); }; }
    // 调试面板在每次重绘后重新接线
    var cp2 = document.getElementById('dbgcopy');
    if (cp2) cp2.onclick = window.__dbgCopy;
    var box2 = document.getElementById('dbgbox');
    if (box2) box2.style.display = dbg ? 'block' : 'none';
    var sc = window.SCREENS[S.screen];
    if (sc && sc.init) sc.init();
    if (typeof window.AFTER_RENDER === 'function') window.AFTER_RENDER();
  }

  /* 屏幕渲染分发：支持 function 与 {render,init} 两种注册形态 */
  function screenHtml() {
    var sc = window.SCREENS[S.screen];
    if (!sc) return '<div class="notice warn"><span class="ic">!</span><div>' +
      '<div>该模块暂未开放。</div></div></div>';
    return typeof sc === 'function' ? sc() : sc.render();
  }

  /* 把屏幕 HTML 末尾的操作条抽出来 —— 放到滚动区之外，避免压住内容 */
  function splitActbar(html) {
    var i = html.lastIndexOf('<div class="actbar">');
    if (i < 0) return { body: html, foot: '' };
    return { body: html.slice(0, i), foot: html.slice(i) };
  }

  /* 当前屏幕该用哪个角色 */
  function roleFor(sc) {
    if (sc === 's1' || sc === 's1b' || sc === 's5b') return 'editor';
    if (sc === 's2') return 'audit1';
    if (sc === 's3' || sc === 's3b') return 'biz';          // 归集工单创建与业务审核（目录系统）
    if (sc === 's4' || sc === 's4b' || sc === 's4c' || sc === 's4d' || sc === 's5') return 'collect';
    return 'govern';
  }

  /* 当前办理角色：显式指定，未指定时取初始环节角色 */
  function roleCurrent() {
    return (S.role && ROLES[S.role]) ? S.role : 'editor';
  }

  /* 当前角色是否具备本环节办理权限 */
  function roleAllowed() {
    return roleCurrent() === roleFor(S.screen);
  }

  /* 底部功能区 —— 国办发〔2017〕47号要求列明项（用流转文本行，不用一堆 span）*/
  function renderFooter() {
    return '<div class="footer">' +
      '<span class="fk">党政机关网站标识</span>·' +
      '<span class="fk">政府网站标识码：XXXXXXXXXX</span>·' +
      '<span class="fk"><a>ICP备案编号：XXXXXXXX号</a></span>·' +
      '<span class="fk"><a>公安机关备案标识：XXXXXXXXXXXXX号</a></span>·' +
      '<span class="fk">网站主办单位：四川省大数据中心</span>·' +
      '<span class="fk">联系电话：028-XXXXXXXX</span>·' +
      '<span class="fk"><a>站点地图</a></span>' +
      '<span class="ver">版本 ' + VERSION + '</span>' +
      '</div>';
  }

  /* ── 事件绑定 ─────────────────────────────────────────────── */
  function bindShell() {
    // 输入即清错：字段被修正后自动去掉红色错误态（否则出现「值已合法但仍标红」）
    if (!window.__errClearBound) {
      window.__errClearBound = true;
      var clr = function (e) {
        var t = e.target;
        if (!t || !t.closest) return;
        var fi = t.closest('.fi.err');
        if (fi) fi.classList.remove('err');
      };
      document.addEventListener('input', clr, true);
      document.addEventListener('change', clr, true);
    }
    document.querySelectorAll('[data-menu]').forEach(function (el) {
      el.onclick = function () { go(el.getAttribute('data-menu')); };
    });
    document.querySelectorAll('[data-sys]').forEach(function (el) {
      el.onclick = function () {
        var k = el.getAttribute('data-sys');
        var target = (SYSTEMS[k] && SYSTEMS[k].home) || 's1b';
        go(target);
      };
    });
    document.querySelectorAll('[data-stage]').forEach(function (el) {
      el.onclick = function () { toast(el.textContent); };
    });
    var x = document.getElementById('drawer-x'); if (x) x.onclick = closeDrawer;
    var sc = document.getElementById('scrim'); if (sc) sc.onclick = function () { closeDrawer(); closeModal(); };
  }

  /* ── 路由 ─────────────────────────────────────────────────── */
  /* 权限门：当前角色无本环节办理权限时，阻断操作并提示在右上角切换角色 */
  function roleBar() {
    if (roleAllowed()) { return ''; }
    var need = roleFor(S.screen), n = ROLES[need], cur = ROLES[roleCurrent()];
    return '<div class="rolebar"><span class="ic">✕</span>' +
      '<span>本环节须由「<b>' + esc(n.role) + '</b>（' + esc(n.name) + ' · ' + esc(n.org) +
      '）」办理；当前角色「' + esc(cur.role) + '」无该权限，无法继续操作。' +
      '请在右上角切换为「' + esc(n.role) + '」后继续。</span>' +
      '<span class="btn sm pri" id="btn-role-fix">切换为' + esc(n.role) + '</span></div>';
  }

  /* 被权限门管控的办理动作选择器 */
  var GATED_SEL = '.mainfoot .btn, .screen .actbar .btn, #modal-foot .btn, #drawer-foot .btn';

  /* 权限门豁免：查看 / 导出 / 跳转 / 取消类动作不挡 —— 真实系统里查看与办理是分离的权限 */
  var VIEW_ACT_IDS = {
    'btn-cancel': 1, 'back-cat': 1, 'back-collect': 1,
    'btn-export': 1, 'btn-export2': 1, 'p-export': 1,
    'go-inst': 1, 'go-clean': 1, 'go-clean2': 1, 'go-summary': 1,
    'go-src': 1, 'go-task': 1, 'go-task2': 1, 'to-task': 1
  };
  var VIEW_ACT_RE = /^(查看|导出|下载|查询|重置|返回|取消|关闭|展开|前往|预览|详情|明细|打印)/;
  function isViewAct(el) {
    if (!el || !el.tagName) { return false; }
    if (el.id === 'btn-role-fix') { return true; }
    if (el.id && VIEW_ACT_IDS[el.id]) { return true; }
    return VIEW_ACT_RE.test((el.innerText || el.textContent || '').trim());
  }
  /* 给豁免按钮打标记，视觉灰化随之豁免（不加则出现「看着被禁其实能用」的矛盾） */
  function markViewActs() {
    [].slice.call(document.querySelectorAll(GATED_SEL)).forEach(function (el) {
      if (isViewAct(el)) { el.classList.add('vg'); }
      else { el.classList.remove('vg'); }
    });
  }

  /* 权限门：无办理权限时点击办理动作，给出明确反馈（而不是毫无反应） */
  document.addEventListener('click', function (e) {
    if (roleAllowed()) { return; }
    var el = e.target && e.target.closest ? e.target.closest(GATED_SEL) : null;
    if (!el || isViewAct(el)) { return; }   /* 查看类不拦，只拦办理 */
    e.preventDefault();
    e.stopPropagation();
    var need = ROLES[roleFor(S.screen)];
    toast('当前角色无本环节办理权限，请在右上角切换为「' + need.role + '」', 'warn');
  }, true);

  /* 轻量角色切换：只更新顶栏与权限门，不重绘屏幕内容（避免冲掉已打开的弹窗/抽屉） */
  function setRoleSoft(k) {
    if (!ROLES[k] || S.role === k) { return; }
    S.role = k;
    var r = ROLES[k];
    var wu = document.getElementById('who-user'), wr = document.getElementById('who-role');
    var wo = document.getElementById('who-org');
    if (wu) { wu.textContent = r.name; }
    if (wr) { wr.textContent = r.role.split('（')[0]; }
    if (wo) { wo.textContent = r.org; }
    var m = document.querySelector('.main');
    if (m) {
      if (roleAllowed()) { m.removeAttribute('data-gated'); }
      else { m.setAttribute('data-gated', '1'); }
    }
    if (roleAllowed()) { document.body.removeAttribute('data-gated'); }
    else { document.body.setAttribute('data-gated', '1'); }
    markViewActs();
    var br = document.getElementById('btn-role');
    if (br) { br.classList.toggle('deny', !roleAllowed()); }
    var bar = document.querySelector('.rolebar');
    if (bar && roleAllowed()) { bar.parentNode.removeChild(bar); }
  }

  /* 切换办理角色（角色未变化时不重绘，避免冲掉已打开的弹窗/抽屉） */
  function setRole(k) {
    if (!ROLES[k] || S.role === k) { return; }
    S.role = k;
    var r = ROLES[k];
    render();
    toast('已切换为「' + r.role + ' · ' + r.name + '」', 'ok');
  }

  /* 切换角色面板 */
  function openRoleSwitch() {
    var cur = roleCurrent();
    var need = roleFor(S.screen);
    var order = ROLE_ORDER.slice();
    if (order.indexOf(need) > 0) {                 // 本环节所需角色排到最前
      order.splice(order.indexOf(need), 1);
      order.unshift(need);
    }
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
      '<span class="btn" data-close="1">取消</span>');
    document.getElementById('modal').classList.add('rolepanel');
    document.querySelectorAll('.rolelist .rl').forEach(function (el) {
      el.onclick = function () { closeModal(); setRole(el.getAttribute('data-role')); };
    });

  }

  /* ── 路由：每屏一个拼音首字母路径（模拟真实系统地址）─────────────
     只在 http(s) 下生效；file:// 打开时 pushState 会抛异常，已捕获忽略。 */
  var ROUTES = {
    's1': 'xzzwsjml',
    's1b': 'sjmllb',
    's2': 'sjmlspgl',
    's3': 'gjgdywsh',
    's3b': 'sjgjgd',
    's4': 'gjgdsh/djs',
    's4b': 'gjgdsh/ybj',
    's4c': 'qzsjk',
    's4d': 'gjsjk',
    's5': 'lxgjrw',
    's5b': 'mlgjzt',
    's6': 'sjzlgzpz',
    's6b': 'gzpzspgl',
    's7': 'zlrwgl',
    's7b': 'rwslywgl',
    's7c': 'sjqxjgmx',
    's8': 'zlcxzl',
  };
  var ROUTES_REV = (function () {
    var r = {}; for (var k in ROUTES) { r[ROUTES[k]] = k; } return r;
  })();
  function routeOf(sc) { return '/' + (ROUTES[sc] || ''); }
  function screenOfPath(p) {
    var s = String(p || '').replace(/^\/+|\/+$/g, '');
    if (!s) { return null; }
    if (ROUTES_REV[s]) { return ROUTES_REV[s]; }
    if (/^s[0-9][a-z]?$/i.test(s) && window.SCREENS && window.SCREENS[s.toLowerCase()]) {
      return s.toLowerCase();          /* 也允许直接写屏号，如 /s7c */
    }
    return null;
  }
  function pushRoute(sc) {
    try {
      if (location.protocol === 'file:') { return; }
      var p = routeOf(sc);
      if (location.pathname !== p) { history.pushState({ sc: sc }, '', p); }
    } catch (e) { /* 不支持 pushState 的环境忽略即可 */ }
  }

  function go(sc, noPush) {
    if (!META[sc]) { toast('该模块暂未开放'); return; }
    var prev = S.screen;
    S.screen = sc;
    if (!noPush) { pushRoute(sc); }
    var obj = window.SCREENS[sc];
    // 进入「新」屏幕时才重置屏内状态（筛选/分页等）——否则每次渲染都会被重置
    if (prev !== sc && obj && obj.enter) obj.enter();
    render();
    var m = document.querySelector('.mainscroll'); if (m) m.scrollTop = 0;
  }

  /* ── 抽屉 / 弹窗 / toast ─────────────────────────────────── */
  function openDrawer(title, html, footHtml, wide) {
    var d = document.getElementById('drawer');
    document.getElementById('drawer-title').textContent = title;
    document.getElementById('drawer-body').innerHTML = html;
    document.getElementById('drawer-foot').innerHTML = footHtml || '<span class="btn" data-close="1">关闭</span>';
    d.className = 'drawer' + (wide ? ' wide' : '');
    requestAnimationFrame(function () {
      d.classList.add('on');
      document.getElementById('scrim').classList.add('on');
    });
    document.querySelectorAll('[data-close]').forEach(function (el) {
      el.onclick = function () { closeDrawer(); };
    });
    if (typeof window.AFTER_DRAWER === 'function') window.AFTER_DRAWER();
    markViewActs();
  }
  function closeDrawer() {
    var d = document.getElementById('drawer'); if (!d) return;
    d.classList.remove('on');
    document.getElementById('scrim').classList.remove('on');
  }
  function openModal(title, body, foot) {
    document.getElementById('modal-title').textContent = title;
    document.getElementById('modal-body').innerHTML = body;
    document.getElementById('modal-foot').innerHTML = foot || '<span class="btn pri" data-close-m="1">确定</span>';
    document.getElementById('modal').classList.add('on');
    document.getElementById('scrim').classList.add('on');
    document.querySelectorAll('[data-close-m]').forEach(function (el) {
      el.onclick = function () { closeModal(); };
    });
    if (typeof window.AFTER_MODAL === 'function') window.AFTER_MODAL();
    markViewActs();
  }
  function closeModal() {
    document.getElementById('modal').classList.remove('rolepanel');
    var m = document.getElementById('modal'); if (!m) return;
    m.classList.remove('on');
    if (!document.getElementById('drawer').classList.contains('on'))
      document.getElementById('scrim').classList.remove('on');
  }
  var toastTimer = null;
  function toast(text, kind) {
    var t = document.getElementById('toast'); if (!t) return;
    t.textContent = text;
    // 抽屉打开时把 toast 挪到「剩余可见区域」的中央，否则会压在抽屉上
    var d = document.getElementById('drawer');
    var open = d && d.classList.contains('on');
    if (open) {
      var dw = d.getBoundingClientRect().width || 0;
      t.style.left = Math.max(140, Math.round((window.innerWidth - dw) / 2)) + 'px';
      t.style.bottom = '132px';        // 抬高，避开吸底操作条
    } else {
      t.style.left = '50%';
      t.style.bottom = '76px';
    }
    t.className = 'toast on' + (kind ? ' ' + kind : '');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { t.className = 'toast'; }, 2600);
  }

  /* ── 调试开关（Ctrl+D / Cmd+D）───────────────────────────────
     悬停任意元素 → 右下角浮出定位信息；
     ★ 点击该元素即可「锁定并自动复制」，不会触发系统本身的功能；
       锁定后鼠标随便移动，面板信息不再变化，可从容点【复制】或按 C 再复制；
     Esc 解锁；再按 Ctrl+D 关闭调试模式。对外使用时默认关闭。 */
  var dbg = false, dbgLast = null, dbgPin = null;

  /* 报告用的 class 必须剔掉调试自身加的高亮类 */
  function cleanCls(cn) {
    return (typeof cn === 'string' ? cn : '')
             .replace(/\bdbgout\b/g, '').replace(/\bdbgpin\b/g, '').trim();
  }
  function cssPath(el) {
    var parts = [];
    while (el && el.nodeType === 1 && parts.length < 7) {
      var s = el.tagName.toLowerCase();
      if (el.id) { parts.unshift(s + '#' + el.id); break; }
      var cls = cleanCls(el.className).split(/\s+/).filter(Boolean).slice(0, 2);
      if (cls.length) s += '.' + cls.join('.');
      var p = el.parentElement;
      if (p) {
        var sib = Array.prototype.filter.call(p.children, function (x) { return x.tagName === el.tagName; });
        if (sib.length > 1) s += ':nth-of-type(' + (sib.indexOf(el) + 1) + ')';
      }
      parts.unshift(s);
      el = p;
    }
    return parts.join(' > ');
  }
  function dbgInfo(el) {
    if (!el || el.nodeType !== 1) return null;
    return {
      screen: S.screen, sys: S.sys, tag: el.tagName.toLowerCase(),
      id: el.id || '(无)',
      cls: cleanCls(el.className) || '(无)',
      path: cssPath(el),
      text: (el.innerText || el.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 60)
    };
  }
  function dbgRender(el) {
    var box = document.getElementById('dbgtxt'); if (!box) return;
    var i = dbgInfo(el);
    if (!i) { box.textContent = '把鼠标移到任意元素上，点击即可锁定并复制'; return; }
    box.innerHTML =
      '<div class="dbgr"><b>屏</b>' + esc(i.screen) + '　<b>系统</b>' + esc(i.sys) +
        (dbgPin ? '　<span class="dbglock">已锁定</span>' : '') + '</div>' +
      '<div class="dbgr"><b>元素</b>' + esc(i.tag) + '</div>' +
      '<div class="dbgr"><b>id</b>' + esc(i.id) + '</div>' +
      '<div class="dbgr"><b>class</b>' + esc(i.cls) + '</div>' +
      '<div class="dbgr"><b>选择器</b><span class="dbgsel">' + esc(i.path) + '</span></div>' +
      '<div class="dbgr"><b>文本</b>' + esc(i.text) + '</div>' +
      '<div class="dbghint">' +
        (dbgPin ? '已锁定，鼠标移动不影响本面板　按 <b>Esc</b> 解锁'
                : '点击元素＝锁定并复制　按 <b>C</b> 复制当前　<b>Esc</b> 解锁') +
      '</div>';
  }
  function dbgText() {
    var i = dbgInfo(dbgPin || dbgLast);
    if (!i) return null;
    var NL = String.fromCharCode(10);   // 用字符码构造换行，避免反斜杠转义在各层被吞
    return '屏 ' + i.screen + '｜系统 ' + i.sys + '｜元素 ' + i.tag +
           '｜id ' + i.id + '｜class ' + i.cls + NL +
           '选择器 ' + i.path + NL +
           '文本 ' + i.text;
  }
  function dbgCopy(quiet) {
    var txt = dbgText();
    if (!txt) { toast('请先把鼠标移到要反馈的元素上，或点击该元素'); return false; }
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(txt);
    } catch (err) { /* 降级：下方 select 可手动复制 */ }
    // 兜底：把文本塞进面板里的只读输入框，剪贴板 API 受限时可手动 Ctrl+C
    var ta = document.getElementById('dbgraw');
    if (ta) { ta.value = txt; ta.style.display = 'block'; }
    if (!quiet) toast(dbgPin ? '已复制（已锁定元素）' : '已复制当前元素', 'ok');
    return true;
  }
  window.__dbgCopy = function (e) { if (e) e.stopPropagation(); dbgCopy(); };
  function dbgLock(el) {
    if (!el || el.nodeType !== 1) return;
    if (dbgLast) dbgLast.classList.remove('dbgout');
    dbgPin = el;
    el.classList.add('dbgpin');
    dbgRender(el);
  }
  function dbgUnlock(quiet) {
    if (dbgPin) dbgPin.classList.remove('dbgpin');
    dbgPin = null;
    if (dbgLast) { dbgLast.classList.remove('dbgout'); dbgLast = null; }
    if (!quiet) toast('已解锁，可继续选取元素');
    dbgRender(null);
  }
  function toggleDebug(force) {
    dbg = (typeof force === 'boolean') ? force : !dbg;
    var box = document.getElementById('dbgbox');
    if (box) box.style.display = dbg ? 'block' : 'none';
    document.body.style.cursor = dbg ? 'crosshair' : '';
    dbgUnlock(true);
    var ta = document.getElementById('dbgraw'); if (ta) ta.style.display = 'none';
    if (dbg) dbgRender(null);
    toast(dbg ? '调试模式已开启：悬停查看，点击元素即锁定并复制（Ctrl+D 关闭）'
              : '调试模式已关闭', dbg ? 'ok' : '');
  }
  document.addEventListener('keydown', function (e) {
    if ((e.ctrlKey || e.metaKey) && (e.key === 'd' || e.key === 'D')) {
      e.preventDefault(); toggleDebug(); return;
    }
    if (!dbg) return;
    var t = e.target, inField = t && /^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName);
    if (e.key === 'Escape') { e.preventDefault(); dbgUnlock(); return; }
    if (!inField && (e.key === 'c' || e.key === 'C') && !e.ctrlKey && !e.metaKey) {
      e.preventDefault(); dbgCopy();
    }
  });
  document.addEventListener('mousemove', function (e) {
    if (!dbg) return;
    if (dbgPin) return;                       // 已锁定：鼠标移动不再改面板
    var el = e.target;
    if (el === dbgLast) return;
    if (dbgLast) dbgLast.classList.remove('dbgout');
    if (el && el.nodeType === 1 && !(el.closest && el.closest('#dbgbox'))) {
      el.classList.add('dbgout'); dbgLast = el;
    }
    dbgRender(el);
  }, true);
  /* 点击元素＝锁定并自动复制，且不触发系统本身功能 */
  document.addEventListener('click', function (e) {
    if (!dbg) return;
    if (e.target && e.target.closest && e.target.closest('#dbgbox')) return;  // 面板自身照常
    e.preventDefault(); e.stopPropagation();
    dbgLock(e.target);
    dbgCopy(true);
    toast('已锁定并复制该元素（Esc 解锁，未执行该元素功能）', 'ok');
  }, true);

  /* ── 导出（供自动化验证与调试）────────────────────────────── */
  window.APP = {
    setRole: function (k) { setRole(k); },
    setRoleSoft: function (k) { setRoleSoft(k); },
    roleFor: function (sc) { return roleFor(sc); },
    roleCurrent: function () { return roleCurrent(); },
    S: S, go: go, render: render, SYSTEMS: SYSTEMS, VERSION: VERSION, LIFECYCLE: LIFECYCLE,
    addCatalog: addCatalog, newCatalogCode: newCatalogCode,
    today: today, now: now, fsDays: fsDays, plusMs: plusMs, xlsxSheets: xlsxSheets, idxOf: idxOf,
    pendingCatalogs: pendingCatalogs, publishedCatalogs: publishedCatalogs,
    META: META, SCREENS: (window.SCREENS = window.SCREENS || {}),
    openDrawer: openDrawer, closeDrawer: closeDrawer,
    openModal: openModal, closeModal: closeModal, toast: toast,
    toggleDebug: toggleDebug, isDebug: function () { return dbg; },
    toggleDebug: toggleDebug, debug: function () { return dbg; },
    esc: esc, tag: tag, statusTag: statusTag, now: now, today: today, num: num,
    ROLES: ROLES, LIFECYCLE: LIFECYCLE,
    get screen() { return S.screen; },
    get sys() { return S.sys; }
  };
  window.__proto = window.APP;   // 兼容 skill 约定的测试接口名

  /* ── 启动 ─────────────────────────────────────────────────── */
  document.addEventListener('DOMContentLoaded', function () {
    if (!document.getElementById('root')) {
      var d = document.createElement('div'); d.id = 'root'; document.body.appendChild(d);
    }
    /* 地址栏带有效路由时按它定位屏幕并保持地址；根路径/未知路径一律落在站点根，不改写地址 */
    var sc0 = screenOfPath(location.pathname);
    if (sc0 && META[sc0]) {
      S.screen = sc0; S.sys = META[sc0].sys;
      render();
      pushRoute(S.screen);
    } else {
      render();
      try {
        if (location.protocol !== 'file:' &&
            (location.pathname !== '/' || location.search)) {
          history.replaceState({ sc: S.screen }, '', '/');
        }
      } catch (e) {}
    }
  });

  /* 浏览器前进 / 后退 */
  window.addEventListener('popstate', function (e) {
    var sc = (e.state && e.state.sc) || screenOfPath(location.pathname);
    if (sc && META[sc]) { S.sys = META[sc].sys; go(sc, true); }
  });
})();

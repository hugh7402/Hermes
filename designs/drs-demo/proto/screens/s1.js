/* ==========================================================================
   屏1 · 新增政务数据目录
   对标对手弱点做改进：
     · 分组可折叠 + 左侧锚点导航 + 每组完成状态（对手：不可折叠、无锚点）
     · 条件字段真联动显隐（对手：是否允许回流 与 原因 同时出现）
     · 只读字段带锁 + “系统自动生成”标注（对手：灰色但没说明）
     · 吸底操作条，随时可提交（对手：按钮在底部要滚到底）
     · 错误汇总条可点击定位到出错字段（对手：无错误汇总）
   ========================================================================== */
window.SCREENS = window.SCREENS || {};
(function () {
  'use strict';

  var A = function () { return window.APP; };

  /* 新增表单自身的状态（与「当前目录」无关；保存草稿只影响本表） */
  var savedDraft = false;

  /* ── 预填值（取自《填写清单0910-样例》，并按输入需求清单 v2 的确认结果调整）── */
  var DEF = {
    1: '四川省自然人基本登记信息',
    55: '四川省公安厅',
    56: '手工新增',
    2: '自然人的基础身份信息，包括姓名、性别、出生日期、民族、国籍等，是自然人身份识别的基础数据。',
    3: '数据管理系统',
    4: '省直',
    5: '民生保障',
    6: '省级',
    7: '数据库',
    8: 'mysql',
    9: '融合数据',
    10: '每日',
    11: '每天 2:00 更新前一天数据',
    12: '否',
    13: '是',
    15: '户籍地省市县代码',
    16: '全省',
    17: '2025-06-30',
    18: '至今',
    19: '有条件共享',
    20: '库表',
    21: '依据《四川省公共数据共享开放管理办法》依申请共享',
    22: '每日',
    24: '有条件开放',
    25: '依申请开放，需说明使用用途',
    34: '是',
    26: '自然人身份信息核验', 27: '510000000001',
    28: '自然人基本信息查询', 29: '51000000000001',
    30: '自然人基本信息核验办事指南', 31: '510000000000000000000000000000001',
    32: '自然人身份信息核验', 33: '510000000001'
  };

  /* ── 数据项（取样例真实 15 项；≥3 项满足治理规则配置要求）── */
  function items() {
    var B = window.DATA && window.DATA.catalog && window.DATA.catalog.items;
    return (B || []).map(function (it, i) {
      return {
        no: i + 1, name: it.cn, en: it.en, desc: it.desc,
        type: it.type, len: it.len, domain: it.has_domain || '否',
        domainName: it.domain_name || '', pk: it.pk, nullable: it.nullable,
        share: it.share || '有条件共享', shareCond: it.share_cond || '依申请共享',
        open: it.open || '有条件开放', openCond: it.open_cond || '依申请开放',
        srcSys: it.src_sys || '数据管理系统', srcCat: it.src_cat || '自建自用',
        sens: it.sensitivity, legal: it.legal_source || '否', reg: it.for_reg || '是'
      };
    });
  }

  /* ── 只读字段 ── */
  var READONLY = {
    code: { label: '数据目录编码', val: function () { return A().S.catalog.code; },
            note: '系统自动生成，不可编辑' }
  };

  function ctlText(id, val, ph, ro) {
    if (ro) {
      return '<div class="ctl ro"><span class="lock">🔒</span><span>' + A().esc(val) + '</span>' +
             '<span class="mut sm" style="margin-left:auto">系统自动生成</span></div>';
    }
    return '<div class="ctl"><input id="' + id + '" type="text" value="' + A().esc(val) + '" ' +
           'placeholder="' + A().esc(ph || '请输入') + '"></div>';
  }
  function ctlArea(id, val, ph) {
    return '<div class="ctl"><textarea id="' + id + '" placeholder="' + A().esc(ph || '请输入') + '" ' +
           'style="min-height:52px">' + A().esc(val) + '</textarea></div>';
  }
  function ctlSelect(id, val, opts, ph) {
    var o = '<option value="">' + A().esc(ph || '请选择') + '</option>';
    opts.forEach(function (v) {
      o += '<option value="' + A().esc(v) + '"' + (v === val ? ' selected' : '') + '>' + A().esc(v) + '</option>';
    });
    return '<div class="ctl"><select id="' + id + '">' + o + '</select></div>';
  }
  function ctlChips(id, vals, opts) {
    var cur = String(vals || '').split(/[，,]/).map(function (s) { return s.trim(); }).filter(Boolean);
    var h = '<div class="ctl" style="flex-wrap:wrap;gap:5px" data-chips="' + id + '">' +
      // 真值存在 hidden input（id 与字段一致，供 collect/validate 读取）
      '<input type="hidden" id="' + id + '" value="' + A().esc(cur.join('，')) + '">';
    cur.forEach(function (c) {
      h += '<span class="chip" data-v="' + A().esc(c) + '">' + A().esc(c) +
           '<x class="chip-x" title="移除">✕</x></span>';
    });
    h += '<select class="chip-add" id="' + id + '-add" style="width:auto;min-width:88px">' +
         '<option value="">＋ 添加</option>';
    opts.forEach(function (v) {
      h += '<option value="' + A().esc(v) + '"' + (cur.indexOf(v) >= 0 ? ' disabled' : '') + '>' +
           A().esc(v) + (cur.indexOf(v) >= 0 ? '（已选）' : '') + '</option>';
    });
    return h + '</select></div>';
  }

  /* chip 多选的读写与同步 */
  function syncChips(id) {
    var wrap = document.querySelector('[data-chips="' + id + '"]'); if (!wrap) return;
    var vals = Array.prototype.map.call(wrap.querySelectorAll('.chip'), function (c) {
      return c.getAttribute('data-v'); });
    var hid = document.getElementById(id);
    if (hid) hid.value = vals.join('，');
  }
  function bindChips(id) {
    var wrap = document.querySelector('[data-chips="' + id + '"]'); if (!wrap) return;
    var add = document.getElementById(id + '-add');
    if (add) add.onchange = function () {
      var v = add.value; if (!v) return;
      var span = document.createElement('span');
      span.className = 'chip'; span.setAttribute('data-v', v);
      span.innerHTML = A().esc(v) + '<x class="chip-x" title="移除">✕</x>';
      wrap.insertBefore(span, add);
      Array.prototype.forEach.call(add.options, function (o) {
        if (o.value === v) { o.disabled = true; o.textContent = v + '（已选）'; } });
      add.value = '';
      span.querySelector('.chip-x').onclick = function () { removeChip(wrap, span, add, v); };
      syncChips(id);
      if (id === 'f6') A().toast('已添加：' + v);
    };
    wrap.querySelectorAll('.chip-x').forEach(function (x) {
      x.onclick = function () {
        var span = x.parentNode;
        removeChip(wrap, span, add, span.getAttribute('data-v'));
        syncChips(id);
      };
    });
    syncChips(id);
  }
  function removeChip(wrap, span, add, v) {
    span.remove();
    if (add) Array.prototype.forEach.call(add.options, function (o) {
      if (o.value === v) { o.disabled = false; o.textContent = v; } });
  }

  /* 单个字段容器 */
  function field(f, ctrlHtml, extra) {
    var req = f.required === 'req' ? '<span class="req">*</span>' :
              (f.required === 'cond' ? '<span class="req" title="条件必填">◐</span>' : '');
    var hint = f.hint ? '<i class="hint" title="' + A().esc(f.hint) + '">?</i>' : '';
    var cond = f.cond ? '<span class="tl">条件：' + A().esc(f.cond) + '</span>' : '';
    return '<div class="fi" id="fi-' + f.idx + '" data-field="' + f.idx + '">' +
      '<label>' + req + A().esc(f.label) + hint + '</label>' + ctrlHtml + cond +
      '<span class="msg">此项为必填，请填写</span></div>';
  }

  /* ── 分组面板 ── */
  function groupPanel(g, gi, extraHtml, nOverride) {
    if (g.isTable) return itemGroup(g, gi);
    // 按字段性质排栅格：摘要/原因类占 2 列
    var wide = { 2: 1, 11: 1, 14: 1, 15: 1, 21: 1, 25: 1, 35: 1 };
    var body = '<div class="fgrid">';
    if (extraHtml) body += extraHtml;          // 只读字段等，作为栅格内第一项
    g.fields.forEach(function (f) {
      var cls = wide[f.idx] ? 'fi span2' : 'fi';
      var html;
      if (f.idx === 6) html = ctlChips('f' + f.idx, DEF[f.idx], f.values);
      else if (f.values && f.values.length) html = ctlSelect('f' + f.idx, DEF[f.idx], f.values);
      else if (f.idx === 17 || f.idx === 18) html = ctlText('f' + f.idx, DEF[f.idx], '如 2025-06-30');
      else if (wide[f.idx]) html = ctlArea('f' + f.idx, DEF[f.idx]);
      else html = ctlText('f' + f.idx, DEF[f.idx]);
      body += field(f, html).replace('class="fi"', 'class="' + cls + '"');
    });
    body += '</div>';
    return panelWrap(g, gi, body, nOverride || g.fields.length);
  }

  function panelWrap(g, gi, body, n) {
    return '<div class="panel" id="gp-' + gi + '" data-group="' + g.name + '">' +
      '<div class="ph"><span class="n">' + (gi + 1) + '</span><h3>' + A().esc(g.name) + '</h3>' +
      '<span class="meta">' + n + ' 项</span><span class="caret">▼</span></div>' +
      '<div class="pb">' + body + '</div></div>';
  }

  /* ── 数据项表格（19 项字段：表格显示主列，编辑开抽屉看全）── */
  function itemGroup(g, gi) {
    var its = items();
    var rows = its.map(function (it) {
      return '<tr data-item="' + it.no + '">' +
        '<td class="c">' + it.no + '</td>' +
        '<td>' + A().esc(it.name) + '</td>' +
        '<td class="mono">' + A().esc(it.en) + '</td>' +
        '<td>' + A().esc(it.type) + '</td>' +
        '<td class="n">' + A().esc(it.len || '—') + '</td>' +
        '<td class="c">' + (it.pk === '是' ? '<b style="color:var(--pri)">是</b>' : '否') + '</td>' +
        '<td class="c">' + A().esc(it.nullable) + '</td>' +
        '<td>' + A().esc(String(it.sens).slice(0, 2)) + '</td>' +
        '<td>' + A().statusTag(it.share) + '</td>' +
        '<td><div class="ops"><a data-edit-item="' + it.no + '">编辑</a>' +
        '<span class="sep">|</span><a class="mut" data-del-item="' + it.no + '">删除</a></div></td>' +
        '</tr>';
    }).join('');
    var body =
      '<div class="notice"><span class="ic">i</span><div>' +
      '数据项共 <b>' + its.length + '</b> 项，其中主键 <b>' +
      its.filter(function (x) { return x.pk === '是'; }).length +
      '</b> 个。<b>治理规则需挂载在字段上，故数据项不少于 3 项</b>（本次 ' + its.length +
      ' 项，满足要求）。点击「编辑」可查看与修改全部 19 项属性。</div></div>' +
      '<div class="tblwrap" style="max-height:none"><table class="data" id="tbl-items">' +
      '<thead><tr><th class="c" style="width:44px">序号</th><th>数据项名称</th><th>英文名称</th>' +
      '<th>数据类型</th><th class="n">长度</th><th class="c">主键</th><th class="c">可为空</th>' +
      '<th>敏感级别</th><th>共享属性</th><th style="width:110px">操作</th></tr></thead>' +
      '<tbody>' + rows + '</tbody></table></div>' +
      '<div class="row" style="margin-top:10px">' +
      '<span class="btn" id="btn-add-item">＋ 新增数据项</span>' +
      '<span class="mut sm">一个数据目录必须且仅有一个主键；主键的「是否可为空」必须为“否”</span></div>';
    return panelWrap(g, gi, body, its.length);
  }

  /* 统一的「该组有多少项内容」计数
     普通组 = 字段数；数据项组 = 实际数据项条数（不是它的 19 个属性列） */
  function groupCount(g) { return g.isTable ? items().length : g.fields.length; }
  function totalCount(spec) {
    return spec.reduce(function (a, g) { return a + groupCount(g); }, 0);
  }

  /* ── 锚点导航 ── */
  function formNav(spec) {
    return '<div class="formnav" id="formnav"><div class="fn-h">属性分组导航</div>' +
      spec.map(function (g, i) {
        return '<a data-goto="' + i + '"><span>' + A().esc(g.name) + '</span>' +
               '<span class="st" id="navst-' + i + '">' + groupCount(g) + '</span></a>';
      }).join('') + '</div>';
  }

  var render = function () {
    var spec = window.FORM_SPEC || [];
    var S = A().S;
    return '' +
    '<div class="pagetitle"><h1>新增政务数据目录</h1>' +
      '<div class="right">' +
        '<span class="btn sm" id="btn-upload">数据目录导入</span>' +
        '<input type="file" id="file-upload" accept=".csv,.txt,.json,.xlsx,.xls" style="display:none">' +
        '<span class="mut sm">目录状态：</span>' + A().statusTag(savedDraft ? '草稿' : '未提交') +
      '</div></div>' +

    '<div class="errbar" id="errbar"><b>提交未通过校验，请修正下列问题后重试：</b><ul id="errlist"></ul></div>' +

    '<div class="row" style="align-items:flex-start;gap:14px">' +
      formNav(spec) +
      '<div class="grow" style="min-width:0">' +

        // 基础标识属性（含只读的「数据目录编码」，作为栅格内第一项）
        (function () {
          var extra = '<div class="fi" id="fi-code"><label>数据目录编码' +
            '<i class="hint" title="由系统按 R＋行政区划6位＋TAB＋日期8位＋序号 自动生成">?</i></label>' +
            '<div class="ctl ro"><span class="lock">🔒</span>' +
            '<span class="mono">保存后自动生成</span>' +
            '<span class="mut sm" style="margin-left:auto">系统自动生成</span></div></div>';
          // 只读的「数据目录编码」不计入填写项数，保证与左侧锚点口径一致
          return groupPanel(spec[0], 0, extra, spec[0].fields.length);
        })() +

        spec.slice(1).map(function (g, i) { return groupPanel(g, i + 1); }).join('') +

      '</div>' +
    '</div>' +

    // 吸底操作条
    '<div class="actbar">' +
      '<span class="btn" id="btn-cancel">取消</span>' +
      '<span class="btn" id="btn-save">保存草稿</span>' +
      '<span class="btn pri" id="btn-submit">提交审核</span>' +
    '</div>';
  };

  /* 来源系统 → 所属分类（联动规则1：选定来源系统后自动带出；分类值域：自建自用/国直/省直/市级自建） */
  var SECLASS = {
    '四川省人口基础信息库': '国直',
    '金保工程二期社会保险稽核管理系统': '国直',
    '四川省社会保障卡管理系统': '国直',
    '四川省社会救助信息管理系统': '省直',
    '四川省养老服务信息平台': '省直',
    '四川省卫生健康信息平台': '省直',
    '四川省学籍管理系统': '省直',
    '四川省医疗保障信息平台': '省直',
    '四川省市场监管一体化平台': '省直',
    '四川省税务大数据平台': '国直',
    '数据管理系统': '省直'
  };
  /* 数据提供单位 → 可选来源系统（联动规则2：单位决定可选系统范围，通用系统对所有单位开放） */
  var SYSBYORG = {
    '四川省公安厅': ['四川省人口基础信息库', '数据管理系统'],
    '四川省民政厅': ['四川省社会救助信息管理系统', '四川省养老服务信息平台', '数据管理系统'],
    '四川省人力资源和社会保障厅': ['金保工程二期社会保险稽核管理系统',
                                  '四川省社会保障卡管理系统', '数据管理系统'],
    '四川省卫生健康委员会': ['四川省卫生健康信息平台', '数据管理系统'],
    '四川省教育厅': ['四川省学籍管理系统', '数据管理系统'],
    '四川省医疗保障局': ['四川省医疗保障信息平台', '数据管理系统'],
    '四川省市场监督管理局': ['四川省市场监管一体化平台', '数据管理系统'],
    '四川省税务局': ['四川省税务大数据平台', '数据管理系统']
  };

  /* 按数据提供单位收敛可选来源系统；用户选择变更时把所属分类带出来。
     keepClass=true 用于页面载入：只收敛可选范围，不改写已存数据 */
  function syncSource(keepClass) {
    var orgEl = document.getElementById('f55');
    var sel = document.getElementById('f3');
    if (!sel) { return; }
    var org = orgEl ? orgEl.value : '';
    var list = SYSBYORG[org];
    if (list && sel.getAttribute('data-org') !== org) {
      var cur = sel.value;
      // 用 DOM 构造 option，不拼 HTML 字符串
      while (sel.firstChild) { sel.removeChild(sel.firstChild); }
      list.forEach(function (x) {
        var o = document.createElement('option');
        o.textContent = x;
        if (x === cur) { o.selected = true; }
        sel.appendChild(o);
      });
      var none = document.createElement('option');
      none.textContent = '暂无系统';
      if (cur === '暂无系统') { none.selected = true; }
      sel.appendChild(none);
      sel.setAttribute('data-org', org);
      if (list.indexOf(sel.value) < 0 && sel.value !== '暂无系统') { sel.value = list[0]; }
    }
    // 带出只在「来源系统值真的发生变化」时发生：
    // 载入时(keepClass)不动；仅重选数据提供单位而系统未变时也不动
    var last = sel.getAttribute('data-sys') || '';
    if (!keepClass && sel.value !== last) {
      var cls = SECLASS[sel.value];
      var c = document.getElementById('f4');
      if (c && cls) { c.value = cls; }
    }
    sel.setAttribute('data-sys', sel.value);
    applyCond();
  }

  /* 按当前选择刷新条件字段显隐（11 条联动规则） */
  function applyCond() {
    var v = function (id) { var e = document.getElementById(id); return e ? e.value : ''; };
    var show = function (idx, on) {
      var el = document.getElementById('fi-' + idx); if (!el) return;
      el.style.display = on ? '' : 'none';
    };
    show(4, v('f3') && v('f3') !== '暂无系统');            // 所属分类
    show(8, v('f7') && v('f7') !== '暂无数据');            // 格式类型
    show(14, v('f13') === '否');                           // 不允许回流原因
    show(15, v('f13') === '是');                           // 回流切分字段
    show(20, v('f19') !== '不予共享');                     // 共享方式
    show(22, v('f19') !== '不予共享');                     // 共享频率
    show(23, v('f22') === '其他');                         // 共享频率说明
    show(35, true);   // 不予发布原因：常显（选「否」时必填）——便于评审直接看到该要素
    // 聚合约束提示
    var n = document.getElementById('agg-tip');
    if (n) n.style.display = (v('f19') === '无条件共享') ? '' : 'none';
  }

  function collect() {
    var out = {};
    (window.FORM_SPEC || []).forEach(function (g) {
      g.fields.forEach(function (f) {
        var e = document.getElementById('f' + f.idx);
        if (e) out[f.idx] = e.value;
      });
    });
    return out;
  }

  /* 校验：必填 + 主键规则 + 聚合约束 */
  function validate() {
    var errs = [], vals = collect();
    (window.FORM_SPEC || []).forEach(function (g) {
      if (g.isTable) return;
      g.fields.forEach(function (f) {
        var fi = document.getElementById('fi-' + f.idx);
        if (!fi || fi.style.display === 'none') return;
        // 条件必填：常显字段的必填与否仍按条件判定（不能靠「隐藏即跳过」）
        //   23 共享频率说明 —— 仅当共享频率=其他
        //   35 不予发布原因 —— 仅当是否发布=否
        var need = f.required === 'req' ||
          (f.required === 'cond'
            && !(f.idx === 23 && vals[22] !== '其他')
            && !(f.idx === 35 && vals[34] !== '否'));
        if (need && !String(vals[f.idx] || '').trim()) {
          errs.push({ idx: f.idx, label: f.label, why: '必填项未填写' });
        }
      });
    });
    // 数据项规则
    var its = items();
    if (its.length < 3) errs.push({ idx: 36, label: '数据项', why: '少于 3 项，无法配置治理规则' });
    var pks = its.filter(function (x) { return x.pk === '是'; });
    if (pks.length === 0) errs.push({ idx: 43, label: '数据项·是否主键', why: '必须指定 1 个主键' });
    // 聚合约束
    if (vals[19] === '无条件共享' && its.some(function (x) {
      return x.share === '有条件共享' || x.share === '不予共享'; })) {
      errs.push({ idx: 19, label: '共享属性',
        why: '任一数据项为「有条件共享/不予共享」时，目录整体不得填「无条件共享」' });
    }
    if (vals[24] === '无条件开放' && its.some(function (x) {
      return x.open === '有条件开放' || x.open === '不予开放'; })) {
      errs.push({ idx: 24, label: '开放属性',
        why: '任一数据项为「有条件开放/不予开放」时，目录整体不得填「无条件开放」' });
    }
    return errs;
  }

  function showErrs(errs) {
    var bar = document.getElementById('errbar'), list = document.getElementById('errlist');
    document.querySelectorAll('.fi.err').forEach(function (e) { e.classList.remove('err'); });
    if (!errs.length) { bar.classList.remove('on'); return; }
    list.innerHTML = errs.map(function (e) {
      return '<li data-err="' + e.idx + '">' + A().esc(e.label) + ' — ' + A().esc(e.why) + '</li>';
    }).join('');
    bar.classList.add('on');
    errs.forEach(function (e) {
      var fi = document.getElementById('fi-' + e.idx); if (fi) fi.classList.add('err');
    });
    list.querySelectorAll('li').forEach(function (li) {
      li.onclick = function () {
        var fi = document.getElementById('fi-' + li.getAttribute('data-err'));
        if (!fi) return;
        fi.scrollIntoView({ block: 'center', behavior: 'smooth' });
        var c = fi.querySelector('input,select,textarea'); if (c) c.focus();
      };
    });
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  /* 数据项编辑抽屉（19 项全字段） */
  /* ── 数据项：可手工新增 / 编辑 / 删除（真实可操作）──────────────
     内部键（cn/en/…）与界面键（name/en/…）的映射 */
  var ITEM_KEY = { 36: 'name', 37: 'en', 38: 'desc', 39: 'type', 40: 'len', 41: 'domain',
                   42: 'domainName', 43: 'pk', 44: 'nullable', 45: 'share', 46: 'shareCond',
                   47: 'open', 48: 'openCond', 49: 'srcSys', 50: 'srcCat', 51: 'sens',
                   52: 'legal', 53: 'reg', 54: 'regNote' };
  var RAW_KEY = { name: 'cn', en: 'en', desc: 'desc', type: 'type', len: 'len',
                  domain: 'has_domain', domainName: 'domain_name', pk: 'pk',
                  nullable: 'nullable', share: 'share', shareCond: 'share_cond',
                  open: 'open', openCond: 'open_cond', srcSys: 'src_sys',
                  srcCat: 'src_cat', sens: 'sens', legal: 'legal', reg: 'reg',
                  regNote: 'reg_note' };
  /* 可编辑的核心属性（其余按要素规格只读展示） */
  var ITEM_EDITABLE = ['name', 'en', 'type', 'len', 'pk', 'nullable',
                       'share', 'shareCond', 'open', 'openCond', 'desc'];

  function rawItems() {
    if (!window.DATA) { window.DATA = {}; }
    if (!window.DATA.catalog) { window.DATA.catalog = {}; }
    if (!window.DATA.catalog.items) { window.DATA.catalog.items = []; }
    return window.DATA.catalog.items;
  }

  function itemForm(it) {
    var spec = (window.FORM_SPEC || []).filter(function (g) { return g.isTable; })[0] || { fields: [] };
    return '<div class="fgrid c2">' + spec.fields.map(function (f) {
      var k = ITEM_KEY[f.idx]; if (!k) return '';
      var v = it[k] == null ? '' : String(it[k]);
      var req = f.required === 'req' ? '<span class="req">*</span>' :
                (f.required === 'cond' ? '<span class="req">◐</span>' : '');
      var editable = ITEM_EDITABLE.indexOf(k) >= 0;
      var ctl;
      if (!editable) {
        ctl = '<div class="ctl ro"><span>' + (v ? A().esc(v) : '—') + '</span></div>';
      } else if (f.values && f.values.length) {
        ctl = '<div class="ctl"><select id="it-' + k + '">' +
          [''].concat(f.values).map(function (o) {
            return '<option' + (String(o) === v ? ' selected' : '') + '>' + A().esc(o) + '</option>';
          }).join('') + '</select></div>';
      } else {
        ctl = '<div class="ctl"><input class="inp" id="it-' + k + '" value="' + A().esc(v) + '"></div>';
      }
      return '<div class="fi" id="fi-it-' + k + '"><label>' + req + A().esc(f.label) + '</label>' +
             ctl + '</div>';
    }).join('') + '</div>';
  }

  /* 打开数据项表单：no 为 null 表示新增 */
  function openItem(no) {
    var all = items();
    var it = no ? all.filter(function (x) { return x.no === no; })[0] : null;
    if (no && !it) { return; }
    if (!it) {
      it = { name: '', en: '', desc: '', type: 'varchar', len: '', pk: '否', nullable: '是',
             share: '有条件共享', shareCond: '依申请共享', open: '有条件开放',
             openCond: '依申请开放' };
    }
    var isNew = !no;
    A().openDrawer((isNew ? '新增数据项' : '编辑数据项 · ' + it.name + '（第 ' + no + ' 项）'),
      itemForm(it) +
      '<div class="notice" style="margin-top:12px"><span class="ic">i</span><div>' +
      '数据项须<b>不少于 3 项</b>，且必须指定 <b>1 个主键</b>；治理规则将挂载在数据项字段上。' +
      '当前共 <b>' + all.length + '</b> 项。</div></div>',
      '<span class="btn" data-close="1">取消</span>' +
      '<span class="btn pri" id="item-save">' + (isNew ? '新增' : '保存') + '</span>');

    var b = document.getElementById('item-save');
    if (b) b.onclick = function () {
      // 取值
      var out = {}, empty = [];
      ITEM_EDITABLE.forEach(function (k) {
        var e = document.getElementById('it-' + k);
        var val = e ? String(e.value == null ? '' : e.value).trim() : '';
        out[RAW_KEY[k]] = val;
        var fi = document.getElementById('fi-it-' + k);
        if (fi) { fi.classList.remove('err'); }
        if (!val && (k === 'name' || k === 'en')) {
          empty.push(k); if (fi) { fi.classList.add('err'); }
        }
      });
      if (empty.length) {
        A().toast('数据项中文名称与英文名称不能为空', 'err'); return;
      }
      // 英文名重名检查
      var B = rawItems();
      var dup = B.some(function (x, i) {
        return String(x.en || '') === out.en && (!no || i !== no - 1);
      });
      if (dup) { A().toast('数据项英文名称已存在：' + out.en, 'err'); return; }

      if (isNew) {
        B.push(out);
      } else {
        var tgt = B[no - 1] || {};
        for (var k2 in out) { tgt[k2] = out[k2]; }
        B[no - 1] = tgt;
      }
      A().closeDrawer();
      A().render();
      A().toast(isNew ? ('数据项「' + out.cn + '」已新增，共 ' + rawItems().length + ' 项')
                      : ('数据项「' + out.cn + '」已保存'), 'ok');
    };
  }

  var init = function () {
    applyCond();
    bindChips('f6');            // 数据所在层级（多选 chip）
    // 折叠
    document.querySelectorAll('.panel > .ph').forEach(function (ph) {
      ph.onclick = function () { ph.parentNode.classList.toggle('fold'); };
    });
    // 联动
    ['f7', 'f13', 'f19', 'f22', 'f34'].forEach(function (id) {
      var e = document.getElementById(id);
      if (e) { e.onchange = applyCond; e.oninput = applyCond; }
    });
    // 联动规则1/2：来源系统 ↔ 所属分类 ↔ 数据提供单位
    // 注意：必须包一层，否则事件对象会被当成 keepClass 参数传入
    var _sy = document.getElementById('f3');
    if (_sy) { _sy.onchange = function () { syncSource(false); }; }
    var _pv = document.getElementById('f55');
    if (_pv) {
      _pv.onchange = function () { syncSource(false); };
      _pv.oninput = function () { syncSource(false); };
    }
    syncSource(true);   // 载入：只收敛可选范围，保持已存数据不动
    // 锚点
    document.querySelectorAll('[data-goto]').forEach(function (a) {
      a.onclick = function () {
        var p = document.getElementById('gp-' + a.getAttribute('data-goto'));
        if (p) { p.classList.remove('fold'); p.scrollIntoView({ block: 'start', behavior: 'smooth' }); }
      };
    });
    // 数据项
    document.querySelectorAll('[data-edit-item]').forEach(function (a) {
      a.onclick = function () { openItem(a.getAttribute('data-edit-item')); };
    });
    document.querySelectorAll('[data-del-item]').forEach(function (a) {
      a.onclick = function () {
        var no = parseInt(a.getAttribute('data-del-item'), 10);
        var it = items().filter(function (x) { return x.no === no; })[0]; if (!it || !no) { return; }
        if (items().length <= 3) {
          A().toast('数据项不得少于 3 项，当前 ' + items().length + ' 项，无法删除', 'err'); return;
        }
        A().openModal('删除数据项',
          '确定删除数据项 <b>' + A().esc(it.name) + '</b>（第 ' + no + ' 项）？' +
          '删除后挂载在该字段上的治理规则需一并调整。',
          '<span class="btn" data-close-m="1">取消</span>' +
          '<span class="btn pri" id="del-item-ok">确定删除</span>');
        var db = document.getElementById('del-item-ok');
        if (db) db.onclick = function () {
          rawItems().splice(no - 1, 1);
          A().closeModal();
          A().render();
          A().toast('数据项已删除，现共 ' + rawItems().length + ' 项', 'ok');
        };
      };
    });
    var ai = document.getElementById('btn-add-item');
    if (ai) ai.onclick = function () { openItem(null); };

    // ── 数据目录导入：真实解析 CSV / XLSX，逐行生成数据目录 ──────────
    var up = document.getElementById('btn-upload'), fi = document.getElementById('file-upload');
    if (up) up.onclick = function () { fi.click(); };
    if (fi) fi.onchange = function () {
      var f = fi.files && fi.files[0]; if (!f) return;
      var isX = /\.xlsx?$/i.test(f.name);
      var rd = new FileReader();
      rd.onload = function () {
        var go = function (sheets) { doImport(f, sheets); };
        if (isX) {
          A().xlsxSheets(rd.result).then(go).catch(function (e) {
            A().openModal('导入失败',
              '<div class="notice err"><span class="ic">!</span><div>文件解析失败：<b>' +
              A().esc(e.message) + '</b></div></div><div class="mut sm" style="margin-top:10px">' +
              '请确认导出的文件为 .xlsx 格式；也可另存为 CSV 后导入。</div>',
              '<span class="btn" data-close-m="1">关闭</span>');
          });
        } else { go([String(rd.result || '')]); }
      };
      if (isX) rd.readAsArrayBuffer(f); else rd.readAsText(f, 'utf-8');
      fi.value = '';
    };

    /* ── 导入实现 ───────────────────────────────────────────────── */
    function parseDelim(text) {
      var rows = [], row = [], cur = '', q = false, i, ch;
      text = text.replace(/^\uFEFF/, '');
      for (i = 0; i < text.length; i++) {
        ch = text[i];
        if (q) {
          if (ch === '"') { if (text[i + 1] === '"') { cur += '"'; i++; } else { q = false; } }
          else { cur += ch; }
        } else if (ch === '"') { q = true; }
        else if (ch === ',' || ch === '\t') { row.push(cur); cur = ''; }
        else if (ch === '\n') { row.push(cur); rows.push(row); row = []; cur = ''; }
        else if (ch !== '\r') { cur += ch; }
      }
      if (cur !== '' || row.length) { row.push(cur); rows.push(row); }
      return rows.filter(function (r) {
        return r.some(function (c) { return String(c || '').trim(); });
      });
    }

    /* 表头行识别：与要素字段名匹配最多的一行 */
    function mapColumns(rows) {
      var labels = {};
      (window.FORM_SPEC || []).forEach(function (g) {
        g.fields.forEach(function (f) { labels[String(f.label).trim()] = f.idx; });
      });
      var best = -1, bestN = 0, map = {};
      rows.slice(0, 8).forEach(function (r, ri) {
        var m = {}, n = 0;
        r.forEach(function (cell, ci) {
          var t = String(cell == null ? '' : cell).trim().replace(/^[◐*★\s]+/, '');
          if (labels[t] !== undefined && m[labels[t]] === undefined) { m[labels[t]] = ci; n++; }
        });
        if (n > bestN) { bestN = n; best = ri; map = m; }
      });
      return { headRow: best, map: map, matched: bestN };
    }

    function asRows(x) { return Array.isArray(x) ? x : parseDelim(String(x == null ? '' : x)); }

    function doImport(file, sheets) {
      var rows = asRows(sheets[0]);
      var mc = mapColumns(rows);
      if (mc.matched < 2) {
        A().openModal('导入失败',
          '<div class="notice err"><span class="ic">!</span><div>未能识别表头。当前模板的字段名须与要素名称一致。' +
          '</div></div><div class="mut sm" style="margin-top:10px">识别到的首行：<span class="mono">' +
          A().esc((rows[0] || []).slice(0, 8).join(' | ')) + '</span></div>',
          '<span class="btn" data-close-m="1">关闭</span>');
        return;
      }
      // 数据项（第二个工作表，按目录名称挂接）
      var itemMap = {};
      if (sheets[1]) {
        var irows = asRows(sheets[1]);
        var ih = irows[0] || [];
        var cName = ih.findIndex(function (x) { return /目录名称/.test(String(x)); });
        if (cName >= 0) {
          irows.slice(1).forEach(function (r) {
            var k = String(r[cName] || '').trim();
            if (!k) return;
            (itemMap[k] = itemMap[k] || []).push({
              cn: String(r[1] || ''), en: String(r[2] || ''), type: String(r[3] || 'varchar'),
              len: String(r[4] || ''), pk: String(r[5] || '否'), req: String(r[6] || '否'),
              share: String(r[7] || '有条件共享'), share_cond: String(r[8] || '依申请共享'),
              open: String(r[9] || '有条件开放'), open_cond: String(r[10] || '依申请开放'),
              desc: String(r[11] || '')
            });
          });
        }
      }
      var made = [];
      rows.slice(mc.headRow + 1).forEach(function (r) {
        var vals = {};
        for (var idx in mc.map) { vals[idx] = String(r[mc.map[idx]] == null ? '' : r[mc.map[idx]]).trim(); }
        var _nIdx = A().idxOf('数据目录名称');
        if (!String(vals[_nIdx] || '').trim()) { return; }   // 目录名称为空的行跳过
        var its = itemMap[String(vals[A().idxOf('数据目录名称')] || '').trim()];
        var gl = function (lb, d) {
          var i = A().idxOf(lb);
          return String(i == null ? '' : (vals[i] || '')).trim() || d;
        };
        made.push(A().addCatalog({
          code: gl('数据目录编码', ''),
          name: gl('数据目录名称', '未命名数据目录'),
          org: gl('数据提供单位', '四川省公安厅'),
          summary: gl('数据摘要', ''),
          source: gl('数据来源系统', '暂无系统'),
          domain: gl('数据所属领域', '民生保障'),
          level: gl('数据所在层级', '省级'),
          share: gl('共享属性', '有条件共享'),
          method: '数据目录导入',
          items: (its && its.length) ? its : [],
          vals: vals,
          status: '待审核'
        }));
      });
      if (!made.length) {
        A().openModal('导入结果',
          '<div class="notice warn"><span class="ic">!</span><div>表头识别成功（匹配 <b>' + mc.matched +
          '</b> 个要素），但没有读到有效数据行——「数据目录名称」为空的记录会被跳过。</div></div>',
          '<span class="btn" data-close-m="1">关闭</span>');
        return;
      }
      A().render();   // 先重绘，再弹窗
      A().openModal('导入完成',
        '<div class="notice ok"><span class="ic">✓</span><div>文件 <b>' + A().esc(file.name) +
        '</b> 解析成功，共生成 <b>' + made.length + '</b> 条数据目录（状态：待审核）。</div></div>' +
        '<div class="tblwrap" style="margin-top:10px"><table class="data"><thead><tr>' +
        '<th>数据目录编码</th><th>数据目录名称</th><th>数据提供单位</th><th>所属领域</th>' +
        '<th>来源方式</th><th>数据项</th></tr></thead><tbody>' +
        made.map(function (c) {
          return '<tr><td class="mono">' + A().esc(c.code) + '</td><td>' + A().esc(c.name) +
            '</td><td>' + A().esc(c.org) + '</td><td>' + A().esc(c.domain) +
            '</td><td>' + A().esc(c.method) + '</td><td class="n">' + (c.items || []).length +
            '</td></tr>';
        }).join('') + '</tbody></table></div>' +
        // 逐条列出导入的目录要素（基础标识/数据特征/范围界定/共享开放/事项业务关联）
        made.slice(0, 3).map(function (c) {
          var gs = (window.FORM_SPEC || []).filter(function (g) { return !g.isTable; });
          return '<div class="panel" style="margin-top:12px"><div class="ph"><h3>' +
            A().esc(c.name) + ' · 目录要素</h3><span class="meta">' + A().esc(c.method) +
            '</span></div><div class="pb">' +
            gs.map(function (g) {
              var rows = g.fields.filter(function (f) {
                var i = A().idxOf(f.label);
                return i != null && String((c.vals || {})[i] || '').trim();
              });
              if (!rows.length) { return ''; }
              return '<div style="margin-bottom:10px">' +
                '<div style="font-weight:600;color:var(--pri);font-size:12.5px;margin-bottom:5px">' +
                A().esc(g.get ? g.get('name') : g.name) + '</div>' +
                '<div class="kv">' + rows.map(function (f) {
                  var i = A().idxOf(f.label);
                  return '<div class="r"><div class="k">' + A().esc(f.label) + '</div>' +
                    '<div class="v">' + A().esc(String((c.vals || {})[i])) + '</div></div>';
                }).join('') + '</div></div>';
            }).join('') + '</div></div>';
        }).join(''),
        '<span class="btn" data-close-m="1">取消</span>' +
        '<span class="btn pri" id="imp-go-approve">前往数据目录审批管理</span>');
      var g2 = document.getElementById('imp-go-approve');
      if (g2) g2.onclick = function () { A().closeModal(); A().go('s2'); };
    }

    // 保存草稿
    var sv = document.getElementById('btn-save');
    if (sv) sv.onclick = function () {
      savedDraft = true; A().toast('已保存草稿', 'ok'); A().render();
    };
    var cn = document.getElementById('btn-cancel');
    if (cn) cn.onclick = function () { A().go('s1b'); };

    // 提交审核
    var sb = document.getElementById('btn-submit');
    if (sb) sb.onclick = function () {
      var errs = validate();
      showErrs(errs);
      if (errs.length) { A().toast('有 ' + errs.length + ' 项需修正', 'err'); return; }
      // 真正建立一条新的数据目录档案（手工编目）
      var _v = collect();
      var _g = function (lb, d) {
        var i = A().idxOf(lb), x = (i == null ? '' : _v[i]);
        return String(x == null ? '' : x).trim() || d;
      };
      var _cat = A().addCatalog({
        name: _g('数据目录名称', '未命名数据目录'),
        org: _g('数据提供单位', '四川省公安厅'),
        summary: _g('数据摘要', ''),
        source: _g('数据来源系统', '暂无系统'),
        domain: _g('数据所属领域', '民生保障'),
        level: _g('数据所在层级', '省级'),
        share: _g('共享属性', '有条件共享'),
        method: '手工新增',
        items: items(),
        vals: _v,
        status: '待审核'
      });
      A().S.formRecord = _cat.code;
      A().S.done.cat = true;
      A().render();   // 先重绘（刷新目录状态与列表），再开弹窗
      A().openModal('提交成功',
        '<div class="notice ok"><span class="ic">✓</span><div>' +
        '数据目录 <b>' + A().esc(_cat.name) + '</b>（编码 <span class="mono">' +
        A().esc(_cat.code) + '</span>）已建档并提交，进入审核流程。</div></div>' +
        '<div class="tl" style="margin-top:12px">' +
        '<div class="ti"><div class="tt">数据目录审核 · 目录审核员</div><div class="td">待处理</div></div>' +
        '</div><div class="mut sm" style="margin-top:10px">请到【我的审批工单】完成目录审核，审核通过后目录即发布。</div>',
        '<span class="btn" data-close-m="1">取消</span>' +
        '<span class="btn pri" id="go-audit">前往我的审批工单</span>');
      var g = document.getElementById('go-audit');
      if (g) g.onclick = function () { A().closeModal(); A().go('s2'); };
    };
  };

  window.SCREENS.s1 = { render: render, init: init, validate: validate,
                        collect: collect, openItem: openItem, applyCond: applyCond };
})();

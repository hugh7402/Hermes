/* 原型调试开关（Ctrl+D）—— 点一下即锁定并复制，零歧义反馈
 *
 * 依赖页面提供：APP.screen（当前屏 id）、toast(msg)（可省）
 * 用法：1) 把 CSS 块贴进样式表  2) 把下面的 JS 贴进主脚本  3) render() 末尾调 __dbgWire()
 *       4) 在 render 输出里放：__dbgBoxHTML()
 *
 * 设计要点（都是踩过的坑，别改）：
 *   - 点击元素 = 锁定 + 自动复制，且不触发该元素功能（capture + preventDefault）
 *   - 锁定后 mousemove 直接 return —— 否则「把鼠标移去点【复制】」信息就变了，功能等于没有
 *   - 兜底框必须 textarea 不是 input（input 的 value 不保留换行）
 *   - 面板 pointer-events:none，只有标题栏 auto（否则挡住自己下方的元素）
 */
var DBG = { on: false, last: null, pin: null };

function dbgStripCls(cn) {
  return (typeof cn === 'string' ? cn : '').replace(/\bdbgout\b/g, '').replace(/\bdbgpin\b/g, '').trim();
}
function dbgPath(el) {
  var parts = [], n = el, guard = 0;
  while (n && n.nodeType === 1 && guard++ < 8) {
    var s = n.tagName.toLowerCase();
    if (n.id) { parts.unshift(s + '#' + n.id); break; }
    var cls = dbgStripCls(n.className).split(/\s+/).filter(Boolean)[0];
    if (cls) s += '.' + cls;
    var p = n.parentElement;
    if (p) {
      var sibs = Array.prototype.filter.call(p.children, function (c) { return c.tagName === n.tagName; });
      if (sibs.length > 1) s += ':nth-of-type(' + (sibs.indexOf(n) + 1) + ')';
    }
    parts.unshift(s); n = p;
  }
  return parts.join(' > ');
}
function dbgInfo(el) {
  if (!el || el.nodeType !== 1) return null;
  if (el.closest && el.closest('#dbgbox')) return null;
  return { screen: (window.APP && APP.screen) || '-', tag: el.tagName.toLowerCase(),
           id: el.id || '(无)', cls: dbgStripCls(el.className) || '(无)', path: dbgPath(el),
           text: (el.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 80) };
}

/* 只写 
 会踩转义链路的坑，用 fromCharCode 最稳 */
function dbgText(i) {
  var NL = String.fromCharCode(10);
  return '屏 ' + i.screen + '｜元素 ' + i.tag + '｜id ' + i.id + '｜class ' + i.cls
       + NL + '选择器 ' + i.path + NL + '文本 ' + i.text;
}
function dbgShow(el) {
  var box = document.getElementById('dbgbox'), txt = document.getElementById('dbgtxt');
  if (!box || !txt) return;
  var i = dbgInfo(el);
  box.style.display = i ? 'block' : 'none';
  if (i) {
    var pin = (DBG.pin === el);
    txt.innerHTML = '<b>' + (pin ? '● 已锁定' : '○ 跟随中') + '</b> 屏 <b>' + i.screen
      + '</b> 元素 <b>' + i.tag + '</b>' + (NL()) + 'id ' + i.id + '｜class ' + i.cls
      + (NL()) + '<span style="opacity:.75">' + i.path + '</span>' + (NL()) + '文本 ' + i.text;
  }
  function NL() { return '<br>'; }
}
function dbgCopy(silent) {
  var el = DBG.pin || DBG.last, i = dbgInfo(el);
  if (!i) { if (window.toast) toast('先点击要反馈的元素，或把鼠标移上去'); return false; }
  var line = dbgText(i);
  /* 兜底：必须 textarea（input 的 value 不保留换行） */
  var ta = document.getElementById('dbgraw');
  if (ta) { ta.value = line; ta.style.display = 'block'; ta.select(); }
  try { navigator.clipboard.writeText(line); } catch (e) {}
  if (!silent && window.toast) toast('已复制定位信息，直接粘给开发即可');
  return true;
}

function __dbgBoxHTML() {
  return '<div class="dbgbox" id="dbgbox" style="display:none">'
    + '<div class="dbgh">调试信息<span class="dbgcopy" id="dbgcopy">复制</span></div>'
    + '<div id="dbgtxt">把鼠标移到任意元素上，点击即可锁定并复制</div>'
    + '<textarea id="dbgraw" readonly style="display:none"></textarea>'
    + '<div class="dbghint">点击元素=锁定并复制　按 C 复制当前　Esc 解锁　Ctrl+D 关闭</div>'
    + '</div>';
}

var __dbgWired = false;
function __dbgWire() {
  var cp = document.getElementById('dbgcopy');
  if (cp) cp.onclick = function (e) { e.stopPropagation(); dbgCopy(false); };
  if (__dbgWired) return;
  __dbgWired = true;
  document.addEventListener('mousemove', function (e) {
    if (!DBG.on) return;
    if (DBG.pin) return;               /* ★ 锁定后不跟随，否则复制不到 */
    var el = e.target;
    if (el.closest && el.closest('#dbgbox')) return;
    if (DBG.last) DBG.last.classList.remove('dbgout');
    DBG.last = el; el.classList.add('dbgout'); dbgShow(el);
  }, true);
  document.addEventListener('click', function (e) {
    if (!DBG.on) return;
    if (e.target.closest && e.target.closest('#dbgbox')) return;   /* 放行面板自身 */
    e.preventDefault(); e.stopPropagation();                        /* ★ 不触发该元素功能 */
    if (DBG.pin) DBG.pin.classList.remove('dbgpin');
    DBG.pin = e.target; DBG.pin.classList.add('dbgpin');
    if (DBG.last) DBG.last.classList.remove('dbgout');
    dbgShow(DBG.pin); dbgCopy(false);
  }, true);
  document.addEventListener('keydown', function (e) {
    if ((e.ctrlKey || e.metaKey) && (e.key === 'd' || e.key === 'D')) { e.preventDefault(); __dbgToggle(); return; }
    if (!DBG.on) return;
    if (e.key === 'Escape' && DBG.pin) { DBG.pin.classList.remove('dbgpin'); DBG.pin = null; dbgShow(DBG.last); }
    else if ((e.key === 'c' || e.key === 'C') && !e.ctrlKey && !e.metaKey) {
      var t = document.activeElement;
      if (!t || !/^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName)) { e.preventDefault(); dbgCopy(false); }
    }
  }, true);
}
function __dbgToggle(v) {
  DBG.on = (v === undefined) ? !DBG.on : v;
  document.documentElement.classList.toggle('dbgmode', DBG.on);
  if (!DBG.on) {
    if (DBG.last) DBG.last.classList.remove('dbgout');
    if (DBG.pin) DBG.pin.classList.remove('dbgpin');
    DBG.last = DBG.pin = null;
    var b = document.getElementById('dbgbox'); if (b) b.style.display = 'none';
  }
}

/* 配套 CSS（贴进样式表）
.dbgout { outline: 2px solid #ff3b30 !important; outline-offset: 1px !important; }
.dbgpin { outline: 2px solid #ffb020 !important; outline-offset: 1px !important;
          box-shadow: 0 0 0 3px rgba(255,176,32,.28) !important; }
.dbgbox { position: fixed; right: 12px; bottom: 12px; width: 380px; z-index: 99999;
          background: #101c26; color: #cfe8f7; border-radius: 6px; font: 12px/1.7 monospace;
          box-shadow: 0 8px 26px rgba(0,0,0,.45);
          pointer-events: none; }              /* ★ 面板本体不接事件，否则挡住下方元素 */
.dbgbox .dbgh { pointer-events: auto; }         /* ★ 只有标题栏可点（【复制】在这） */
.dbgcopy { float: right; cursor: pointer; background: #2691e2; color: #fff;
           padding: 2px 10px; border-radius: 3px; }
*/

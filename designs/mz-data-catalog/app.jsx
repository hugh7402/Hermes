/* app.jsx — App：状态所有者 + 挂载
   共享状态一律上提到 App，通过 props 下传（不跨文件散落 useState） */

const { useState, useEffect, useMemo, useRef } = React;
const { CATALOG, MY_APPLIES, CYCLE_OPTIONS, SHARE_FILTERS, sizeText, nowStamp } = window;

const PAGE_SIZE = 8;

function App(){
  /* ---- 主题（令牌翻转）---- */
  const [theme, setTheme] = useState('light');
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  /* ---- 导航 / 目录 ---- */
  const [screen, setScreen] = useState('catalog');
  const [records, setRecords] = useState(CATALOG);
  const [kw, setKw] = useState('');
  const [share, setShare] = useState('全部');
  const [sort, setSort] = useState({ key:'updated', dir:'desc' });
  const [page, setPage] = useState(1);

  /* ---- 详情抽屉 ---- */
  const [openId, setOpenId] = useState(null);
  const [drawerTab, setDrawerTab] = useState('base');
  const openRecord = records.find(r => r.id === openId) || null;

  /* ---- 申请表单 ---- */
  const [form, setForm] = useState({
    catalog:'', org:'省民政厅信息中心', type:'有条件共享', term:'1 年', usage:'', pledge:false,
  });
  const [errs, setErrs] = useState({});
  const [confirmOpen, setConfirmOpen] = useState(false);

  /* ---- 我的申请 / 提示 ---- */
  const [applies, setApplies] = useState(MY_APPLIES);
  const [toast, setToast] = useState({ open:false, msg:'' });
  const toastTimer = useRef(null);

  function say(msg){
    setToast({ open:true, msg });
    clearTimeout(toastTimer.current);
    toastTimer.current = setTimeout(() => setToast(t => ({ ...t, open:false })), 2400);
  }

  /* ---- ESC 关闭浮层 ---- */
  useEffect(() => {
    const onKey = e => {
      if (e.key === 'Escape'){ setConfirmOpen(false); setOpenId(null); }
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, []);

  /* ---- 过滤 + 排序 ---- */
  const filtered = useMemo(() => {
    const q = kw.trim().toLowerCase();
    let rows = records.filter(r =>
      (!q || (r.name + r.org).toLowerCase().includes(q)) &&
      (share === '全部' || r.share === share)
    );
    const { key, dir } = sort;
    rows = rows.slice().sort((a, b) => {
      let x = a[key], y = b[key];
      if (typeof x === 'string'){ x = x.localeCompare(y, 'zh'); y = 0; }
      const d = typeof x === 'number' ? x - y : x;
      return dir === 'asc' ? d : -d;
    });
    return rows;
  }, [records, kw, share, sort]);

  const pages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const cur = Math.min(page, pages);
  const pageRows = filtered.slice((cur - 1) * PAGE_SIZE, cur * PAGE_SIZE);

  function changeSort(key){
    setSort(s => s.key === key
      ? { key, dir: s.dir === 'asc' ? 'desc' : 'asc' }
      : { key, dir: key === 'name' || key === 'org' ? 'asc' : 'desc' });
  }
  function goScreen(id){
    setScreen(id);
    if (id !== 'catalog') setOpenId(null);
    window.scrollTo(0, 0);
  }
  function openRecordById(id){
    setOpenId(id);
    setDrawerTab('base');
  }

  /* ---- 申请流程 ---- */
  function startApply(){
    const rec = openRecord;
    if (rec){
      setForm(f => ({
        ...f,
        catalog: rec.name,
        type: rec.share === '无条件共享' ? '无条件共享' : '有条件共享',
      }));
    }
    setErrs({});
    setOpenId(null);
    goScreen('apply');
  }
  function validate(){
    const e = {};
    if (!form.usage.trim()) e.usage = '请填写申请用途';
    else if (form.usage.trim().length < 10) e.usage = `申请用途不少于 10 字，当前 ${form.usage.trim().length} 字`;
    if (!form.pledge) e.pledge = '请勾选数据安全承诺';
    return e;
  }
  function submitApply(ev){
    ev.preventDefault();
    const e = validate();
    setErrs(e);
    if (Object.keys(e).length){ say(Object.values(e)[0]); return; }
    setConfirmOpen(true);
  }
  function confirmApply(){
    const no = 'SQ' + (1003 + applies.length - MY_APPLIES.length);
    setApplies(list => [{
      no, catalog: form.catalog || '（未选择目录）', org: form.org,
      term: form.term, time: nowStamp(), status: '待审核',
    }, ...list]);
    setRecords(rs => rs.map(r =>
      r.name === form.catalog && r.status === '已发布' ? { ...r, status:'待审核' } : r));
    setConfirmOpen(false);
    setForm(f => ({ ...f, usage:'', pledge:false }));
    setErrs({});
    goScreen('myapply');
    say('申请已提交，进入部门审核流程');
  }

  const myCount = applies.length;

  /* ================= 各屏 ================= */
  const ScreenWorkbench = (
    <section data-screen-label="工作台">
      <div className="kpis">
        {[['目录总数', 1284, ''], ['已发布', 967, 'var(--ok)'],
          ['待我审核', 48, 'var(--warn)'], ['我的申请', myCount, '']].map(([k, v, c]) => (
          <div className="kpi" key={k}>
            <span className="k">{k}</span>
            <span className="v" style={{ color: c || 'inherit' }}>{v}</span>
          </div>
        ))}
      </div>
      <div className="sect">待办</div>
      <div className="panel">
        <dl className="dl">
          <dt>共享申请</dt><dd>待审核 <b>48</b> 条，其中超期 <b>3</b> 条</dd>
          <dt>目录变更</dt><dd>待确认 6 条</dd>
          <dt>归集异常</dt><dd>2 个批次需要处理</dd>
        </dl>
      </div>
    </section>
  );

  const ScreenCatalog = (
    <section data-screen-label="数据资源目录">
      <div className="toolbar">
        <div className="search">
          <IconSearch />
          <input id="q" value={kw} placeholder="搜索目录名称或提供单位"
                 aria-label="搜索目录"
                 onChange={e => { setKw(e.target.value); setPage(1); }} />
        </div>
        <Segmented label="共享类型筛选" options={SHARE_FILTERS} value={share}
                   onChange={v => { setShare(v); setPage(1); }} />
        <span className="count" id="count-line">
          符合条件 {filtered.length} 条 / 全部 {records.length} 条
        </span>
        <button className="btn btn-primary spacer" id="btn-new"
                onClick={() => say('原型范围外：新建目录流程未展开')}>
          <IconPlus />新建目录
        </button>
      </div>

      <div className="panel">
        {pageRows.length
          ? <CatalogTable rows={pageRows} sort={sort} onSort={changeSort}
                          selectedId={openId} onOpen={openRecordById} />
          : <div className="empty">没有符合条件的目录，试试调整搜索词或共享类型</div>}
        {filtered.length > 0 && (
          <Pager page={cur} pages={pages} total={filtered.length} onPage={setPage} />
        )}
      </div>
    </section>
  );

  const ScreenGather = (
    <section data-screen-label="数据归集">
      <div className="kpis">
        {[['今日归集批次', 42, ''], ['归集记录', '1,286 万', ''], ['成功率', '99.2%', 'var(--ok)']]
          .map(([k, v, c]) => (
          <div className="kpi" key={k}><span className="k">{k}</span>
            <span className="v" style={{ color: c || 'inherit' }}>{v}</span></div>
        ))}
      </div>
      <div className="panel">
        <dl className="dl">
          <dt>异常批次</dt><dd>3 个批次失败，均为上游接口超时</dd>
          <dt>待处理工单</dt><dd>2 条</dd>
          <dt>最近一次成功</dt><dd>2026-10-07 09:12</dd>
        </dl>
      </div>
    </section>
  );

  const usageLen = form.usage.trim().length;
  const ScreenApply = (
    <section data-screen-label="共享申请">
      <div className="steps">
        {[['填写申请', true], ['部门审核', false], ['授权开通', false]].map(([label, on], i) => (
          <React.Fragment key={label}>
            {i > 0 && <span className="bar" />}
            <span className="s" data-on={on}><span className="d">{i + 1}</span>{label}</span>
          </React.Fragment>
        ))}
      </div>

      <form className="panel" style={{ padding:'20px 22px', maxWidth:'660px' }}
            id="apply-form" onSubmit={submitApply} noValidate>
        <div className="field">
          <label htmlFor="f-catalog"><span className="req">*</span>申请目录</label>
          <div className="ctl">
            <input className="inp" id="f-catalog" readOnly value={form.catalog}
                   placeholder="从「数据资源目录」点击目录行带入"
                   onChange={() => {}} />
            <div className="help">由目录详情抽屉的「申请共享」带入，也可在上方列表选择后带入</div>
          </div>
        </div>

        <div className="field">
          <label htmlFor="f-org"><span className="req">*</span>申请单位</label>
          <div className="ctl">
            <input className="inp" id="f-org" value={form.org}
                   onChange={e => setForm(f => ({ ...f, org:e.target.value }))} />
          </div>
        </div>

        <div className="field">
          <label htmlFor="f-type">共享类型</label>
          <div className="ctl">
            <select className="sel" id="f-type" value={form.type}
                    onChange={e => setForm(f => ({ ...f, type:e.target.value }))}>
              <option>有条件共享</option><option>无条件共享</option>
            </select>
          </div>
        </div>

        <div className="field">
          <label htmlFor="f-term">使用期限</label>
          <div className="ctl">
            <select className="sel" id="f-term" value={form.term}
                    onChange={e => setForm(f => ({ ...f, term:e.target.value }))}>
              {CYCLE_OPTIONS.map(t => <option key={t}>{t}</option>)}
            </select>
          </div>
        </div>

        <div className="field">
          <label htmlFor="f-usage"><span className="req">*</span>申请用途</label>
          <div className="ctl">
            <textarea className="ta" id="f-usage" value={form.usage}
                      placeholder="说明使用场景、数据范围，以及不用于其他用途的承诺（不少于 10 字）"
                      aria-invalid={!!errs.usage}
                      onChange={e => setForm(f => ({ ...f, usage:e.target.value }))} />
            <div className={'help' + (errs.usage ? ' err' : '')} id="usage-help">
              {errs.usage || `已输入 ${usageLen} 字`}
            </div>
          </div>
        </div>

        <div className="field">
          <label>数据安全承诺</label>
          <div className="ctl">
            <label className="check" htmlFor="f-pledge">
              <input type="checkbox" id="f-pledge" checked={form.pledge}
                     onChange={e => setForm(f => ({ ...f, pledge:e.target.checked }))} />
              <span>本单位承诺依法依规使用数据，落实分类分级保护要求，不向第三方转供。</span>
            </label>
            {errs.pledge && <div className="help err">{errs.pledge}</div>}
          </div>
        </div>

        <div style={{ display:'flex', gap:'8px', justifyContent:'flex-end', paddingTop:'4px' }}>
          <button type="button" className="btn btn-ghost" id="btn-cancel-apply"
                  onClick={() => goScreen('catalog')}>取消</button>
          <button type="submit" className="btn btn-primary" id="btn-submit">提交申请</button>
        </div>
      </form>
    </section>
  );

  const ScreenMyApply = (
    <section data-screen-label="我的申请">
      <div className="panel">
        {applies.length ? (
          <div className="scroll">
            <table>
              <thead><tr>
                <th style={{ width:'78px' }}>单号</th>
                <th>申请目录</th>
                <th style={{ width:'150px' }}>申请单位</th>
                <th style={{ width:'76px' }}>期限</th>
                <th style={{ width:'124px' }}>提交时间</th>
                <th style={{ width:'84px' }}>状态</th>
              </tr></thead>
              <tbody id="myapply-body">
                {applies.map(a => (
                  <tr key={a.no} style={{ cursor:'default' }}>
                    <td className="mono">{a.no}</td>
                    <td className="name">{a.catalog}</td>
                    <td className="org">{a.org}</td>
                    <td className="dim">{a.term}</td>
                    <td className="time">{a.time}</td>
                    <td><Status value={a.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : <div className="empty">暂无申请记录</div>}
      </div>
    </section>
  );

  const ScreenMonitor = (
    <section data-screen-label="监控管理">
      <div className="kpis">
        {[['接口调用', '8,624', ''], ['失败', 12, 'var(--danger)'], ['平均响应', '186 ms', '']]
          .map(([k, v, c]) => (
          <div className="kpi" key={k}><span className="k">{k}</span>
            <span className="v" style={{ color: c || 'inherit' }}>{v}</span></div>
        ))}
      </div>
      <div className="panel">
        <dl className="dl">
          <dt>告警</dt>
          <dd>
            <span className="st st-rev"><i />中</span>
            {' '}低保对象查询接口 5xx 占比 0.6%（近 1 小时）
          </dd>
          <dt>处置建议</dt><dd>检查上游汇聚任务 2026-10-07 批次是否延迟</dd>
        </dl>
      </div>
    </section>
  );

  const SCREENS = {
    workbench: ScreenWorkbench, catalog: ScreenCatalog, gather: ScreenGather,
    apply: ScreenApply, myapply: ScreenMyApply, monitor: ScreenMonitor,
  };

  const TITLES = {
    workbench:['工作台','首页 / 工作台'],
    catalog:['数据资源目录','首页 / 数据管理 / 数据资源目录'],
    gather:['数据归集','首页 / 数据管理 / 数据归集'],
    apply:['共享申请','首页 / 服务与运营 / 共享申请'],
    myapply:['我的申请','首页 / 服务与运营 / 我的申请'],
    monitor:['监控管理','首页 / 服务与运营 / 监控管理'],
  };

  return (
    <>
      {/* ⚠️ 结构要点：浮层（抽屉/弹窗/Toast）必须放在 .app 之外。
          .app 是 display:grid 容器，若浮层作为它的子元素，会被当成 grid item 排进下一行；
          浏览器里 position:fixed 能侥幸脱流，但静态渲染器会真的把它排到内容下方。
          放在 grid 之外才是正确结构。 */}
      <div className="app">
        <Sidebar screen={screen} onGo={goScreen} myCount={myCount} />
        <div className="main">
          <div className="head">
            <div>
              <h1>{TITLES[screen][0]}</h1>
              <div className="path">{TITLES[screen][1]}</div>
            </div>
            <div className="right">
              <button className="icon-btn" id="btn-theme" aria-label="切换深色模式"
                      title="切换深色 / 浅色"
                      onClick={() => setTheme(t => t === 'light' ? 'dark' : 'light')}>
                {theme === 'light' ? <IconMoon /> : <IconSun />}
              </button>
            </div>
          </div>
          <div className="body" id="screen-body">
            {SCREENS[screen]}
          </div>
        </div>
      </div>

      <DetailDrawer open={!!openRecord} record={openRecord} tab={drawerTab}
                    onTab={setDrawerTab} onClose={() => setOpenId(null)}
                    onApply={startApply} />

      <ConfirmModal open={confirmOpen}
                    text={`申请目录：${form.catalog || '—'}；使用期限：${form.term}。提交后进入部门审核流程。`}
                    onCancel={() => setConfirmOpen(false)}
                    onOk={confirmApply} />

      <Toast msg={toast.msg} open={toast.open} />
    </>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />);

/* 供自动化测试驱动（jsdom）。仅暴露只读查询与少量动作，不改设计逻辑。 */
window.__proto = {
  screen: () => (document.querySelector('[aria-current="page"]') || {}).id,
  rows: () => document.querySelectorAll('tbody#myapply-body tr, .panel tbody tr').length,
  rowCount: () => document.querySelectorAll('.panel tbody tr').length,
  drawerOpen: () => document.querySelector('.drawer').getAttribute('data-open') === 'true',
  modalOpen: () => document.querySelector('.modal').getAttribute('data-open') === 'true',
  toast: () => document.querySelector('.toast').textContent,
  toastOpen: () => document.querySelector('.toast').getAttribute('data-open') === 'true',
  theme: () => document.documentElement.getAttribute('data-theme'),
  activeTab: () => (document.querySelector('.tabs [aria-selected="true"]') || {}).textContent,
  applyRows: () => document.querySelectorAll('#myapply-body tr').length,
  countLine: () => document.querySelector('#count-line').textContent.trim(),
};
document.documentElement.setAttribute('data-ready', '1');

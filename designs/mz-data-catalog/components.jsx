/* components.jsx — 呈现组件：props 进，回调出，自身不持有应用状态 */

const { fmtNum, sizeText, shareClass, statusClass } = window;

/* ---------- 侧栏 ---------- */
const NAV = [
  { grp:'数据管理', items:[
      { id:'workbench', label:'工作台',        icon:'IconGrid' },
      { id:'catalog',   label:'数据资源目录',  icon:'IconLayers', badge:1284 },
      { id:'gather',    label:'数据归集',      icon:'IconFlow' },
  ]},
  { grp:'服务与运营', items:[
      { id:'apply',     label:'共享申请',      icon:'IconShare' },
      { id:'myapply',   label:'我的申请',      icon:'IconInbox', badge:0 },
      { id:'monitor',   label:'监控管理',      icon:'IconMonitor' },
  ]},
];

function Sidebar({ screen, onGo, myCount }){
  return (
    <aside className="side">
      <div className="brand">
        <div className="mark">民</div>
        <div>
          <div className="name">数据资源管理</div>
          <div className="sub">省民政厅 · 数据管理组</div>
        </div>
      </div>
      <nav className="nav" aria-label="主导航">
        {NAV.map(g => (
          <div key={g.grp}>
            <div className="grp">{g.grp}</div>
            {g.items.map(it => {
              const I = window[it.icon];
              const badge = it.id === 'myapply' ? myCount : it.badge;
              return (
                <button key={it.id} type="button"
                        aria-current={screen === it.id ? 'page' : undefined}
                        id={`nav-${it.id}`}
                        onClick={() => onGo(it.id)}>
                  <I />
                  <span>{it.label}</span>
                  {badge ? <span className="badge">{badge.toLocaleString('zh-CN')}</span> : null}
                </button>
              );
            })}
          </div>
        ))}
      </nav>
      <div className="side-foot">
        <div className="who">邵</div>
        <span>邵雷 · 数据管理组</span>
      </div>
    </aside>
  );
}

/* ---------- 分段控件 ---------- */
function Segmented({ options, value, onChange, label }){
  return (
    <div className="seg" role="group" aria-label={label}>
      {options.map(o => (
        <button key={o} type="button"
                aria-pressed={value === o}
                data-value={o}
                onClick={() => onChange(o)}>{o}</button>
      ))}
    </div>
  );
}

/* ---------- 状态 / 共享类型 ---------- */
const Status = ({ value }) => (
  <span className={statusClass(value)}><i />{value}</span>
);
const Share = ({ value }) => (
  <span className={shareClass(value)}>{value}</span>
);

/* ---------- 目录表 ---------- */
const COLS = [
  { key:'name',    label:'目录名称',   cls:'name', sortable:true,  width:'auto' },
  { key:'org',     label:'提供单位',   cls:'org',  sortable:true,  width:'178px' },
  { key:'share',   label:'共享类型',   cls:'',     sortable:false, width:'96px' },
  { key:'size',    label:'数据量',     cls:'dim',  sortable:true,  width:'92px' },
  { key:'updated', label:'更新时间',   cls:'time', sortable:true,  width:'100px' },
  { key:'status',  label:'状态',       cls:'',     sortable:false, width:'84px' },
];

function CatalogTable({ rows, sort, onSort, selectedId, onOpen }){
  return (
    <div className="scroll">
      <table>
        <thead>
          <tr>
            {COLS.map(c => (
              <th key={c.key} style={{ width:c.width }}
                  className={c.sortable ? 'sortable' : ''}
                  scope="col"
                  onClick={c.sortable ? () => onSort(c.key) : undefined}>
                {c.label}
                {c.sortable && sort.key === c.key
                  ? <span className="arrow">{sort.dir === 'asc' ? '↑' : '↓'}</span>
                  : null}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map(r => (
            <tr key={r.id} data-id={r.id}
                aria-selected={selectedId === r.id}
                onClick={() => onOpen(r.id)}>
              <td className={COLS[0].cls}>{r.name}</td>
              <td className={COLS[1].cls}>{r.org}</td>
              <td><Share value={r.share} /></td>
              <td className={COLS[3].cls}>{sizeText(r.size)}</td>
              <td className={COLS[4].cls}>{r.updated}</td>
              <td><Status value={r.status} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/* ---------- 分页 ---------- */
function Pager({ page, pages, total, onPage }){
  const nums = [];
  for (let p = 1; p <= pages; p++){
    if (pages > 7 && p > 2 && p < pages - 1 && Math.abs(p - page) > 1){
      if (nums[nums.length - 1] !== '…') nums.push('…');
      continue;
    }
    nums.push(p);
  }
  return (
    <div className="pager">
      <span className="count">共 {fmtNum(total)} 条</span>
      <span className="spacer" />
      <button className="pg" id="pg-prev" disabled={page <= 1}
              onClick={() => onPage(page - 1)}>上一页</button>
      {/* 注意：不能用 <span style={{display:'contents'}}> 包裹页码 —— 非浏览器渲染器
          不支持 display:contents，会导致这些按钮不再是 flex item 而错位换行。用 Fragment。 */}
      {nums.map((n, i) => n === '…'
        ? <span key={'d' + i} style={{ color:'var(--text-3)', padding:'0 2px' }}>…</span>
        : <button key={n} className="pg" data-page={n}
                  aria-current={n === page}
                  onClick={() => onPage(n)}>{n}</button>)}
      <button className="pg" id="pg-next" disabled={page >= pages}
              onClick={() => onPage(page + 1)}>下一页</button>
    </div>
  );
}

/* ---------- 详情抽屉 ---------- */
function DetailDrawer({ open, record, tab, onTab, onClose, onApply }){
  const r = record;
  return (
    <>
      <div className="scrim" data-open={open} onClick={onClose} />
      <aside className="drawer" data-open={open} data-screen-label="目录详情"
             role="dialog" aria-modal="true" aria-labelledby="drawer-title">
        <header>
          <div style={{ minWidth:0 }}>
            <h2 id="drawer-title">{r ? r.name : '—'}</h2>
            <div className="code">{r ? r.code : ''}</div>
          </div>
          <button className="icon-btn close" id="btn-drawer-close"
                  onClick={onClose} aria-label="关闭"><IconClose /></button>
        </header>

        <div className="dbody">
          <div className="tabs" role="tablist">
            {[['base','基本信息'],['fields','字段信息'],['share','共享属性']].map(([k, label]) => (
              <button key={k} type="button" role="tab"
                      id={`tab-${k}`}
                      aria-selected={tab === k}
                      onClick={() => onTab(k)}>{label}</button>
            ))}
          </div>

          {r && tab === 'base' && (
            <dl className="dl">
              <dt>目录名称</dt><dd>{r.name}</dd>
              <dt>目录编码</dt><dd className="mono">{r.code}</dd>
              <dt>提供单位</dt><dd>{r.org}</dd>
              <dt>共享类型</dt><dd><Share value={r.share} /></dd>
              <dt>数据量</dt><dd>{sizeText(r.size)}</dd>
              <dt>更新周期</dt><dd>{r.cycle}</dd>
              <dt>更新时间</dt><dd>{r.updated}</dd>
              <dt>资源摘要</dt><dd className="note">{r.desc}</dd>
            </dl>
          )}

          {r && tab === 'fields' && (
            <div className="scroll">
              <table>
                <thead><tr>
                  <th style={{ width:'132px' }}>字段名</th>
                  <th style={{ width:'84px' }}>类型</th>
                  <th>说明</th>
                </tr></thead>
                <tbody>
                  {r.fields.map(f => (
                    <tr key={f[0]} style={{ cursor:'default' }}>
                      <td className="mono">{f[0].replace(/_ys$/, '')}</td>
                      <td style={{ color:'var(--text-2)', fontSize:'12px' }}>{f[1]}</td>
                      <td>{f[2]}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {r && tab === 'share' && (
            <dl className="dl">
              <dt>共享方式</dt><dd>库表订阅 · API 接口 · 文件下载</dd>
              <dt>授权对象</dt><dd>省直部门、市（州）民政部门</dd>
              <dt>敏感级别</dt><dd><span className="st"><i style={{
                  width:'6px',height:'6px',borderRadius:'50%',display:'block',
                  background: r.level === '高' ? 'var(--danger)'
                            : r.level === '中' ? 'var(--warn)' : 'var(--ok)'
                }} />{r.level} 级</span></dd>
              <dt>是否脱敏</dt><dd>{r.masked ? '是（身份证号、住址等敏感字段）' : '否'}</dd>
              <dt>安全要求</dt>
              <dd className="note">
                {r.masked
                  ? '使用方须落实分类分级保护，敏感字段不得还原，不得向第三方转供。'
                  : '按开放共享管理规定使用，保留数据来源标注。'}
              </dd>
            </dl>
          )}
        </div>

        <div className="dfoot">
          <button className="btn btn-ghost" id="btn-drawer-close2" onClick={onClose}>关闭</button>
          <button className="btn btn-primary" id="btn-go-apply"
                  disabled={!r || r.status === '已下架'}
                  onClick={onApply}>申请共享</button>
        </div>
      </aside>
    </>
  );
}

/* ---------- 确认弹窗 ---------- */
function ConfirmModal({ open, text, onCancel, onOk }){
  return (
    <>
      <div className="scrim" data-open={open} onClick={onCancel} />
      <div className="modal" data-open={open} role="dialog" aria-modal="true"
           aria-labelledby="modal-title" data-screen-label="提交确认">
        <h3 id="modal-title">确认提交申请</h3>
        <div className="mbody" id="modal-body">{text}</div>
        <div className="mfoot">
          <button className="btn btn-ghost" id="btn-modal-cancel" onClick={onCancel}>再改改</button>
          <button className="btn btn-primary" id="btn-modal-ok" onClick={onOk}>确认提交</button>
        </div>
      </div>
    </>
  );
}

/* ---------- 提示条 ---------- */
const Toast = ({ msg, open }) => (
  <div className="toast" data-open={open} role="status" aria-live="polite">{msg}</div>
);

Object.assign(window, {
  NAV, Sidebar, Segmented, Status, Share, CatalogTable, Pager,
  DetailDrawer, ConfirmModal, Toast,
});

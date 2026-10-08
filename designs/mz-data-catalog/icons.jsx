/* icons.jsx — 统一的线性图标（16px，stroke 1.6，继承 currentColor）
   图标是 UI 元件，不是「用 SVG 代替图片」——skill 禁止的是后者。 */

const Ico = ({ d, size = 16, fill = 'none', children }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill={fill}
       stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"
       aria-hidden="true">
    {d ? <path d={d} /> : children}
  </svg>
);

const IconSearch   = p => <Ico {...p}><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></Ico>;
const IconSun      = p => <Ico {...p}><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M19.1 4.9l-1.4 1.4M6.3 17.7l-1.4 1.4"/></Ico>;
const IconMoon     = p => <Ico {...p}><path d="M20 14.5A8.5 8.5 0 1 1 9.5 4a6.8 6.8 0 0 0 10.5 10.5z"/></Ico>;
const IconClose    = p => <Ico {...p} d="M6 6l12 12M18 6L6 18"/>;
const IconPlus     = p => <Ico {...p} d="M12 5v14M5 12h14"/>;
const IconChevL    = p => <Ico {...p} d="M14.5 6l-6 6 6 6"/>;
const IconChevR    = p => <Ico {...p} d="M9.5 6l6 6-6 6"/>;
const IconCloseSm  = p => <Ico {...p} d="M7 7l10 10M17 7L7 17"/>;
const IconGrid     = p => <Ico {...p}><rect x="3.5" y="3.5" width="7" height="7" rx="1.5"/><rect x="13.5" y="3.5" width="7" height="7" rx="1.5"/><rect x="3.5" y="13.5" width="7" height="7" rx="1.5"/><rect x="13.5" y="13.5" width="7" height="7" rx="1.5"/></Ico>;
const IconLayers   = p => <Ico {...p} d="M12 3.5l8.5 4.5L12 12.5 3.5 8zM3.5 12.5L12 17l8.5-4.5"/>;
const IconFlow     = p => <Ico {...p} d="M5 6h6a3 3 0 0 1 3 3v6M14 15l-2.5-2.5M14 15l2.5-2.5M4 6h.01M20 18h-6"/>;
const IconShare    = p => <Ico {...p}><circle cx="17.5" cy="6" r="2.6"/><circle cx="6.5" cy="12" r="2.6"/><circle cx="17.5" cy="18" r="2.6"/><path d="M9 10.7l6-3.2M9 13.3l6 3.2"/></Ico>;
const IconShield   = p => <Ico {...p} d="M12 3l7 3v6c0 4.4-3 7.6-7 9-4-1.4-7-4.6-7-9V6z"/>;
const IconMonitor  = p => <Ico {...p}><rect x="3.5" y="4.5" width="17" height="12" rx="2"/><path d="M9 20h6M12 16.5V20"/></Ico>;
const IconInbox    = p => <Ico {...p} d="M3.5 13.5h4l1.5 2.5h6l1.5-2.5h4M4.5 5.5h15l-1.5 8h-12z"/>;
const IconDoc      = p => <Ico {...p}><path d="M6 3.5h7l5 5v12H6z"/><path d="M13 3.5v5h5"/></Ico>;
const IconSort     = p => <Ico {...p} d="M8 5v14M5 8l3-3 3 3M16 19V5M13 16l3 3 3-3"/>;
const IconCheck    = p => <Ico {...p} d="M5 12.5l4.5 4.5L19 7.5"/>;
const IconWarn     = p => <Ico {...p} d="M12 4.5l8.5 15h-17zM12 10v4M12 17h.01"/>;
const IconLock     = p => <Ico {...p}><rect x="5" y="10.5" width="14" height="9.5" rx="2"/><path d="M8.5 10.5V8a3.5 3.5 0 0 1 7 0v2.5"/></Ico>;

Object.assign(window, {
  Ico, IconSearch, IconSun, IconMoon, IconClose, IconPlus,
  IconChevL, IconChevR, IconCloseSm, IconGrid, IconLayers, IconFlow,
  IconShare, IconShield, IconMonitor, IconInbox, IconDoc, IconSort,
  IconCheck, IconWarn, IconLock,
});

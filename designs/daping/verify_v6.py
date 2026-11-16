# -*- coding: utf-8 -*-
"""v6 真机验证：× 统一为「返回上一页」+ 13 屏全链路回归"""
import pathlib
from playwright.sync_api import sync_playwright

CH = '/opt/data/chrome/shell/chrome-headless-shell-linux64/chrome-headless-shell'
HTML = 'file:///opt/data/designs/daping/四川省一体化数据平台_大屏交互.html'
OUT = pathlib.Path('/opt/data/designs/daping/_shots')
OUT.mkdir(parents=True, exist_ok=True)
for f in OUT.glob('[0-9]*.png'):
    f.unlink()

fails = []
def chk(name, cond, extra=''):
    print(f'  {"✅" if cond else "❌"} {name}{("  " + str(extra)) if extra else ""}')
    if not cond:
        fails.append(name)

def cur(pg):
    return pg.evaluate("window.__daping.current()")

def act(pg):
    return pg.evaluate("[...document.querySelectorAll('.hot.act')].map(a=>a.id)")

def ratio(pg):
    return pg.evaluate("(()=>{const r=document.querySelector('#frame').getBoundingClientRect();return Math.round(r.width/r.height*1000)/1000})()")

def go(pg, sid):
    pg.evaluate(f"window.__daping.go('{sid}')"); pg.wait_for_timeout(320)

SCREENS = {
    'home':        ('首页',                 '2276x1280', 4),
    'sjzl':        ('数据治理',              '2276x1280', 4),
    'sjfn':        ('数据赋能(法人)',         '2276x1280', 3),
    'sjfn_dfn':    ('数据赋能-数据赋能',       '2276x1280', 4),
    'sjfn_yjs':    ('支撑高效办成一件事',      '2276x1280', 4),
    'sjfn_zrr':    ('自然人',                '2276x1280', 2),
    'sjfn_zrr_ld': ('人口流动',              '2276x1280', 2),
    'sjhj':        ('数据汇聚',              '2048x1280', 5),
    'sjhj_bm':     ('数据编目',              '2276x1280', 3),
    'sjhj_hj':     ('汇聚更新弹层',           '2048x1280', 3),
    'sjhj_zrrku':  ('自然人库汇聚弹层',        '2048x1280', 3),
    'sjhj_frku':   ('法人库汇聚弹层',         '2048x1280', 3),
    'sjaq':        ('数据安全',              '2466x1280', 1),
}

with sync_playwright() as p:
    b = p.chromium.launch(executable_path=CH, args=['--no-sandbox', '--disable-gpu'])
    pg = b.new_page(viewport={'width': 1600, 'height': 900})
    errs = []
    pg.on('console', lambda m: errs.append(m.text) if m.type == 'error' else None)
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(HTML); pg.wait_for_timeout(1500)

    print('═══ 基础 ═══')
    chk('无 JS 报错', not errs, errs[:2])
    chk('13 屏 DOM', pg.evaluate("document.querySelectorAll('.screen').length") == 13,
        pg.evaluate("document.querySelectorAll('.screen').length"))
    chk('热区 41 个', pg.evaluate("window.__daping.hotspotCount") == 41,
        pg.evaluate("window.__daping.hotspotCount"))
    chk('初始首页', cur(pg) == 'home')

    print('\n═══ × 返回测试：4 个弹层各自回到进来的那一页 ═══')
    # (起点, 点击进入, 期望返回到)
    cases = [
        ('sjhj', '#hot-sjhj-n3', 'sjhj_zrrku', 'sjhj',      '自然人库汇聚'),
        ('sjhj', '#hot-sjhj-n4', 'sjhj_frku',  'sjhj',      '法人库汇聚'),
        ('sjhj', '#hot-sjhj-n1', 'sjhj_bm',    'sjhj',      '数据编目'),
        ('sjhj', '#hot-sjhj-n2', 'sjhj_hj',    'sjhj',      '汇聚更新'),
        ('sjhj_bm', '#hot-sjhj_bm-n1', 'sjhj_hj', 'sjhj_bm', '编目→汇聚更新'),
    ]
    for start, click, mid, expect_back, label in cases:
        go(pg, start)
        pg.click(click); pg.wait_for_timeout(450)
        ok1 = cur(pg) == mid
        pg.click(f'#hot-{mid}-close'); pg.wait_for_timeout(450)
        ok2 = cur(pg) == expect_back
        chk(f'{label}：× 返回 {expect_back}', ok1 and ok2, f'进入={cur(pg) if not ok1 else mid}')

    print('\n═══ × 兜底：直接打开弹层页（无历史）→ × 回数据汇聚 ═══')
    pg2 = b.new_page(viewport={'width': 1400, 'height': 800})
    pg2.goto(HTML + '#sjhj_zrrku'); pg2.wait_for_timeout(1200)
    chk('直开落在弹层页', cur(pg2) == 'sjhj_zrrku', cur(pg2))
    pg2.click('#hot-sjhj_zrrku-close'); pg2.wait_for_timeout(450)
    chk('× 兜底回数据汇聚', cur(pg2) == 'sjhj', cur(pg2))
    pg2.close()

    print('\n═══ 只有 4 个页面有「返回」型热区 ═══')
    r = pg.evaluate("""(()=>{const m={};document.querySelectorAll('.hot[data-back]').forEach(a=>{
        const s=a.getAttribute('data-scr'); m[s]=(m[s]||0)+1});return m})()""")
    chk('返回热区落在 4 个弹层页', len(r) == 4 and all(v == 1 for v in r.values()), r)
    chk('无图片的页面乱加 ×', set(r) == {'sjhj_bm', 'sjhj_hj', 'sjhj_zrrku', 'sjhj_frku'}, set(r))

    print('\n═══ 全链路回归 ═══')
    go(pg, 'home')
    pg.click('#hot-home-n2'); pg.wait_for_timeout(450)
    chk('首页→数据治理', cur(pg) == 'sjzl', cur(pg))
    chk('治理 4 热区', len(act(pg)) == 4, act(pg))
    pg.click('#hot-sjzl-n2'); pg.wait_for_timeout(450)
    chk('治理→数据赋能', cur(pg) == 'sjfn', cur(pg))
    go(pg, 'sjzl'); pg.click('#hot-sjzl-n3'); pg.wait_for_timeout(450)
    chk('治理→数据安全', cur(pg) == 'sjaq', cur(pg))
    go(pg, 'sjzl'); pg.click('#hot-sjzl-n1'); pg.wait_for_timeout(450)
    chk('治理→数据汇聚', cur(pg) == 'sjhj', cur(pg))
    go(pg, 'sjzl'); pg.click('#hot-t-sjzl'); pg.wait_for_timeout(450)
    chk('治理标题→首页', cur(pg) == 'home', cur(pg))
    go(pg, 'sjfn'); pg.click('#hot-sjfn-n1'); pg.wait_for_timeout(450)
    chk('法人页→数据赋能页', cur(pg) == 'sjfn_dfn', cur(pg))
    pg.click('#hot-sjfn_dfn-n3'); pg.wait_for_timeout(450)
    chk('→支撑高效办成一件事', cur(pg) == 'sjfn_yjs', cur(pg))
    pg.click('#hot-sjfn_yjs-n3'); pg.wait_for_timeout(450)
    chk('→切回支撑部门场景应用', cur(pg) == 'sjfn_dfn', cur(pg))
    pg.click('#hot-sjfn_dfn-n1'); pg.wait_for_timeout(450)
    chk('→自然人', cur(pg) == 'sjfn_zrr', cur(pg))
    pg.click('#hot-sjfn_zrr-ld'); pg.wait_for_timeout(450)
    chk('→人口流动', cur(pg) == 'sjfn_zrr_ld', cur(pg))
    pg.click('#hot-sjfn_zrr_ld-hj'); pg.wait_for_timeout(450)
    chk('→切回自然人', cur(pg) == 'sjfn_zrr', cur(pg))

    print('\n═══ 13 屏逐屏核对：尺寸 / 无滤镜 / 热区数 ═══')
    for sid, (nm, nat, cnt) in SCREENS.items():
        go(pg, sid)
        r = pg.evaluate(f"""(()=>{{const i=document.querySelector('#scr-{sid} img.shot');
          if(!i)return null;const s=getComputedStyle(i);
          return {{nat:i.naturalWidth+'x'+i.naturalHeight,filter:s.filter,opacity:s.opacity,
                   fit:s.objectFit,act:document.querySelectorAll('.hot.act').length}}}})()""")
        ok = (r and r['nat'] == nat and r['filter'] == 'none'
              and r['opacity'] == '1' and r['act'] == cnt)
        chk(f'{nm} {nat} 热区{cnt}', ok, r)

    print('\n═══ 画幅 / 键盘 / 路由 ═══')
    for sid, want in [('home', 2276/1280), ('sjhj', 2048/1280), ('sjaq', 2466/1280)]:
        go(pg, sid)
        chk(f'{sid} 画幅', abs(ratio(pg) - want) < 0.02, ratio(pg))
    go(pg, 'sjfn_yjs')
    pg.keyboard.press('Escape'); pg.wait_for_timeout(350)
    chk('ESC 回首页', cur(pg) == 'home')
    pg.evaluate("location.hash='#sjhj_zrrku'"); pg.wait_for_timeout(500)
    chk('hash 路由', cur(pg) == 'sjhj_zrrku', cur(pg))

    print('\n═══ 汇总 ═══')
    print(f'  {"✅ 全部通过" if not fails else "❌ 失败 " + str(len(fails)) + " 项"}')
    for f in fails:
        print(f'     - {f}')
    b.close()

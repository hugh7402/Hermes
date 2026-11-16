# -*- coding: utf-8 -*-
"""v5 真机验证：13 屏全链路 + 尺寸/画幅自适应 + 图片零改动"""
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
    'sjhj_bm':     ('数据编目',              '2276x1280', 2),
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
    chk('热区 40 个', pg.evaluate("window.__daping.hotspotCount") == 40,
        pg.evaluate("window.__daping.hotspotCount"))
    chk('初始首页', cur(pg) == 'home')
    chk('首页 4 热区', len(act(pg)) == 4, act(pg))
    pg.screenshot(path=str(OUT / '01_首页.png'))

    print('\n═══ 数据治理页（新图，带 4 导航）═══')
    pg.click('#hot-home-n2'); pg.wait_for_timeout(500)
    chk('首页→数据治理', cur(pg) == 'sjzl', cur(pg))
    chk('热区=标题+3导航', len(act(pg)) == 4, act(pg))
    pg.screenshot(path=str(OUT / '02_数据治理.png'))
    pg.click('#hot-sjzl-n2'); pg.wait_for_timeout(450)
    chk('治理→数据赋能', cur(pg) == 'sjfn', cur(pg))
    go(pg, 'sjzl')
    pg.click('#hot-sjzl-n3'); pg.wait_for_timeout(450)
    chk('治理→数据安全', cur(pg) == 'sjaq', cur(pg))
    go(pg, 'sjzl')
    pg.click('#hot-sjzl-n1'); pg.wait_for_timeout(450)
    chk('治理→数据汇聚', cur(pg) == 'sjhj', cur(pg))
    go(pg, 'sjzl')
    pg.click('#hot-t-sjzl'); pg.wait_for_timeout(450)
    chk('治理点标题→首页', cur(pg) == 'home', cur(pg))

    print('\n═══ 数据汇聚支线（5 条路径）═══')
    go(pg, 'sjhj')
    chk('数据汇聚 5 热区', len(act(pg)) == 5, act(pg))
    pg.screenshot(path=str(OUT / '03_数据汇聚.png'))
    pg.click('#hot-sjhj-n1'); pg.wait_for_timeout(450)
    chk('→数据编目', cur(pg) == 'sjhj_bm', cur(pg))
    pg.screenshot(path=str(OUT / '04_数据编目.png'))
    pg.click('#hot-sjhj_bm-n1'); pg.wait_for_timeout(450)
    chk('编目→汇聚更新', cur(pg) == 'sjhj_hj', cur(pg))
    pg.click('#hot-sjhj_hj-close'); pg.wait_for_timeout(450)
    chk('汇聚更新 ×→数据汇聚', cur(pg) == 'sjhj', cur(pg))
    pg.click('#hot-sjhj-n2'); pg.wait_for_timeout(450)
    chk('→汇聚更新（从汇聚页）', cur(pg) == 'sjhj_hj', cur(pg))
    pg.screenshot(path=str(OUT / '05_汇聚更新.png'))
    go(pg, 'sjhj')
    pg.click('#hot-sjhj-n3'); pg.wait_for_timeout(450)
    chk('→自然人库汇聚', cur(pg) == 'sjhj_zrrku', cur(pg))
    pg.screenshot(path=str(OUT / '06_自然人库汇聚.png'))
    pg.click('#hot-sjhj_zrrku-close'); pg.wait_for_timeout(450)
    chk('自然人库 ×→数据汇聚', cur(pg) == 'sjhj', cur(pg))
    pg.click('#hot-sjhj-n4'); pg.wait_for_timeout(450)
    chk('→法人库汇聚', cur(pg) == 'sjhj_frku', cur(pg))
    pg.screenshot(path=str(OUT / '07_法人库汇聚.png'))
    pg.click('#hot-sjhj_frku-close'); pg.wait_for_timeout(450)
    chk('法人库 ×→数据汇聚', cur(pg) == 'sjhj', cur(pg))

    print('\n═══ 数据赋能支线 ═══')
    go(pg, 'sjfn')
    pg.click('#hot-sjfn-n1'); pg.wait_for_timeout(450)
    chk('法人页→数据赋能页', cur(pg) == 'sjfn_dfn', cur(pg))
    chk('dfn 4 热区', len(act(pg)) == 4, act(pg))
    pg.screenshot(path=str(OUT / '08_数据赋能_数据赋能.png'))
    pg.click('#hot-sjfn_dfn-n3'); pg.wait_for_timeout(450)
    chk('→支撑高效办成一件事', cur(pg) == 'sjfn_yjs', cur(pg))
    pg.screenshot(path=str(OUT / '09_高效办成一件事.png'))
    pg.click('#hot-sjfn_yjs-n3'); pg.wait_for_timeout(450)
    chk('→支撑部门场景应用情况（切回）', cur(pg) == 'sjfn_dfn', cur(pg))
    pg.click('#hot-sjfn_dfn-n2'); pg.wait_for_timeout(450)
    chk('dfn→法人页', cur(pg) == 'sjfn', cur(pg))
    go(pg, 'sjfn_dfn')
    pg.click('#hot-sjfn_dfn-n1'); pg.wait_for_timeout(450)
    chk('dfn→自然人', cur(pg) == 'sjfn_zrr', cur(pg))
    pg.screenshot(path=str(OUT / '10_自然人.png'))
    pg.click('#hot-sjfn_zrr-ld'); pg.wait_for_timeout(450)
    chk('→人口流动', cur(pg) == 'sjfn_zrr_ld', cur(pg))
    pg.screenshot(path=str(OUT / '11_人口流动.png'))
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

    print('\n═══ 画幅按屏自适应 ═══')
    for sid, want in [('home', 2276/1280), ('sjhj', 2048/1280), ('sjaq', 2466/1280)]:
        go(pg, sid)
        chk(f'{sid} 画幅 {want:.3f}', abs(ratio(pg) - want) < 0.02, ratio(pg))

    print('\n═══ 键盘 / 路由 ═══')
    go(pg, 'sjfn_yjs')
    pg.keyboard.press('Escape'); pg.wait_for_timeout(350)
    chk('ESC 回首页', cur(pg) == 'home')
    pg.evaluate("location.hash='#sjhj_zrrku'"); pg.wait_for_timeout(500)
    chk('hash 路由', cur(pg) == 'sjhj_zrrku', cur(pg))
    pg.evaluate("location.hash='#sjzl'"); pg.wait_for_timeout(500)
    chk('hash 路由 #sjzl', cur(pg) == 'sjzl', cur(pg))

    print('\n═══ 汇总 ═══')
    print(f'  {"✅ 全部通过" if not fails else "❌ 失败 " + str(len(fails)) + " 项"}')
    for f in fails:
        print(f'     - {f}')
    print(f'  截图 {len(list(OUT.glob("[0-9]*.png")))} 张')
    b.close()

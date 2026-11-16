# -*- coding: utf-8 -*-
"""v4 真机验证：8 屏全链路 + 尺寸/画幅自适应"""
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

def frame_ratio(pg):
    return pg.evaluate("(()=>{const f=document.querySelector('#frame');const r=f.getBoundingClientRect();return Math.round(r.width/r.height*1000)/1000})()")

IMGS = {
    'home':         ('首页',            '2276x1280', 4),
    'sjzl':         ('数据治理',         '2276x1280', 2),
    'sjfn':         ('数据赋能(法人)',    '2276x1280', 3),
    'sjfn_dfn':     ('数据赋能-数据赋能',  '2276x1280', 3),
    'sjfn_zrr':     ('自然人',          '2276x1280', 2),
    'sjfn_zrr_ld':  ('人口流动',        '2276x1280', 2),
    'sjaq':         ('数据安全',        '2466x1280', 1),
}

with sync_playwright() as p:
    b = p.chromium.launch(executable_path=CH, args=['--no-sandbox', '--disable-gpu'])
    pg = b.new_page(viewport={'width': 1600, 'height': 900})
    errs = []
    pg.on('console', lambda m: errs.append(m.text) if m.type == 'error' else None)
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(HTML); pg.wait_for_timeout(1200)

    print('═══ 基础 ═══')
    chk('无 JS 报错', not errs, errs[:2])
    chk('8 屏 DOM', pg.evaluate("document.querySelectorAll('.screen').length") == 8,
        pg.evaluate("document.querySelectorAll('.screen').length"))
    chk('热区 18 个', pg.evaluate("window.__daping.hotspotCount") == 18,
        pg.evaluate("window.__daping.hotspotCount"))
    chk('初始首页', cur(pg) == 'home')
    chk('首页 4 个生效热区', len(act(pg)) == 4, act(pg))
    pg.screenshot(path=str(OUT / '1_首页.png'))

    print('\n═══ 首页 → 数据赋能（法人页）═══')
    pg.click('#hot-home-n3'); pg.wait_for_timeout(500)
    chk('到 sjfn', cur(pg) == 'sjfn', cur(pg))
    chk('生效热区 3 个', len(act(pg)) == 3, act(pg))
    pg.screenshot(path=str(OUT / '2_数据赋能_法人.png'))

    print('\n═══ 法人页 → 导航「数据赋能」→ 三级数据赋能 ═══')
    pg.click('#hot-sjfn-n1'); pg.wait_for_timeout(500)
    chk('到 sjfn_dfn', cur(pg) == 'sjfn_dfn', cur(pg))
    chk('生效热区 3 个', len(act(pg)) == 3, act(pg))
    pg.screenshot(path=str(OUT / '3_三级_数据赋能.png'))

    print('\n═══ 三级数据赋能 → 导航「法人」→ 回法人页 ═══')
    pg.click('#hot-sjfn_dfn-n2'); pg.wait_for_timeout(500)
    chk('回到 sjfn', cur(pg) == 'sjfn', cur(pg))

    print('\n═══ 法人页 → 导航「自然人」═══')
    pg.click('#hot-sjfn-n2'); pg.wait_for_timeout(500)
    chk('到自然人页', cur(pg) == 'sjfn_zrr', cur(pg))
    pg.screenshot(path=str(OUT / '4_自然人.png'))

    print('\n═══ 三级数据赋能 → 导航「自然人」也通 ═══')
    pg.evaluate("window.__daping.go('sjfn_dfn')"); pg.wait_for_timeout(400)
    pg.click('#hot-sjfn_dfn-n1'); pg.wait_for_timeout(500)
    chk('也到自然人页', cur(pg) == 'sjfn_zrr', cur(pg))

    print('\n═══ 自然人 → 人口流动 → 切回 ═══')
    pg.click('#hot-sjfn_zrr-ld'); pg.wait_for_timeout(500)
    chk('到人口流动', cur(pg) == 'sjfn_zrr_ld', cur(pg))
    pg.screenshot(path=str(OUT / '5_人口流动.png'))
    pg.click('#hot-sjfn_zrr_ld-hj'); pg.wait_for_timeout(500)
    chk('切回自然人', cur(pg) == 'sjfn_zrr', cur(pg))

    print('\n═══ 首页 → 数据安全（宽图 2466×1280）═══')
    pg.evaluate("window.__daping.go('home')"); pg.wait_for_timeout(400)
    r_home = frame_ratio(pg)
    pg.click('#hot-home-n4'); pg.wait_for_timeout(600)
    chk('到数据安全', cur(pg) == 'sjaq', cur(pg))
    r_aq = frame_ratio(pg)
    chk('画幅随之变宽', abs(r_aq - 2466/1280) < 0.02, f'{r_aq}  首页={r_home}')
    pg.screenshot(path=str(OUT / '6_数据安全.png'))
    pg.click('#hot-t-sjaq'); pg.wait_for_timeout(500)
    chk('点标题回首页', cur(pg) == 'home', cur(pg))
    chk('画幅回到 16:9', abs(frame_ratio(pg) - 2276/1280) < 0.02, frame_ratio(pg))

    print('\n═══ 首页 → 数据治理 → × ═══')
    pg.click('#hot-home-n2'); pg.wait_for_timeout(500)
    chk('到数据治理', cur(pg) == 'sjzl', cur(pg))
    pg.screenshot(path=str(OUT / '7_数据治理.png'))
    pg.click('#hot-sjzl-close'); pg.wait_for_timeout(500)
    chk('× 回首页', cur(pg) == 'home', cur(pg))

    print('\n═══ 数据汇聚（待补）═══')
    pg.click('#hot-home-n1'); pg.wait_for_timeout(400)
    chk('可进', cur(pg) == 'sjhj')
    chk('有待补标记', pg.evaluate("!!document.querySelector('#scr-sjhj .ph-badge')"))
    pg.click('#hot-t-sjhj'); pg.wait_for_timeout(400)
    chk('回首页', cur(pg) == 'home')

    print('\n═══ 七张图逐张核对未被改动 ═══')
    for sid, (nm, nat, cnt) in IMGS.items():
        pg.evaluate(f"window.__daping.go('{sid}')"); pg.wait_for_timeout(350)
        r = pg.evaluate(f"""(()=>{{const i=document.querySelector('#scr-{sid} img.shot');
          if(!i)return null;const s=getComputedStyle(i);
          return {{nat:i.naturalWidth+'x'+i.naturalHeight,filter:s.filter,opacity:s.opacity,
                   fit:s.objectFit,act:document.querySelectorAll('.hot.act').length}}}})()""")
        ok = (r and r['nat'] == nat and r['filter'] == 'none'
              and r['opacity'] == '1' and r['act'] == cnt)
        chk(f'{nm} {nat} 无滤镜 热区{cnt}', ok, r)

    print('\n═══ 键盘与路由 ═══')
    pg.evaluate("window.__daping.go('sjfn_dfn')"); pg.wait_for_timeout(300)
    pg.keyboard.press('Escape'); pg.wait_for_timeout(300)
    chk('ESC 回首页', cur(pg) == 'home')
    pg.evaluate("location.hash='#sjfn_dfn'"); pg.wait_for_timeout(500)
    chk('hash 路由 #sjfn_dfn', cur(pg) == 'sjfn_dfn', cur(pg))

    print('\n═══ 汇总 ═══')
    print(f'  {"✅ 全部通过" if not fails else "❌ 失败 " + str(len(fails)) + " 项"}')
    for f in fails:
        print(f'     - {f}')
    print(f'  截图 {len(list(OUT.glob("[0-9]*.png")))} 张')
    b.close()

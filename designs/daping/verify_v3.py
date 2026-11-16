# -*- coding: utf-8 -*-
"""v3 真机验证：首页→数据赋能→自然人→人口流动 全链路"""
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
    print(f'  {"✅" if cond else "❌"} {name}{("  " + extra) if extra else ""}')
    if not cond:
        fails.append(name)

def cur(pg):
    return pg.evaluate("window.__daping.current()")

def act(pg):
    return pg.evaluate("[...document.querySelectorAll('.hot.act')].map(a=>a.id)")

with sync_playwright() as p:
    b = p.chromium.launch(executable_path=CH, args=['--no-sandbox', '--disable-gpu'])
    pg = b.new_page(viewport={'width': 1600, 'height': 900})
    errs = []
    pg.on('console', lambda m: errs.append(m.text) if m.type == 'error' else None)
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(HTML); pg.wait_for_timeout(900)

    print('═══ 初始化 ═══')
    chk('无 JS 报错', not errs, str(errs[:2]))
    chk('7 个屏 DOM 齐全', pg.evaluate("document.querySelectorAll('.screen').length") == 7,
        str(pg.evaluate("document.querySelectorAll('.screen').length")))
    chk('热区 14 个', pg.evaluate("window.__daping.hotspotCount") == 14,
        str(pg.evaluate("window.__daping.hotspotCount")))
    chk('初始在首页', cur(pg) == 'home')
    chk('首页生效热区=4个导航', len(act(pg)) == 4, str(act(pg)))
    pg.screenshot(path=str(OUT / '1_首页.png'))

    print('\n═══ 首页 → 数据赋能（法人页）═══')
    pg.click('#hot-home-n3'); pg.wait_for_timeout(450)
    chk('到数据赋能', cur(pg) == 'sjfn', cur(pg))
    chk('该屏热区=标题+自然人', len(act(pg)) == 2, str(act(pg)))
    pg.screenshot(path=str(OUT / '2_数据赋能_法人.png'))

    print('\n═══ 数据赋能：点导航「自然人」═══')
    pg.click('#hot-sjfn-n1'); pg.wait_for_timeout(450)
    chk('到自然人页（户籍人口分析）', cur(pg) == 'sjfn_zrr', cur(pg))
    chk('该屏热区=标题+人口流动分析', len(act(pg)) == 2, str(act(pg)))
    pg.screenshot(path=str(OUT / '3_自然人_户籍人口.png'))

    print('\n═══ 自然人：点右上「人口流动分析」═══')
    pg.click('#hot-sjfn_zrr-ld'); pg.wait_for_timeout(450)
    chk('到人口流动页', cur(pg) == 'sjfn_zrr_ld', cur(pg))
    chk('该屏热区=标题+户籍人口分析', len(act(pg)) == 2, str(act(pg)))
    pg.screenshot(path=str(OUT / '4_自然人_人口流动.png'))

    print('\n═══ 人口流动：点「户籍人口分析」切回 ═══')
    pg.click('#hot-sjfn_zrr_ld-hj'); pg.wait_for_timeout(450)
    chk('切回自然人页', cur(pg) == 'sjfn_zrr', cur(pg))

    print('\n═══ 每屏点标题回首页 ═══')
    for sid, nm in [('sjfn_zrr', '自然人页'), ('sjfn', '数据赋能页'), ('sjzl', '数据治理页')]:
        if cur(pg) != sid:
            pg.evaluate(f"window.__daping.go('{sid}')"); pg.wait_for_timeout(300)
        pg.click(f'#hot-t-{sid}'); pg.wait_for_timeout(400)
        chk(f'{nm} 点标题回首页', cur(pg) == 'home', cur(pg))

    print('\n═══ 数据治理页：× 关闭回首页 ═══')
    pg.click('#hot-home-n2'); pg.wait_for_timeout(400)
    chk('到数据治理', cur(pg) == 'sjzl', cur(pg))
    pg.click('#hot-sjzl-close'); pg.wait_for_timeout(400)
    chk('× 回首页', cur(pg) == 'home', cur(pg))

    print('\n═══ 待补页与键盘 ═══')
    pg.click('#hot-home-n1'); pg.wait_for_timeout(350)
    chk('数据汇聚（待补）可进', cur(pg) == 'sjhj')
    chk('显示待补标记', pg.evaluate("!!document.querySelector('#scr-sjhj .ph-badge')"))
    pg.click('#hot-t-sjhj'); pg.wait_for_timeout(300)
    chk('待补页点标题回首页', cur(pg) == 'home')
    pg.keyboard.press('Escape'); pg.wait_for_timeout(250)
    chk('ESC 回首页', cur(pg) == 'home')

    print('\n═══ 五张图未被改动 ═══')
    for sid, nm in [('home', '首页'), ('sjfn', '数据赋能'), ('sjzl', '数据治理'),
                    ('sjfn_zrr', '自然人'), ('sjfn_zrr_ld', '人口流动')]:
        r = pg.evaluate(f"""(()=>{{const i=document.querySelector('#scr-{sid} img.shot');
          if(!i)return null;const s=getComputedStyle(i);
          return {{nat:i.naturalWidth+'x'+i.naturalHeight,filter:s.filter,opacity:s.opacity}}}})()""")
        ok = r and r['filter'] == 'none' and r['opacity'] == '1' and r['nat'] == '2276x1280'
        chk(f'{nm} 原生2276x1280 无滤镜', ok, str(r))

    print('\n═══ 汇总 ═══')
    print(f'  {"✅ 全部通过" if not fails else "❌ 失败 " + str(len(fails)) + " 项: " + str(fails)}')
    print(f'  截图 {len(list(OUT.glob("[0-9]*.png")))} 张')
    b.close()

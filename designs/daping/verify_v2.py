# -*- coding: utf-8 -*-
"""v2 真机验证：三图导航链 + 屏级热区隔离 + 图片未被改动"""
import pathlib
from playwright.sync_api import sync_playwright

CH = '/opt/data/chrome/shell/chrome-headless-shell-linux64/chrome-headless-shell'
HTML = 'file:///opt/data/designs/daping/四川省一体化数据平台_大屏交互.html'
OUT = pathlib.Path('/opt/data/designs/daping/_shots')
OUT.mkdir(parents=True, exist_ok=True)
for f in OUT.glob('*.png'):
    if not f.name.startswith('_'):
        f.unlink()

fails = []
def chk(name, cond, extra=''):
    print(f'  {"✅" if cond else "❌"} {name}{("  " + extra) if extra else ""}')
    if not cond:
        fails.append(name)

with sync_playwright() as p:
    b = p.chromium.launch(executable_path=CH, args=['--no-sandbox', '--disable-gpu'])
    pg = b.new_page(viewport={'width': 1600, 'height': 900})
    errs = []
    pg.on('console', lambda m: errs.append(m.text) if m.type == 'error' else None)
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(HTML); pg.wait_for_timeout(800)

    print('═══ 初始化 ═══')
    chk('无 JS 报错', not errs, str(errs[:2]))
    chk('热区总数 = 9', pg.evaluate("window.__daping.hotspotCount") == 9,
        str(pg.evaluate("window.__daping.hotspotCount")))
    chk('初始在首页', pg.evaluate("window.__daping.current()") == 'home')
    pg.screenshot(path=str(OUT / '1_首页.png'))

    print('\n═══ 屏级热区隔离 ═══')
    act = pg.evaluate("[...document.querySelectorAll('.hot.act')].map(a=>a.id)")
    chk('首页只有 4 个导航热区生效（无标题热区）', len(act) == 4, str(act))
    chk('首页热区都是导航', all('-n' in x for x in act), str(act))

    print('\n═══ 首页 → 数据治理（图3 标准层弹窗）═══')
    pg.click('#hot-home-n2'); pg.wait_for_timeout(400)
    chk('跳到数据治理', pg.evaluate("window.__daping.current()") == 'sjzl')
    act = pg.evaluate("[...document.querySelectorAll('.hot.act')].map(a=>a.id)")
    chk('该屏只有标题+关闭 2 个热区', len(act) == 2, str(act))
    chk('导航热区已失效（不可见）',
        pg.evaluate("(()=>{const a=document.getElementById('hot-home-n1');"
                    "return getComputedStyle(a).pointerEvents==='none'})()"))
    pg.screenshot(path=str(OUT / '2_数据治理_标准层.png'))

    print('\n═══ 数据治理：点标题回首页 ═══')
    pg.click('#hot-t-sjzl'); pg.wait_for_timeout(400)
    chk('点标题回到首页', pg.evaluate("window.__daping.current()") == 'home')

    print('\n═══ 首页 → 数据赋能（图2 法人综合分析）═══')
    pg.click('#hot-home-n3'); pg.wait_for_timeout(400)
    chk('跳到数据赋能', pg.evaluate("window.__daping.current()") == 'sjfn')
    pg.screenshot(path=str(OUT / '3_数据赋能_法人.png'))

    print('\n═══ 数据赋能：点标题回首页 ═══')
    pg.click('#hot-t-sjfn'); pg.wait_for_timeout(400)
    chk('点标题回到首页', pg.evaluate("window.__daping.current()") == 'home')

    print('\n═══ 首页 → 数据汇聚 / 数据安全（待补占位）═══')
    pg.click('#hot-home-n1'); pg.wait_for_timeout(350)
    chk('跳到数据汇聚', pg.evaluate("window.__daping.current()") == 'sjhj')
    chk('显示待补标记', pg.evaluate("!!document.querySelector('#scr-sjhj .ph-badge')"))
    pg.screenshot(path=str(OUT / '4_数据汇聚_待补.png'))
    pg.click('#hot-t-sjhj'); pg.wait_for_timeout(300)
    chk('待补页点标题也能回首页', pg.evaluate("window.__daping.current()") == 'home')

    pg.click('#hot-home-n4'); pg.wait_for_timeout(350)
    chk('跳到数据安全', pg.evaluate("window.__daping.current()") == 'sjaq')

    print('\n═══ 键盘与路由 ═══')
    pg.keyboard.press('Escape'); pg.wait_for_timeout(300)
    chk('ESC 回首页', pg.evaluate("window.__daping.current()") == 'home')
    pg.keyboard.press('ArrowRight'); pg.wait_for_timeout(300)
    chk('→ 翻页到数据汇聚', pg.evaluate("window.__daping.current()") == 'sjhj')
    before = pg.evaluate("document.body.classList.contains('hide-tips')")
    pg.keyboard.press('h'); pg.wait_for_timeout(200)
    chk('H 切换提示显隐',
        before != pg.evaluate("document.body.classList.contains('hide-tips')"))
    pg.keyboard.press('h')
    pg.goto(HTML + '#sjfn'); pg.wait_for_timeout(700)
    chk('地址栏 #sjfn 直达', pg.evaluate("window.__daping.current()") == 'sjfn')

    print('\n═══ 图片未被改动（三张逐屏核对）═══')
    for sid, nm in [('home', '图1'), ('sjfn', '图2'), ('sjzl', '图3')]:
        r = pg.evaluate(f"""(()=>{{
          const i=document.querySelector('#scr-{sid} img.shot');
          if(!i) return null;
          const s=getComputedStyle(i);
          return {{nat:i.naturalWidth+'x'+i.naturalHeight,
                   filter:s.filter, opacity:s.opacity, transform:s.transform}};
        }})()""")
        ok = r and r['filter'] == 'none' and r['opacity'] == '1' and r['nat'] == '2276x1280'
        chk(f'{nm} 原生 2276x1280 且无滤镜/无缩放', ok, str(r))

    print('\n═══ 等比不拉伸 ═══')
    geo = pg.evaluate("(()=>{const f=document.getElementById('frame').getBoundingClientRect();"
                      "return +(f.width/f.height).toFixed(4)})()")
    chk('画幅 16:9', abs(geo - 1.7778) < 0.01, str(geo))

    print('\n═══ 汇总 ═══')
    print(f'  {"✅ 全部通过" if not fails else "❌ 失败 " + str(len(fails)) + " 项: " + str(fails)}')
    print(f'  截图 {len([f for f in OUT.glob("*.png") if not f.name.startswith("_")])} 张')
    b.close()

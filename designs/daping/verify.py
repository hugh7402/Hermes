# -*- coding: utf-8 -*-
"""真 Chrome 验证：逐屏截图 + 真实点击跳转断言"""
import pathlib
from playwright.sync_api import sync_playwright

CH = '/opt/data/chrome/shell/chrome-headless-shell-linux64/chrome-headless-shell'
HTML = 'file:///opt/data/designs/daping/四川省一体化数据平台_大屏交互.html'
OUT = pathlib.Path('/opt/data/designs/daping/_shots')
OUT.mkdir(parents=True, exist_ok=True)

fails = []
def chk(name, cond, extra=''):
    print(f'  {"✅" if cond else "❌"} {name}{("  " + extra) if extra else ""}')
    if not cond:
        fails.append(name)

with sync_playwright() as p:
    b = p.chromium.launch(executable_path=CH, args=['--no-sandbox', '--disable-gpu'])
    pg = b.new_page(viewport={'width': 1600, 'height': 900}, device_scale_factor=1)
    errs = []
    pg.on('console', lambda m: errs.append(m.text) if m.type == 'error' else None)
    pg.on('pageerror', lambda e: errs.append(str(e)))

    pg.goto(HTML)
    pg.wait_for_timeout(700)

    print('\n═══ 初始化 ═══')
    chk('无 JS 报错', not errs, str(errs[:2]))
    chk('热区数量 = 5', pg.evaluate("window.__daping.hotspotCount") == 5,
        str(pg.evaluate("window.__daping.hotspotCount")))
    chk('初始在首页', pg.evaluate("window.__daping.current()") == 'home',
        str(pg.evaluate("window.__daping.current()")))
    chk('5 个屏 DOM 齐全', pg.evaluate("document.querySelectorAll('.screen').length") == 5)

    # 几何：frame 等比不拉伸
    geo = pg.evaluate("(()=>{const f=document.getElementById('frame').getBoundingClientRect();"
                      "return {w:f.width,h:f.height,r:+(f.width/f.height).toFixed(4)}})()")
    chk('画幅比例 = 16:9 (1.7778)', abs(geo['r'] - 1.7778) < 0.01, str(geo))

    print('\n═══ 真实点击：首页 → 数据汇聚 ═══')
    pg.click('#hot-nav-1')
    pg.wait_for_timeout(400)
    chk('跳转到数据汇聚', pg.evaluate("window.__daping.current()") == 'sjhj',
        str(pg.evaluate("window.__daping.current()")))
    chk('数据汇聚屏可见',
        pg.evaluate("document.getElementById('scr-sjhj').classList.contains('on')"))
    chk('URL hash = #sjhj', pg.evaluate("location.hash") == '#sjhj',
        pg.evaluate("location.hash"))
    chk('该屏是真图（含 img.shot）',
        pg.evaluate("!!document.querySelector('#scr-sjhj img.shot')"))
    pg.screenshot(path=str(OUT / '02_数据汇聚.png'))

    print('\n═══ 真实点击：数据汇聚 → 数据治理 ═══')
    pg.click('#hot-nav-2')
    pg.wait_for_timeout(400)
    chk('跳转到数据治理', pg.evaluate("window.__daping.current()") == 'sjzl',
        str(pg.evaluate("window.__daping.current()")))
    chk('显示待补提示',
        pg.evaluate("!!document.querySelector('#scr-sjzl .ph-badge')"))
    pg.screenshot(path=str(OUT / '03_数据治理_待补.png'))

    print('\n═══ 真实点击：数据治理 → 数据赋能 → 数据安全 ═══')
    pg.click('#hot-nav-3'); pg.wait_for_timeout(300)
    chk('跳转到数据赋能', pg.evaluate("window.__daping.current()") == 'sjfn',
        str(pg.evaluate("window.__daping.current()")))
    pg.click('#hot-nav-4'); pg.wait_for_timeout(300)
    chk('跳转到数据安全', pg.evaluate("window.__daping.current()") == 'sjaq',
        str(pg.evaluate("window.__daping.current()")))
    pg.screenshot(path=str(OUT / '05_数据安全_待补.png'))

    print('\n═══ 真实点击：标题 → 返回首页 ═══')
    pg.click('#hot-title')
    pg.wait_for_timeout(400)
    chk('点标题回到首页', pg.evaluate("window.__daping.current()") == 'home',
        str(pg.evaluate("window.__daping.current()")))
    pg.screenshot(path=str(OUT / '01_首页_待补.png'))

    print('\n═══ 键盘：ESC / 方向键 / H / 路由直达 ═══')
    pg.click('#hot-nav-2'); pg.wait_for_timeout(250)
    pg.keyboard.press('Escape'); pg.wait_for_timeout(300)
    chk('ESC 从二级页回首页', pg.evaluate("window.__daping.current()") == 'home')

    pg.keyboard.press('ArrowRight'); pg.wait_for_timeout(300)
    chk('→ 翻到下一页（数据汇聚）', pg.evaluate("window.__daping.current()") == 'sjhj')
    pg.keyboard.press('ArrowRight'); pg.wait_for_timeout(300)
    chk('→ 再翻（数据治理）', pg.evaluate("window.__daping.current()") == 'sjzl')

    before = pg.evaluate("document.body.classList.contains('hide-tips')")
    pg.keyboard.press('h'); pg.wait_for_timeout(200)
    after = pg.evaluate("document.body.classList.contains('hide-tips')")
    chk('H 切换提示显隐', before != after, f'{before} → {after}')
    pg.keyboard.press('h'); pg.wait_for_timeout(150)

    pg.goto(HTML + '#sjfn'); pg.wait_for_timeout(600)
    chk('地址栏 #sjfn 直达数据赋能',
        pg.evaluate("window.__daping.current()") == 'sjfn',
        str(pg.evaluate("window.__daping.current()")))

    print('\n═══ 热区几何与图片是否被改动 ═══')
    hs = pg.evaluate("""(()=>{
      const f=document.getElementById('frame').getBoundingClientRect();
      return [...document.querySelectorAll('.hot')].map(a=>{
        const r=a.getBoundingClientRect();
        return {id:a.id, l:+(((r.left-f.left)/f.width)*100).toFixed(2),
                t:+(((r.top-f.top)/f.height)*100).toFixed(2),
                w:+((r.width/f.width)*100).toFixed(2),
                h:+((r.height/f.height)*100).toFixed(2)};
      });
    })()""")
    for h in hs:
        print(f'    {h["id"]:<12} left {h["l"]:>6}%  top {h["t"]:>5}%  w {h["w"]:>5}%  h {h["h"]:>5}%')
    chk('图片未被 CSS 滤镜改动',
        pg.evaluate("(()=>{const i=document.querySelector('#scr-sjhj img.shot');"
                    "const s=getComputedStyle(i);return s.filter==='none'&&s.opacity==='1'})()"))

    print('\n═══ 汇总 ═══')
    print(f'  {"✅ 全部通过" if not fails else "❌ 失败 " + str(len(fails)) + " 项: " + str(fails)}')
    print(f'  截图 {len(list(OUT.glob("*.png")))} 张 → {OUT}')
    b.close()

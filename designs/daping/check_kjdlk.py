# -*- coding: utf-8 -*-
import pathlib
from playwright.sync_api import sync_playwright

CH = '/opt/data/chrome/shell/chrome-headless-shell-linux64/chrome-headless-shell'
HTML = 'file:///opt/data/designs/daping/四川省一体化数据平台_大屏交互.html'
OUT = pathlib.Path('/opt/data/designs/daping/_shots')

with sync_playwright() as p:
    b = p.chromium.launch(executable_path=CH, args=['--no-sandbox', '--disable-gpu'])
    pg = b.new_page(viewport={'width': 1600, 'height': 900})
    errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(HTML); pg.wait_for_timeout(1500)

    print('  屏数', pg.evaluate("document.querySelectorAll('.screen').length"))
    print('  热区', pg.evaluate("window.__daping.hotspotCount"))
    print('  JS错误', errs)

    def ratio():
        return pg.evaluate(
            "(()=>{const r=document.querySelector('#frame').getBoundingClientRect();"
            "return Math.round(r.width/r.height*1000)/1000})()")

    def act():
        return pg.evaluate("[...document.querySelectorAll('.hot.act')].map(a=>a.id)")

    pg.evaluate("window.__daping.go('home')"); pg.wait_for_timeout(400)
    print('  首页画幅', ratio())
    pg.screenshot(path=str(OUT / '20_首页.png'))

    pg.evaluate("window.__daping.go('sjfn_kjdlk')"); pg.wait_for_timeout(500)
    print('  空间地理库画幅', ratio(), '热区', act())
    pg.screenshot(path=str(OUT / '21_空间地理库.png'))

    pg.evaluate("""(()=>{document.querySelectorAll('.hot.act').forEach(h=>{
        h.style.border='3px solid #ff0055'; h.style.background='rgba(255,0,85,.25)';
        h.style.opacity='1'; h.style.pointerEvents='auto';})})()""")
    pg.wait_for_timeout(250)
    box = pg.evaluate("(()=>{const f=document.querySelector('#frame').getBoundingClientRect();"
                      "return{x:f.x,y:f.y,w:f.width,h:f.height}})()")
    pg.screenshot(path=str(OUT / 'navhot_kjdlk.png'),
                  clip={'x': box['x'] + box['w'] * 0.28, 'y': box['y'],
                        'width': box['w'] * 0.46, 'height': box['h'] * 0.22})
    print('  截图完成')
    b.close()

# -*- coding: utf-8 -*-
import pathlib
from playwright.sync_api import sync_playwright

CH = '/opt/data/chrome/shell/chrome-headless-shell-linux64/chrome-headless-shell'
HTML = 'file:///opt/data/designs/daping/四川省一体化数据平台_大屏交互.html'
OUT = pathlib.Path('/opt/data/designs/daping/_shots')

with sync_playwright() as p:
    b = p.chromium.launch(executable_path=CH, args=['--no-sandbox', '--disable-gpu'])
    pg = b.new_page(viewport={'width': 1600, 'height': 900})
    pg.goto(HTML); pg.wait_for_timeout(1800)
    for sid, tag in [('sjfn_kjdlk', '30_空间地理库_入口'), ('sjfn_kjdlk_p3', '31_GIS3')]:
        pg.evaluate(f"window.__daping.go('{sid}')"); pg.wait_for_timeout(500)
        pg.screenshot(path=str(OUT / f'{tag}.png'))
    # 箭头特写
    box = pg.evaluate("(()=>{const f=document.querySelector('#frame').getBoundingClientRect();"
                      "return{x:f.x,y:f.y,w:f.width,h:f.height}})()")
    pg.screenshot(path=str(OUT / 'arw_zoom.png'),
                  clip={'x': box['x'] + box['w'] * 0.88, 'y': box['y'] + box['h'] * 0.55,
                        'width': box['w'] * 0.12, 'height': box['h'] * 0.40})
    print('截图完成')
    b.close()

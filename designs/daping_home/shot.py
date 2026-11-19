#!/usr/bin/env python3
"""总屏截图 + 基础断言（真 Chrome headless shell）"""
import asyncio, pathlib, json
from playwright.async_api import async_playwright

CH = '/opt/data/chrome/shell/chrome-headless-shell-linux64/chrome-headless-shell'
OUT = pathlib.Path('/opt/data/designs/daping_home/_shots')
OUT.mkdir(exist_ok=True)
HTML = pathlib.Path('/opt/data/designs/daping_home/总屏_首页.html').resolve()


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path=CH,
                                    args=['--no-sandbox', '--disable-gpu'])
        pg = await b.new_page(viewport={'width': 2276, 'height': 1280},
                              device_scale_factor=1)
        errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.on('console', lambda m: errs.append('console:' + m.text) if m.type == 'error' else None)
        await pg.goto(HTML.as_uri())
        await pg.wait_for_timeout(900)

        png = OUT / '总屏_2276x1280.png'
        await pg.screenshot(path=str(png))

        # 断言
        a = {}
        a['title'] = await pg.text_content('h1')
        a['nav_count'] = await pg.eval_on_selector_all('.nav-item', 'els=>els.length')
        a['strip_count'] = await pg.eval_on_selector_all('.strip', 'els=>els.length')
        a['node_count'] = await pg.eval_on_selector_all('.node', 'els=>els.length')
        a['nav_items'] = await pg.eval_on_selector_all('.nav-item', 'els=>els.map(e=>e.textContent.trim())')
        a['node_names'] = await pg.eval_on_selector_all('.node-name', 'els=>els.map(e=>e.textContent.trim())')
        # 溢出检查
        a['overflow'] = await pg.evaluate("""() => {
            var bad=[]; var st=document.getElementById('stage');
            st.querySelectorAll('*').forEach(function(el){
                var r=el.getBoundingClientRect();
                if(r.width>0 && (r.right>innerWidth+1 || r.bottom>innerHeight+1 || r.left<-1 || r.top<-1))
                    bad.push(el.className||el.tagName);
            });
            return bad.slice(0,8);
        }""")
        # 中文字体是否生效
        a['font'] = await pg.evaluate("()=>getComputedStyle(document.querySelector('h1')).fontFamily")
        a['bodyTextLen'] = await pg.evaluate("()=>document.body.innerText.replace(/\\s/g,'').length")

        # 点击测试
        await pg.click('.node[data-go="govern"]')
        await pg.wait_for_timeout(320)
        a['toast_after_click'] = await pg.text_content('#toast')
        a['toast_visible'] = await pg.evaluate("()=>document.getElementById('toast').classList.contains('show')")
        await pg.screenshot(path=str(OUT / '总屏_点击治理toast.png'))

        # nav 点击
        await pg.click('.nav-item[data-go="institution"]')
        await pg.wait_for_timeout(320)
        a['toast_after_nav'] = await pg.text_content('#toast')

        a['page_errors'] = errs
        print(json.dumps(a, ensure_ascii=False, indent=2))
        await b.close()


asyncio.run(main())

#!/usr/bin/env python3
"""总屏 v2 验证：截图 + 几何量化 + 点击链路"""
import asyncio, pathlib, json
from playwright.async_api import async_playwright

CH = '/opt/data/chrome/shell/chrome-headless-shell-linux64/chrome-headless-shell'
OUT = pathlib.Path('/opt/data/designs/daping_home/_shots'); OUT.mkdir(exist_ok=True)
HTML = pathlib.Path('/opt/data/designs/daping_home/总屏_首页.html').resolve()


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path=CH, args=['--no-sandbox', '--disable-gpu'])
        pg = await b.new_page(viewport={'width': 2276, 'height': 1280})
        errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.on('console', lambda m: errs.append('console:' + m.text) if m.type == 'error' else None)
        await pg.goto(HTML.as_uri()); await pg.wait_for_timeout(800)
        await pg.screenshot(path=str(OUT / '总屏v2_2276x1280.png'))

        r = await pg.evaluate("""() => {
          const box = el => { const r = el.getBoundingClientRect();
            return {x:Math.round(r.x), y:Math.round(r.y), w:Math.round(r.width), h:Math.round(r.height)}; };
          const nodes = [...document.querySelectorAll('.node')].map(box);
          const strips = [...document.querySelectorAll('#stage > .wrap > main > .strip')].map(box);
          const guards = [...document.querySelectorAll('.guards .strip')].map(box);
          const nav = [...document.querySelectorAll('.nav-item')].map(box);
          const main = box(document.querySelector('main'));
          const hdr = box(document.querySelector('header'));
          // 垂直空白：header 底部到 main 顶部，main 底部到 stage 底部
          const stageBox = box(document.getElementById('stage'));
          const lastEl = document.querySelector('.guards .strip:last-child');
          const lastBottom = lastEl.getBoundingClientRect().bottom;
          return {
            nodes, strips, guards, nav, main, hdr,
            gap_header_to_main: Math.round(main.y - (hdr.y + hdr.h)),
            gap_content_to_bottom: Math.round(stageBox.y + stageBox.h - lastBottom),
            node_widths_equal: new Set(nodes.map(n=>n.w)).size === 1,
            node_same_y: new Set(nodes.map(n=>n.y)).size === 1,
            guard_widths_equal: new Set(guards.map(n=>n.w)).size === 1,
            bodyLen: document.body.innerText.replace(/\\s/g,'').length,
            overflow: (()=>{ const bad=[]; document.getElementById('stage').querySelectorAll('*').forEach(el=>{
                const r=el.getBoundingClientRect();
                if(r.width>0 && (r.right>innerWidth+1||r.bottom>innerHeight+1||r.left<-1||r.top<-1))
                  bad.push(el.className||el.tagName); }); return bad.slice(0,8); })(),
            idxOrder: [...document.querySelectorAll('.idx,.node-idx')].map(e=>e.textContent.trim())
          };
        }""")
        print(json.dumps(r, ensure_ascii=False, indent=2))

        # 点击链路：6 个入口全覆盖
        clicks = {}
        for sel, name in [('.node[data-go="gather"]', '汇聚'), ('.node[data-go="govern"]', '治理'),
                          ('.node[data-go="empower"]', '赋能'),
                          ('#stage > .wrap > main > .strip[data-go="overview"]', '总览'),
                          ('.guards .strip[data-go="security"]', '安全'),
                          ('.guards .strip[data-go="institution"]', '制度'),
                          ('.nav-item[data-go="govern"]', '导航-治理')]:
            await pg.click(sel); await pg.wait_for_timeout(260)
            clicks[name] = await pg.text_content('#toast')
        print(json.dumps({'clicks': clicks, 'page_errors': errs}, ensure_ascii=False, indent=2))
        await pg.screenshot(path=str(OUT / '总屏v2_点击态.png'))
        await b.close()


asyncio.run(main())

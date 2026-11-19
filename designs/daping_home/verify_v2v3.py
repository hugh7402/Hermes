#!/usr/bin/env python3
"""V2 / V3 双版验证：截图 + 几何 + 点击链路"""
import asyncio, pathlib, json
from playwright.async_api import async_playwright

CH = '/opt/data/chrome/shell/chrome-headless-shell-linux64/chrome-headless-shell'
ROOT = pathlib.Path('/opt/data/designs/daping_home')
OUT = ROOT / '_shots'; OUT.mkdir(exist_ok=True)
PAGES = [('V2', ROOT / '总屏_V2_三栏驾驶舱.html'), ('V3', ROOT / '总屏_V3_中心辐射.html')]


async def check(pg, name):
    r = await pg.evaluate("""() => {
      const st = document.getElementById('stage');
      const bad=[];
      st.querySelectorAll('*').forEach(el=>{ const r=el.getBoundingClientRect();
        if(r.width>0 && (r.right>innerWidth+1||r.bottom>innerHeight+1||r.left<-1||r.top<-1)) bad.push(el.className||el.tagName); });
      // 元素间重叠检测（同级块）
      const blocks=[...document.querySelectorAll('[data-go]')].map(el=>({c:el.className,r:el.getBoundingClientRect()}));
      const ov=[];
      for(let i=0;i<blocks.length;i++) for(let j=i+1;j<blocks.length;j++){
        const a=blocks[i].r,b=blocks[j].r;
        const w=Math.min(a.right,b.right)-Math.max(a.left,b.left);
        const h=Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top);
        if(w>6&&h>6) ov.push(blocks[i].c+' × '+blocks[j].c);
      }
      return {title:document.querySelector('h1').textContent.trim(),
              entries:document.querySelectorAll('[data-go]').length,
              idx:[...document.querySelectorAll('.ix,.n-idx')].map(e=>e.textContent.trim()),
              overflow:bad.slice(0,8), overlaps:ov.slice(0,8),
              bodyLen:document.body.innerText.replace(/\\s/g,'').length,
              scrollH:document.documentElement.scrollHeight};
    }""")
    r['name'] = name
    return r


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path=CH, args=['--no-sandbox', '--disable-gpu'])
        for name, f in PAGES:
            pg = await b.new_page(viewport={'width': 2276, 'height': 1280})
            errs = []
            pg.on('pageerror', lambda e: errs.append(str(e)))
            pg.on('console', lambda m: errs.append('console:' + m.text) if m.type == 'error' else None)
            await pg.goto(f.as_uri()); await pg.wait_for_timeout(850)
            await pg.screenshot(path=str(OUT / f'总屏{name}.png'))
            r = await check(pg, name)
            # 点击覆盖
            clicks = {}
            for sel in ['[data-go="overview"]', '[data-go="gather"]', '[data-go="govern"]',
                        '[data-go="empower"]', '[data-go="security"]', '[data-go="institution"]']:
                await pg.click(sel); await pg.wait_for_timeout(200)
                clicks[sel.split('"')[1]] = await pg.text_content('#toast')
            r['clicks'] = clicks
            r['page_errors'] = errs
            print(json.dumps(r, ensure_ascii=False, indent=2))
            await pg.close()
        await b.close()


asyncio.run(main())

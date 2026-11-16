# -*- coding: utf-8 -*-
"""v7 真机验证：21 屏 / 空间地理库 7 页翻页链 / × 返回 / 全链路"""
import pathlib
from playwright.sync_api import sync_playwright

CH = '/opt/data/chrome/shell/chrome-headless-shell-linux64/chrome-headless-shell'
HTML = 'file:///opt/data/designs/daping/四川省一体化数据平台_大屏交互.html'

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
    return pg.evaluate("(()=>{const r=document.querySelector('#frame').getBoundingClientRect();"
                       "return Math.round(r.width/r.height*1000)/1000})()")
def go(pg, sid):
    pg.evaluate(f"window.__daping.go('{sid}')"); pg.wait_for_timeout(300)
def arrows(pg, sid):
    go(pg, sid)
    return pg.evaluate(f"""[...document.querySelectorAll('#scr-{sid} .arw')].map(b=>(
        b.classList.contains('dn')?'dn':'up')+':'+b.getAttribute('data-go'))""")

SCREENS = {
    'home': ('首页','2276x1280',4), 'sjhj': ('数据汇聚','2048x1280',5),
    'sjhj_bm': ('数据编目','2276x1280',3), 'sjhj_hj': ('汇聚更新','2048x1280',3),
    'sjhj_zrrku': ('自然人库汇聚','2048x1280',3), 'sjhj_frku': ('法人库汇聚','2048x1280',3),
    'sjzl': ('数据治理','2276x1280',4), 'sjfn': ('数据赋能(法人)','2276x1280',4),
    'sjfn_dfn': ('数据赋能-数据赋能','2276x1280',5), 'sjfn_yjs': ('支撑高效办成一件事','2276x1280',5),
    'sjfn_kjdlk': ('空间地理库','1920x887',3),
    'sjfn_kjdlk_p1': ('GIS-1','1920x883',1), 'sjfn_kjdlk_p2': ('GIS-2','1920x880',1),
    'sjfn_kjdlk_p3': ('GIS-3','1920x882',1), 'sjfn_kjdlk_p4': ('GIS-4','1920x885',1),
    'sjfn_kjdlk_p5': ('GIS-5','1920x882',1), 'sjfn_kjdlk_p6': ('GIS-6','1920x884',1),
    'sjfn_kjdlk_p7': ('GIS-7','1920x889',1),
    'sjfn_zrr': ('自然人','2276x1280',2), 'sjfn_zrr_ld': ('人口流动','2276x1280',2),
    'sjaq': ('数据安全','2466x1280',1),
}

with sync_playwright() as p:
    b = p.chromium.launch(executable_path=CH, args=['--no-sandbox', '--disable-gpu'])
    pg = b.new_page(viewport={'width': 1600, 'height': 900})
    errs = []
    pg.on('console', lambda m: errs.append(m.text) if m.type == 'error' else None)
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(HTML); pg.wait_for_timeout(2000)

    print('═══ 基础 ═══')
    chk('无 JS 报错', not errs, errs[:2])
    chk('21 屏 DOM', pg.evaluate("document.querySelectorAll('.screen').length") == 21,
        pg.evaluate("document.querySelectorAll('.screen').length"))
    chk('热区 54 个', pg.evaluate("window.__daping.hotspotCount") == 54,
        pg.evaluate("window.__daping.hotspotCount"))
    chk('初始首页', cur(pg) == 'home')

    print('\n═══ 空间地理库翻页链：向下 7 次 ═══')
    go(pg, 'sjfn')
    pg.click('#hot-sjfn-n3'); pg.wait_for_timeout(450)
    chk('数据赋能页 →「空间地理库」', cur(pg) == 'sjfn_kjdlk', cur(pg))
    chk('入口页没有 ▲ 返回箭头（它在链首）',
        arrows(pg, 'sjfn_kjdlk') == ['dn:sjfn_kjdlk_p1'], arrows(pg, 'sjfn_kjdlk'))
    seq = []
    for i in range(1, 8):
        pg.click('#scr-' + (cur(pg)) + ' .arw.dn'); pg.wait_for_timeout(420)
        seq.append(cur(pg))
    want = [f'sjfn_kjdlk_p{i}' for i in range(1, 8)]
    chk('一路 ▼ 翻到第 7 张', seq == want, seq)
    chk('最后一页没有 ▼', arrows(pg, 'sjfn_kjdlk_p7') == ['up:sjfn_kjdlk_p6'],
        arrows(pg, 'sjfn_kjdlk_p7'))

    print('\n═══ 空间地理库翻页链：▲ 一路返回 ═══')
    back = []
    for i in range(7):
        pg.click('#scr-' + cur(pg) + ' .arw.up'); pg.wait_for_timeout(420)
        back.append(cur(pg))
    chk('▲ 逐级返回到入口页', back[-1] == 'sjfn_kjdlk', back)
    chk('▲ 路径为 p6→p5→…→p1→入口', back == [f'sjfn_kjdlk_p{i}' for i in range(6, 0, -1)] + ['sjfn_kjdlk'], back)

    print('\n═══ 空间地理库页的标签 ═══')
    go(pg, 'sjfn_kjdlk')
    pg.click('#hot-sjfn_kjdlk-n1'); pg.wait_for_timeout(450)
    chk('空间地理库→自然人', cur(pg) == 'sjfn_zrr', cur(pg))
    go(pg, 'sjfn_kjdlk')
    pg.click('#hot-sjfn_kjdlk-n2'); pg.wait_for_timeout(450)
    chk('空间地理库→法人', cur(pg) == 'sjfn', cur(pg))
    go(pg, 'sjfn_kjdlk')
    pg.click('#hot-t-sjfn_kjdlk'); pg.wait_for_timeout(450)
    chk('空间地理库点标题→首页', cur(pg) == 'home', cur(pg))

    print('\n═══ × 返回 ═══')
    for start, click, mid, exp, label in [
        ('sjhj', '#hot-sjhj-n3', 'sjhj_zrrku', 'sjhj', '自然人库汇聚'),
        ('sjhj', '#hot-sjhj-n4', 'sjhj_frku', 'sjhj', '法人库汇聚'),
        ('sjhj', '#hot-sjhj-n1', 'sjhj_bm', 'sjhj', '数据编目'),
        ('sjhj_bm', '#hot-sjhj_bm-n1', 'sjhj_hj', 'sjhj_bm', '编目→汇聚更新'),
    ]:
        go(pg, start)
        pg.click(click); pg.wait_for_timeout(400)
        ok1 = cur(pg) == mid
        pg.click(f'#hot-{mid}-close'); pg.wait_for_timeout(400)
        chk(f'{label} × 返回 {exp}', ok1 and cur(pg) == exp, cur(pg))

    print('\n═══ 一级导航全链路 ═══')
    go(pg, 'home')
    for hid, exp, lbl in [('#hot-home-n1','sjhj','数据汇聚'), ('#hot-home-n2','sjzl','数据治理'),
                          ('#hot-home-n3','sjfn','数据赋能'), ('#hot-home-n4','sjaq','数据安全')]:
        go(pg, 'home'); pg.click(hid); pg.wait_for_timeout(400)
        chk(f'首页→{lbl}', cur(pg) == exp, cur(pg))
    go(pg, 'sjzl')
    for hid, exp, lbl in [('#hot-sjzl-n1','sjhj','数据汇聚'), ('#hot-sjzl-n2','sjfn','数据赋能'),
                          ('#hot-sjzl-n3','sjaq','数据安全')]:
        go(pg, 'sjzl'); pg.click(hid); pg.wait_for_timeout(400)
        chk(f'数据治理→{lbl}', cur(pg) == exp, cur(pg))
    go(pg, 'sjfn'); pg.click('#hot-sjfn-n1'); pg.wait_for_timeout(400)
    chk('法人页→数据赋能页', cur(pg) == 'sjfn_dfn', cur(pg))
    pg.click('#hot-sjfn_dfn-n4'); pg.wait_for_timeout(400)
    chk('数据赋能页→支撑高效办成一件事', cur(pg) == 'sjfn_yjs', cur(pg))
    pg.click('#hot-sjfn_yjs-n4'); pg.wait_for_timeout(400)
    chk('→切回支撑部门场景应用', cur(pg) == 'sjfn_dfn', cur(pg))
    pg.click('#hot-sjfn_dfn-n1'); pg.wait_for_timeout(400)
    chk('→自然人', cur(pg) == 'sjfn_zrr', cur(pg))
    pg.click('#hot-sjfn_zrr-ld'); pg.wait_for_timeout(400)
    chk('→人口流动', cur(pg) == 'sjfn_zrr_ld', cur(pg))
    pg.click('#hot-sjfn_zrr_ld-hj'); pg.wait_for_timeout(400)
    chk('→切回自然人', cur(pg) == 'sjfn_zrr', cur(pg))
    go(pg, 'sjfn'); pg.click('#hot-sjfn-n2'); pg.wait_for_timeout(400)
    chk('法人页→自然人', cur(pg) == 'sjfn_zrr', cur(pg))

    print('\n═══ 21 屏逐屏核对：尺寸 / 无滤镜 / 热区数 ═══')
    bad = []
    for sid, (nm, nat, cnt) in SCREENS.items():
        go(pg, sid)
        r = pg.evaluate(f"""(()=>{{const i=document.querySelector('#scr-{sid} img.shot');
          if(!i)return null;const s=getComputedStyle(i);
          return {{nat:i.naturalWidth+'x'+i.naturalHeight,filter:s.filter,opacity:s.opacity,
                   act:document.querySelectorAll('.hot.act').length}}}})()""")
        if not (r and r['nat'] == nat and r['filter'] == 'none'
                and r['opacity'] == '1' and r['act'] == cnt):
            bad.append((nm, r, nat, cnt))
    chk('21 屏全部合规', not bad, bad[:3])

    print('\n═══ 画幅按屏自适应 ═══')
    for sid, want in [('home', 2276/1280), ('sjhj', 2048/1280),
                      ('sjaq', 2466/1280), ('sjfn_kjdlk', 1920/887)]:
        go(pg, sid)
        chk(f'{sid} 画幅', abs(ratio(pg) - want) < 0.02, ratio(pg))

    print('\n═══ 键盘 / 路由 ═══')
    go(pg, 'sjfn_kjdlk_p3')
    pg.keyboard.press('Escape'); pg.wait_for_timeout(350)
    chk('ESC 回首页', cur(pg) == 'home')
    pg.evaluate("location.hash='#sjfn_kjdlk_p5'"); pg.wait_for_timeout(500)
    chk('hash 路由到 GIS-5', cur(pg) == 'sjfn_kjdlk_p5', cur(pg))

    print('\n═══ 汇总 ═══')
    print(f'  {"✅ 全部通过" if not fails else "❌ 失败 " + str(len(fails)) + " 项"}')
    for f in fails:
        print(f'     - {f}')
    b.close()

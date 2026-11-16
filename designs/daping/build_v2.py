# -*- coding: utf-8 -*-
"""
大屏交互原型构建器 v2 —— 支持每屏独立的图片与热区
原则：图片只读（原样内嵌，不加滤镜/不加字/不裁切），交互全部是叠加层
交付：单文件 HTML，Windows / macOS 双击即开，无需启动包
"""
import base64
import pathlib
import json

ROOT = pathlib.Path('/opt/data/designs/daping')
IMG = ROOT / 'img'
OUT = ROOT / '四川省一体化数据平台_大屏交互.html'
OUT_DELIV = pathlib.Path('/opt/data/OutPut Box/四川省一体化数据平台_大屏交互.html')

W, H = 2276, 1280

# 每屏：名称、图片、标题热区(像素)、导航热区列表[(目标, 标签, 像素框)]
# 五张图的标题位置实测一致
TITLE_PX = (935, 18, 1555, 70)

SCREENS = {
    'home': dict(
        name='首页', img='p0_shouye.jpg', title_px=TITLE_PX,
        nav=[
            ('sjhj', '数据汇聚', (771, 103, 936, 150)),
            ('sjzl', '数据治理', (946, 103, 1109, 150)),
            ('sjfn', '数据赋能', (1119, 103, 1283, 150)),
            ('sjaq', '数据安全', (1293, 103, 1455, 150)),
        ],
    ),
    'sjzl': dict(   # 换成带四项导航的完整页；数据治理为金色当前项
        name='数据治理', img='p3_shujuzhili.jpg',
        title_px=(935, 20, 1585, 82),
        nav=[
            ('sjhj', '数据汇聚', (774, 105, 918, 150)),
            ('sjfn', '数据赋能', (1129, 105, 1273, 150)),
            ('sjaq', '数据安全', (1302, 105, 1446, 150)),
        ],
    ),
    'sjfn': dict(   # 首页「数据赋能」落地页，图上高亮的是「法人」
        name='数据赋能', img='p2_shujufuneng.jpg', title_px=TITLE_PX,
        nav=[
            ('sjfn_dfn', '数据赋能', (713, 100, 863, 160)),
            ('sjfn_zrr', '自然人',   (887, 100, 1037, 160)),
            ('sjfn_kjdlk', '空间地理库', (1240, 100, 1390, 160)),
        ],
    ),
    'sjfn_dfn': dict(   # 三级-数据赋能-数据赋能，图上高亮的是「数据赋能」
        name='数据赋能-数据赋能', img='p7_shujufuneng3.jpg',
        title_px=(935, 20, 1585, 82),
        nav=[
            ('sjfn_zrr', '自然人', (887, 100, 1037, 160)),
            ('sjfn',     '法人',   (1066, 100, 1216, 160)),
            ('sjfn_kjdlk', '空间地理库', (1240, 100, 1390, 160)),
            ('sjfn_yjs', '支撑高效办成一件事赋能进度', (30, 46, 326, 80)),
        ],
    ),
    'sjfn_yjs': dict(   # 三级-数据赋能-数据赋能-支撑高效办成一件事赋能进度
        name='数据赋能-支撑高效办成一件事', img='p12_yjs.jpg',
        title_px=(935, 20, 1585, 82),
        nav=[
            ('sjfn_zrr', '自然人', (887, 100, 1037, 160)),
            ('sjfn',     '法人',   (1066, 100, 1216, 160)),
            ('sjfn_kjdlk', '空间地理库', (1240, 100, 1390, 160)),
            ('sjfn_dfn', '支撑部门场景应用情况', (330, 46, 519, 80)),
        ],
    ),
    'sjfn_kjdlk': dict(   # 三级-数据赋能-空间地理库（浅色 GIS 地图页）
        name='数据赋能-空间地理库', img='p13_kjdlk.jpg',
        title_px=(690, 10, 1290, 55),
        nav=[
            ('sjfn_zrr', '自然人', (692, 84, 884, 132)),
            ('sjfn',     '法人',   (886, 84, 1078, 132)),
        ],
        chain=('gis', 0),
        w=1920, h=887),   # ⚠️ 第五种尺寸（2.16:1），浅色底图，导航仅 3 项
    'sjfn_kjdlk_p1': dict(
        name='空间地理库-1', img='p14_g1.jpg', title_px=(690, 10, 1290, 55),
        nav=[], chain=('gis', 1),
        w=1920, h=883),
    'sjfn_kjdlk_p2': dict(
        name='空间地理库-2', img='p14_g2.jpg', title_px=(690, 10, 1290, 55),
        nav=[], chain=('gis', 2),
        w=1920, h=880),
    'sjfn_kjdlk_p3': dict(
        name='空间地理库-3', img='p14_g3.jpg', title_px=(690, 10, 1290, 55),
        nav=[], chain=('gis', 3),
        w=1920, h=882),
    'sjfn_kjdlk_p4': dict(
        name='空间地理库-4', img='p14_g4.jpg', title_px=(690, 10, 1290, 55),
        nav=[], chain=('gis', 4),
        w=1920, h=885),
    'sjfn_kjdlk_p5': dict(
        name='空间地理库-5', img='p14_g5.jpg', title_px=(690, 10, 1290, 55),
        nav=[], chain=('gis', 5),
        w=1920, h=882),
    'sjfn_kjdlk_p6': dict(
        name='空间地理库-6', img='p14_g6.jpg', title_px=(690, 10, 1290, 55),
        nav=[], chain=('gis', 6),
        w=1920, h=884),
    'sjfn_kjdlk_p7': dict(
        name='空间地理库-7', img='p14_g7.jpg', title_px=(690, 10, 1290, 55),
        nav=[], chain=('gis', 7),
        w=1920, h=889),
    'sjfn_zrr': dict(
        name='数据赋能-自然人', img='p4_ziranren.jpg', title_px=TITLE_PX,
        nav=[],
        extra=[('ld', '人口流动分析', (2080, 38, 2230, 92), 'sjfn_zrr_ld')],
    ),
    'sjfn_zrr_ld': dict(
        name='自然人-人口流动', img='p5_renkouliudong.jpg', title_px=TITLE_PX,
        nav=[],
        extra=[('hj', '户籍人口分析', (1900, 38, 2060, 92), 'sjfn_zrr')],
    ),
    'sjhj': dict(name='数据汇聚', img='p1_shujuhuiju.jpg',
                 nav=[('sjhj_bm', '数据编目', (194, 86, 310, 124)),
                      ('sjhj_hj', '数据汇聚', (707, 86, 823, 124)),
                      ('sjhj_zrrku', '自然人库汇聚', (40, 364, 740, 410)),
                      ('sjhj_frku', '法人库汇聚', (40, 608, 740, 650))],
                 title_px=(645, 20, 1396, 62),   # 该图标题实测 x653-1388 y27-56
                 w=2048, h=1280),   # ⚠️ 第三种尺寸（1.6:1）；该图无主导航栏
    'sjhj_bm': dict(   # 三级-数据汇聚-数据编目（该页表头整体偏暗）
        name='数据汇聚-数据编目', img='p8_bianmu.jpg',
        nav=[('sjhj_hj', '数据汇聚', (786, 96, 916, 140))],
        title_px=(935, 22, 1338, 68),   # 标题实测 x949-1325 y29-61
        extra=[('close', '返回', (2142, 133, 2182, 170), '__back__', 'sjhj')],   # × 实测 x2153-2170 y143-159
        w=2276, h=1280),
    'sjhj_hj': dict(   # 三级-数据汇聚-汇聚更新弹层（背景即数据汇聚页，弹层覆盖主体）
        name='数据汇聚-汇聚更新', img='p9_huiju.jpg',
        nav=[('sjhj_bm', '数据编目', (194, 86, 310, 124))],
        title_px=(846, 20, 1199, 63),   # 标题实测 x853-1192 y26-56（偏暗）
        extra=[('close', '返回', (1996, 184, 2040, 218), '__back__', 'sjhj')],   # 弹层右上 ×
        w=2048, h=1280),
    'sjhj_zrrku': dict(   # 三级-数据汇聚-自然人库汇聚弹层
        name='数据汇聚-自然人库汇聚', img='p10_zrrku.jpg',
        nav=[('sjhj_bm', '数据编目', (194, 86, 310, 124))],
        title_px=(846, 20, 1199, 63),
        extra=[('close', '返回', (1998, 265, 2038, 301), '__back__', 'sjhj')],   # 弹层 × y277-289
        w=2048, h=1280),
    'sjhj_frku': dict(   # 三级-数据汇聚-法人库汇聚弹层
        name='数据汇聚-法人库汇聚', img='p11_frku.jpg',
        nav=[('sjhj_bm', '数据编目', (194, 86, 310, 124))],
        title_px=(846, 20, 1199, 63),
        extra=[('close', '返回', (1998, 233, 2038, 269), '__back__', 'sjhj')],   # 弹层 × y245-257
        w=2048, h=1280),
    'sjaq': dict(name='数据安全', img='p6_shujuaquan.jpg', nav=[],
                 title_px=(955, 8, 1503, 55),   # 该图标题实测 x971-1487 y15-45
                 w=2466, h=1280),   # ⚠️ 该页尺寸与其余页不同（1.93:1）
}
GIS_CHAIN = ['sjfn_kjdlk'] + [f'sjfn_kjdlk_p{i}' for i in range(1, 8)]
ORDER = ['home', 'sjhj', 'sjhj_bm', 'sjhj_hj', 'sjhj_zrrku', 'sjhj_frku',
         'sjzl', 'sjfn', 'sjfn_dfn', 'sjfn_yjs', 'sjfn_kjdlk',
         'sjfn_kjdlk_p1', 'sjfn_kjdlk_p2', 'sjfn_kjdlk_p3', 'sjfn_kjdlk_p4',
         'sjfn_kjdlk_p5', 'sjfn_kjdlk_p6', 'sjfn_kjdlk_p7',
         'sjfn_zrr', 'sjfn_zrr_ld', 'sjaq']


def pct(px, w=W, h=H):
    x0, y0, x1, y1 = px
    return (round(x0 / w * 100, 3), round(y0 / h * 100, 3),
            round((x1 - x0) / w * 100, 3), round((y1 - y0) / h * 100, 3))


def uri(p):
    return 'data:image/jpeg;base64,' + base64.b64encode(p.read_bytes()).decode()


def build():
    imgs, missing = {}, []
    for sid, d in SCREENS.items():
        p = IMG / d['img'] if d.get('img') else None
        if p and p.exists():
            imgs[sid] = uri(p)
        else:
            imgs[sid] = None
            missing.append(sid)

    fb = next((v for v in imgs.values() if v), None) if missing else None
    ph_css = ''
    if fb:
        ph_css = ('.ph{background-image:url(' + fb + ');background-size:contain;'
                  'background-position:center;background-repeat:no-repeat}'
                  '.ph::after{content:"";position:absolute;inset:0;'
                  'background:rgba(3,7,14,.75)}')

    secs, hots = [], []
    n = 0
    for sid in ORDER:
        d = SCREENS[sid]
        sw, sh = d.get('w', W), d.get('h', H)
        real = imgs[sid]
        inner = (f'<img class="shot" src="{real}" alt="{d["name"]}">' if real else
                 f'<div class="ph-badge"><b>{d["name"]}</b>'
                 f'<span>页面图片待补</span></div>')
        # 空间地理库翻页箭头（叠加层，不动原图）
        if d.get('chain'):
            ch, idx = d['chain']
            if idx > 0:
                inner += (f'<button class="arw up" type="button" data-go="{GIS_CHAIN[idx-1]}" '
                          f'title="返回上一页" aria-label="返回上一页">&#9650;</button>')
            if idx + 1 < len(GIS_CHAIN):
                inner += (f'<button class="arw dn" type="button" data-go="{GIS_CHAIN[idx+1]}" '
                          f'title="下一张" aria-label="下一张">&#9660;</button>')
        secs.append(f'<section class="screen{"" if real else " ph"}" id="scr-{sid}">{inner}</section>')

        # 标题 → 首页（首页自身不打热区）
        if sid != 'home':
            l, t, w, h = pct(d['title_px'], sw, sh)
            n += 1
            hots.append(f'<a class="hot" data-scr="{sid}" id="hot-t-{sid}" data-target="home" '
                        f'href="#home" title="返回首页" '
                        f'style="left:{l}%;top:{t}%;width:{w}%;height:{h}%">'
                        f'<i class="tip">返回首页</i></a>')

        # 导航
        for i, (tg, label, box) in enumerate(d.get('nav', []), 1):
            l, t, w, h = pct(box, sw, sh)
            n += 1
            hots.append(f'<a class="hot" data-scr="{sid}" id="hot-{sid}-n{i}" data-target="{tg}" '
                        f'href="#{tg}" title="{label}" '
                        f'style="left:{l}%;top:{t}%;width:{w}%;height:{h}%">'
                        f'<i class="tip">{label}</i></a>')

        # 额外热区（如图3 的 × 关闭）
        for item in d.get('extra', []):
            eid, label, box, tg = item[:4]
            fbk = item[4] if len(item) > 4 else None
            l, t, w, h = pct(box, sw, sh)
            n += 1
            if tg == '__back__':
                attr = f'data-back="1"' + (f' data-fallback="{fbk}"' if fbk else '')
                href = '#'
            else:
                attr = f'data-target="{tg}"'
                href = '#' + tg
            hots.append(f'<a class="hot" data-scr="{sid}" id="hot-{sid}-{eid}" {attr} '
                        f'href="{href}" title="{label}" '
                        f'style="left:{l}%;top:{t}%;width:{w}%;height:{h}%">'
                        f'<i class="tip">{label}</i></a>')

    names = json.dumps({k: v['name'] for k, v in SCREENS.items()}, ensure_ascii=False)
    ratios = json.dumps({k: round(v.get('w', W) / v.get('h', H), 6)
                         for k, v in SCREENS.items()})

    html = f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>四川省一体化数据平台</title>
<style>
  :root{{--ring:96,214,255}}
  *{{box-sizing:border-box}}
  html,body{{margin:0;height:100%;background:#05080f;overflow:hidden;
    font-family:"Noto Sans SC","Microsoft YaHei","PingFang SC",sans-serif}}
  #stage{{position:fixed;inset:0;overflow:hidden}}
  #frame{{position:absolute;left:50%;top:50%;transform:translate(-50%,-50%)}}
  .screen{{position:absolute;inset:0;opacity:0;visibility:hidden;transition:opacity .2s ease-out}}
  .screen.on{{opacity:1;visibility:visible}}
  .shot{{display:block;width:100%;height:100%;object-fit:contain;user-select:none;
    -webkit-user-drag:none;pointer-events:none}}
  {ph_css}
  .ph-badge{{position:absolute;left:50%;top:52%;transform:translate(-50%,-50%);
    text-align:center;color:#dbeafe;pointer-events:none;z-index:2}}
  .ph-badge b{{display:block;font-size:clamp(20px,2.4vw,42px);font-weight:600;letter-spacing:.08em}}
  .ph-badge span{{display:block;margin-top:10px;font-size:clamp(12px,1vw,17px);
    color:#7f9cc4;letter-spacing:.14em}}
  .hot{{position:absolute;display:block;border-radius:4px;text-decoration:none;outline:none;
    border:1px solid transparent;
    transition:background-color .16s ease-out,border-color .16s ease-out}}
  .hot .tip{{position:absolute;left:50%;top:100%;transform:translate(-50%,6px);white-space:nowrap;
    font-size:12px;line-height:1;padding:5px 9px;border-radius:3px;
    background:rgba(8,20,38,.94);border:1px solid rgba(var(--ring),.45);color:#cfe6ff;
    opacity:0;transition:opacity .16s ease-out;pointer-events:none}}
  @media (hover:hover) and (pointer:fine){{
    .hot:hover{{background:rgba(var(--ring),.10);border-color:rgba(var(--ring),.55)}}
    .hot:hover .tip{{opacity:1}}
  }}
  .hot:focus-visible{{border-color:rgba(var(--ring),.85);background:rgba(var(--ring),.12)}}
  .hot:focus-visible .tip{{opacity:1}}
  .hot{{pointer-events:none;opacity:0}}
  .hot.act{{pointer-events:auto;opacity:1}}
  .hot.cur .tip{{display:none}}
  .arw{{position:absolute;right:2.2%;width:clamp(32px,3.2vw,56px);height:clamp(32px,3.2vw,56px);
    border-radius:50%;border:1px solid rgba(var(--ring),.55);background:rgba(8,20,38,.74);
    color:#bfe4ff;font-size:clamp(13px,1.3vw,20px);line-height:1;cursor:pointer;
    display:flex;align-items:center;justify-content:center;z-index:6;padding:0;
    opacity:.55;
    box-shadow:0 2px 14px rgba(0,0,0,.45);
    transition:opacity .18s ease-out,background-color .16s ease-out,
               border-color .16s ease-out,transform .16s ease-out}}
  .arw:hover,.arw:focus-visible{{opacity:1;background:rgba(var(--ring),.26);
    border-color:rgba(var(--ring),.95);transform:scale(1.07)}}
  @media (hover:none){{.arw{{opacity:.85}}}}
  .arw:focus-visible{{outline:2px solid rgba(var(--ring),.9);outline-offset:2px}}
  .arw.dn{{bottom:5%}}
  .arw.up{{bottom:calc(5% + clamp(40px,4vw,66px))}}
  body.hide-tips .hot{{border-color:transparent!important;background:transparent!important}}
  body.hide-tips .hot .tip{{opacity:0!important}}
  .hint{{position:fixed;left:12px;bottom:10px;color:#5b7ea8;font-size:12px;
    letter-spacing:.04em;pointer-events:none;z-index:5}}
  @media (prefers-reduced-motion:reduce){{.screen,.hot,.hot .tip{{transition:none!important}}}}
</style></head>
<body>
<div id="stage"><div id="frame">
{chr(10).join(secs)}
{chr(10).join(hots)}
</div></div>
<div class="hint">H 隐藏提示 · ← → 翻页 · ESC 回首页 · F 全屏</div>
<script>
(function(){{
  var NAMES={names}, ORDER={json.dumps(ORDER)}, RATIOS={ratios}, W={W}, H={H};
  var frame=document.getElementById('frame'), cur=null, stack=[];
  function fit(){{
    var r=RATIOS[cur]||(W/H);
    var vw=innerWidth,vh=innerHeight,w=vw,h=vw/r;
    if(h>vh){{h=vh;w=vh*r}}
    frame.style.width=w+'px';frame.style.height=h+'px';
    frame.style.aspectRatio=String(r);
  }}
  function go(id, isBack){{
    if(!NAMES[id])id='home';
    var nx=document.getElementById('scr-'+id); if(!nx)return;
    if(!isBack && cur && cur!==id && stack[stack.length-1]!==cur) stack.push(cur);
    [].forEach.call(document.querySelectorAll('.screen'),function(s){{s.classList.remove('on')}});
    nx.classList.add('on'); cur=id;
    [].forEach.call(document.querySelectorAll('.hot'),function(a){{
      var mine = a.getAttribute('data-scr')===id;
      a.classList.toggle('act', mine);
      a.classList.toggle('cur', mine && a.getAttribute('data-target')===id);
    }});
    if(location.hash.slice(1)!==id) history.replaceState(null,'','#'+id);
    document.title=id==='home'?'四川省一体化数据平台':NAMES[id]+' - 四川省一体化数据平台';
    window.__daping.last=id;
    fit();
  }}
  function back(fb){{
    var prev=stack.pop();
    if(prev && NAMES[prev] && prev!==cur) go(prev,true);
    else go((fb && NAMES[fb]) ? fb : 'home', true);
  }}
  [].forEach.call(document.querySelectorAll('.hot'),function(a){{
    a.addEventListener('click',function(e){{
      e.preventDefault();
      if(a.getAttribute('data-back')) back(a.getAttribute('data-fallback'));
      else go(a.getAttribute('data-target'));
    }});
  }});
  [].forEach.call(document.querySelectorAll('.arw'),function(b){{
    b.addEventListener('click',function(e){{
      e.preventDefault(); e.stopPropagation(); go(b.getAttribute('data-go'));
    }});
  }});
  addEventListener('keydown',function(e){{
    var k=e.key;
    if(k==='h'||k==='H'){{document.body.classList.toggle('hide-tips');return}}
    if(k==='f'||k==='F'){{
      if(!document.fullscreenElement){{(document.documentElement.requestFullscreen||function(){{}})()}}
      else{{(document.exitFullscreen||function(){{}})()}} return}}
    if(k==='Escape'){{go('home');return}}
    if(k==='ArrowRight'||k==='ArrowLeft'){{
      var i=ORDER.indexOf(cur), n=k==='ArrowRight'?i+1:i-1;
      n=Math.max(0,Math.min(ORDER.length-1,n)); go(ORDER[n]);
    }}
  }});
  addEventListener('resize',fit);
  addEventListener('hashchange',function(){{go(location.hash.slice(1)||'home')}});
  window.__daping={{go:go,current:function(){{return cur}},order:ORDER,names:NAMES,
    hotspotCount:document.querySelectorAll('.hot').length}};
  fit(); go(location.hash.slice(1)||'home');
}})();
</script></body></html>
'''
    OUT.write_text(html, encoding='utf-8')
    OUT_DELIV.parent.mkdir(parents=True, exist_ok=True)
    OUT_DELIV.write_text(html, encoding='utf-8')
    return OUT, missing, n


if __name__ == '__main__':
    import os
    out, missing, n = build()
    print(f'✅ {out}')
    print(f'   单文件 {os.path.getsize(out)/1024:.0f} KB   热区 {n} 个')
    print(f'   待补图片的屏: {missing}')

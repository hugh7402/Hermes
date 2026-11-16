# -*- coding: utf-8 -*-
"""
大屏交互原型构建器
- 图片只读：原图 base64 内嵌，不改色不加字不裁切
- 交互全部为叠加层：导航热区、标题返回、悬停提示
- 单文件 HTML，Windows / macOS 双击即开，无需启动包
生成器可反复跑：把新图片放进 img/ 并登记到 SCREENS 即可。
"""
import base64
import pathlib
import json

ROOT = pathlib.Path('/opt/data/designs/daping')
IMG_DIR = ROOT / 'img'
OUT = ROOT / '四川省一体化数据平台_大屏交互.html'
OUT_DELIV = pathlib.Path('/opt/data/OutPut Box/四川省一体化数据平台_大屏交互.html')

# 原图基准尺寸（热区按此图量的像素坐标，再换算成百分比）
BASE_W, BASE_H = 2276, 1280

# ── 屏定义：id -> (显示名, 图片文件 或 None) ──
SCREENS = {
    'home': ('首页',              None),
    'sjhj': ('数据汇聚',          'p1_shujuhuiju.jpg'),
    'sjzl': ('数据治理',          None),
    'sjfn': ('数据赋能',          None),
    'sjaq': ('数据安全',          None),
}

ORDER = ['home', 'sjhj', 'sjzl', 'sjfn', 'sjaq']

# ── 热区：像素坐标 (x0, y0, x1, y1)，来自对原图的像素级探测 ──
# 文字实测框 + 四周留出点击余量
PAD_X, PAD_Y = 46, 20

HOTSPOTS = [
    # 标题 → 返回首页
    dict(id='hot-title', target='home', label='返回首页',
         px=(949 - 20, 29 - 14, 1326 + 20, 58 + 14)),
    # 四个导航
    dict(id='hot-nav-1', target='sjhj', label='数据汇聚',
         px=(817 - PAD_X, 103, 890 + PAD_X, 150)),
    dict(id='hot-nav-2', target='sjzl', label='数据治理',
         px=(992 - PAD_X, 103, 1063 + PAD_X, 150)),
    dict(id='hot-nav-3', target='sjfn', label='数据赋能',
         px=(1165 - PAD_X, 103, 1237 + PAD_X, 150)),
    dict(id='hot-nav-4', target='sjaq', label='数据安全',
         px=(1339 - PAD_X, 103, 1409 + PAD_X, 150)),
]


def pct(px):
    x0, y0, x1, y1 = px
    return dict(
        left=round(x0 / BASE_W * 100, 3),
        top=round(y0 / BASE_H * 100, 3),
        width=round((x1 - x0) / BASE_W * 100, 3),
        height=round((y1 - y0) / BASE_H * 100, 3),
    )


def b64(path):
    return base64.b64encode(path.read_bytes()).decode()


def build():
    # 各屏图片
    imgs = {}
    missing = []
    for sid, (name, fn) in SCREENS.items():
        p = IMG_DIR / fn if fn else None
        if p and p.exists():
            imgs[sid] = 'data:image/jpeg;base64,' + b64(p)
        else:
            imgs[sid] = None
            missing.append(sid)

    # 占位屏复用唯一可用的图做底（压暗），保证导航始终可点。
    # 用 CSS 类共享一份 base64，避免同一张图被内嵌多次。
    fallback = next((v for v in imgs.values() if v), None)
    ph_css = ''
    if fallback:
        ph_css = ('.ph{ background-image:url(' + fallback + ');'
                  ' background-size:contain; background-position:center;'
                  ' background-repeat:no-repeat; }\n'
                  '  .ph::after{ content:""; position:absolute; inset:0;'
                  ' background:rgba(3,7,14,.72); }')

    screens_html = []
    for sid in ORDER:
        name = SCREENS[sid][0]
        real = imgs[sid]
        if real:
            body = f'<img class="shot" src="{real}" alt="{name}">'
            cls = 'screen'
            badge = ''
        else:
            body = ''
            cls = 'screen ph'
            badge = f'<div class="ph-badge"><b>{name}</b><span>页面图片待补</span></div>'
        screens_html.append(
            f'<section class="{cls}" id="scr-{sid}" data-name="{name}">{body}{badge}</section>'
        )

    hots = []
    for h in HOTSPOTS:
        p = pct(h['px'])
        hots.append(
            f'<a class="hot" id="{h["id"]}" data-target="{h["target"]}" '
            f'href="#{h["target"]}" title="{h["label"]}" '
            f'style="left:{p["left"]}%;top:{p["top"]}%;width:{p["width"]}%;height:{p["height"]}%">'
            f'<i class="tip">{h["label"]}</i></a>'
        )

    nav_names = json.dumps({k: v[0] for k, v in SCREENS.items()}, ensure_ascii=False)

    html = f'''<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>四川省一体化数据平台</title>
<style>
  :root{{ --ring: 96,214,255; }}
  *{{ box-sizing:border-box; }}
  html,body{{ margin:0; height:100%; background:#05080f; overflow:hidden;
              font-family:"Noto Sans SC","Microsoft YaHei","PingFang SC",sans-serif; }}
  #stage{{ position:relative; width:100vw; height:100vh; overflow:hidden; }}
  #frame{{ position:absolute; left:50%; top:50%; transform:translate(-50%,-50%);
           aspect-ratio:{BASE_W} / {BASE_H}; }}
  .screen{{ position:absolute; inset:0; opacity:0; visibility:hidden;
            transition:opacity .2s ease-out; }}
  .screen.on{{ opacity:1; visibility:visible; }}
  .shot{{ display:block; width:100%; height:100%; object-fit:contain; user-select:none;
          -webkit-user-drag:none; pointer-events:none; }}
  {ph_css}

  .ph-badge{{ position:absolute; left:50%; top:52%; transform:translate(-50%,-50%);
             text-align:center; color:#dbeafe; pointer-events:none; }}
  .ph-badge b{{ display:block; font-size:clamp(20px,2.2vw,40px); font-weight:600;
                letter-spacing:.08em; }}
  .ph-badge span{{ display:block; margin-top:10px; font-size:clamp(12px,1vw,17px);
                   color:#7f9cc4; letter-spacing:.14em; }}

  .hot{{ position:absolute; display:block; border-radius:4px;
         text-decoration:none; outline:none;
         border:1px solid transparent;
         transition:background-color .16s ease-out, border-color .16s ease-out; }}
  .hot .tip{{ position:absolute; left:50%; top:100%; transform:translate(-50%,6px);
              white-space:nowrap; font-size:12px; line-height:1; padding:5px 9px;
              border-radius:3px; background:rgba(8,20,38,.92);
              border:1px solid rgba(var(--ring),.45); color:#cfe6ff;
              opacity:0; transition:opacity .16s ease-out; pointer-events:none; }}
  @media (hover:hover) and (pointer:fine){{
    .hot:hover{{ background:rgba(var(--ring),.10);
                 border-color:rgba(var(--ring),.55); }}
    .hot:hover .tip{{ opacity:1; }}
  }}
  .hot:focus-visible{{ border-color:rgba(var(--ring),.85);
                       background:rgba(var(--ring),.12); }}
  .hot:focus-visible .tip{{ opacity:1; }}

  .hot.cur .tip{{ display:none; }}
  body.hide-tips .hot{{ border-color:transparent !important; background:transparent !important; }}
  body.hide-tips .hot .tip{{ opacity:0 !important; }}

  .hint{{ position:fixed; left:12px; bottom:10px; color:#5b7ea8; font-size:12px;
          letter-spacing:.04em; pointer-events:none; }}
  @media (prefers-reduced-motion: reduce){{
    .screen,.hot,.hot .tip{{ transition:none !important; }}
  }}
</style>
</head>
<body>
<div id="stage"><div id="frame">
{chr(10).join(screens_html)}
{chr(10).join(hots)}
</div></div>
<div class="hint">H 隐藏提示 · ← → 翻页 · F 全屏</div>
<script>
(function(){{
  var NAMES = {nav_names};
  var ORDER = {json.dumps(ORDER)};
  var frame = document.getElementById('frame');
  var stage = document.getElementById('stage');
  var cur = null;

  function fit(){{
    var vw = window.innerWidth, vh = window.innerHeight;
    var r = {BASE_W} / {BASE_H};
    var w = vw, h = vw / r;
    if (h > vh) {{ h = vh; w = vh * r; }}
    frame.style.width = w + 'px';
    frame.style.height = h + 'px';
  }}

  function go(id){{
    if (!NAMES[id]) id = 'home';
    var next = document.getElementById('scr-' + id);
    if (!next) return;
    Array.prototype.forEach.call(document.querySelectorAll('.screen'), function(s){{
      s.classList.remove('on');
    }});
    next.classList.add('on');
    cur = id;
    Array.prototype.forEach.call(document.querySelectorAll('.hot'), function(a){{
      if (a.getAttribute('data-target') === id) a.classList.add('cur');
      else a.classList.remove('cur');
    }});
    if (location.hash.slice(1) !== id) history.replaceState(null,'', '#' + id);
    document.title = (id === 'home' ? '四川省一体化数据平台'
                                   : NAMES[id] + ' - 四川省一体化数据平台');
    window.__daping.last = id;
  }}

  Array.prototype.forEach.call(document.querySelectorAll('.hot'), function(a){{
    a.addEventListener('click', function(e){{
      e.preventDefault();
      go(a.getAttribute('data-target'));
    }});
  }});

  document.addEventListener('keydown', function(e){{
    var k = e.key;
    if (k === 'h' || k === 'H'){{ document.body.classList.toggle('hide-tips'); return; }}
    if (k === 'f' || k === 'F'){{
      if (!document.fullscreenElement) {{ (document.documentElement.requestFullscreen||function(){{}})(); }}
      else {{ (document.exitFullscreen||function(){{}})(); }}
      return;
    }}
    if (k === 'Escape' && cur !== 'home') {{ go('home'); return; }}
    if (k === 'ArrowRight' || k === 'ArrowLeft'){{
      var i = ORDER.indexOf(cur);
      var n = (k === 'ArrowRight') ? i + 1 : i - 1;
      if (n < 0) n = 0;
      if (n >= ORDER.length) n = ORDER.length - 1;
      go(ORDER[n]);
    }}
  }});

  window.addEventListener('resize', fit);
  window.addEventListener('hashchange', function(){{
    go(location.hash.slice(1) || 'home');
  }});

  window.__daping = {{
    go: go,
    current: function(){{ return cur; }},
    order: ORDER,
    names: NAMES,
    hotspotCount: document.querySelectorAll('.hot').length
  }};

  fit();
  go(location.hash.slice(1) || 'home');
}})();
</script>
</body>
</html>
'''
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding='utf-8')
    OUT_DELIV.parent.mkdir(parents=True, exist_ok=True)
    OUT_DELIV.write_text(html, encoding='utf-8')
    return OUT, missing, imgs


if __name__ == '__main__':
    out, missing, imgs = build()
    import os
    size = os.path.getsize(out)
    print(f'✅ {out}')
    print(f'   单文件 {size/1024:.0f} KB')
    real = [k for k, v in imgs.items() if v]
    print(f'   已有图片的屏: {real}')
    print(f'   待补图片的屏: {missing}')

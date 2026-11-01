#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""打包：src/ + screens/ + data/ → 单文件自包含 HTML（零外链、零 CDN、断网可用）
   数据压缩：rows 用「列名数组 + 行值数组」而非对象数组，体积降 60%+
"""
import json, pathlib, re, sys

ROOT = pathlib.Path('/opt/data/designs/drs-demo')
SRC = ROOT / 'proto' / 'src'
SCR = ROOT / 'proto' / 'screens'
DATA = ROOT / 'data'
OUT_DIR = ROOT / '交付'
OUT_DIR.mkdir(parents=True, exist_ok=True)

def rd(p):
    return pathlib.Path(p).read_text(encoding='utf-8')

# ── 1. 数据压缩 ──
ds = json.loads((DATA / 'demo_dataset.json').read_text(encoding='utf-8'))
COLS = ['zrrwybs', 'sfzjlx', 'sfzjhm', 'xm', 'cym', 'xb', 'csrq', 'mz', 'gj',
        'zzmm', 'zjxy', 'byzk', 'cd_time', 'col_date_lt', 'hjdssxdm']
COLS_CN = ['自然人唯一标识', '身份证件类型', '身份证件号码', '姓名', '曾用名', '性别',
           '出生日期', '民族', '国籍', '政治面貌', '宗教信仰', '兵役状况',
           '数据批次号', '数据融合加工时间', '户籍地省市县代码']
assert set(COLS) == set(ds['rows'][0].keys()) - {'_rid'}, '列定义与数据不符'

def pack(rows):
    return [[r.get(c, '') for c in COLS] for r in rows]

problems = [{
    'n': i + 1, 't': p['type'], 'f': p['field'], 'rid': p['_rid'],
    'key': p['key'], 'o': p['orig'], 'a': p['authority'],
    'act': p['action'], 'rule': p['rule'],
} for i, p in enumerate(ds['problems'])]

DATA_JS = {
    'catalog': {'name': ds['catalog']['name'], 'code': ds['catalog']['code']},
    'stats': ds['stats'],
    'problems': problems,
    'rules': ds['rule_standard'],
    'source': ds['rule_source'],
    'cols': COLS, 'colsCn': COLS_CN,
    'rows': pack(ds['rows']),
    'auth': pack(ds['authority_rows']),
    'fields': [{'cn': f['cn'], 'en': f['en'], 'type': f['type'], 'len': f['len'],
                'pk': f['pk'], 'nullable': f['nullable'], 'sens': f['sensitivity'],
                'desc': f.get('desc', '')} for f in ds['catalog']['fields']],
}
# 数据项元数据（s1 用）
ds_items = []
for it in ds['catalog']['items']:
    ds_items.append({'cn': it['cn'], 'en': it['en'], 'desc': it['desc'], 'type': it['type'],
                     'len': it['len'], 'has_domain': it['has_domain'], 'domain_name': it['domain_name'],
                     'pk': it['pk'], 'nullable': it['nullable'], 'share': it['share'],
                     'share_cond': it['share_cond'], 'open': it['open'], 'open_cond': it['open_cond'],
                     'src_sys': it['src_sys'], 'src_cat': it['src_cat'],
                     'sensitivity': it['sensitivity'], 'legal_source': it['legal_source'],
                     'for_reg': it['for_reg']})
DATA_JS['catalog']['items'] = ds_items

def js(v):
    return json.dumps(v, ensure_ascii=False, separators=(',', ':'))

# ── 2. 组装 ──
css = rd(SRC / 'style.css')
form_spec = rd(DATA / 'form_spec.json')

scrs = sorted(SCR.glob('s*.js'), key=lambda p: (len(p.stem), p.stem))
js_parts = [rd(SRC / 'app.js')] + [rd(p) for p in scrs]

html = f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>四川省一体化数据资源管理系统</title>
<style>
{css}
</style>
</head>
<body>
<div id="root"></div>
<script>
/* ===== 数据资源目录与治理数据集 ===== */
window.DATA = {js(DATA_JS)};
/* ===== 表单字段规范（7 属性组 / 54 字段，取自《政务数据目录填写清单0910-样例》）===== */
window.FORM_SPEC = {form_spec};
</script>
<script>
{chr(10).join(js_parts)}
</script>
</body>
</html>
"""

VER = 'V3.1'
out = OUT_DIR / ('四川一体化数据资源管理系统_' + VER + '.html')

# 清理交付目录里历史遗留的其它 .html，避免测试/演示误开旧版本
for _stale in OUT_DIR.glob('*.html'):
    if _stale.resolve() != out.resolve():
        _stale.unlink()
        print(f'  🧹 已清理历史遗留文件：{_stale.name}')
out.write_text(html, encoding='utf-8')

# ── 3. 自包含性校验 ──
bad_http = re.findall(r'(?:src|href)\s*=\s*["\']https?://', html)
bad_script = re.findall(r'<script[^>]+src=', html)
bad_link = re.findall(r'<link[^>]+rel=["\']stylesheet', html)
print('════ 打包完成 ════')
print(f'  文件：{out}')
print(f'  大小：{out.stat().st_size/1024:.0f} KB   行数：{len(html.splitlines())}')
print(f'  含：{len(scrs)} 个屏幕文件 | CSS {len(css.splitlines())} 行')
print(f'  数据：{len(DATA_JS["rows"])} 行归集数据 / {len(DATA_JS["auth"])} 行权威源 / {len(problems)} 条问题')
print()
print('  ── 自包含性 ──')
print(f'  外链 http(s) 引用：{len(bad_http)}  {"✅" if not bad_http else "❌ " + str(bad_http[:3])}')
print(f'  <script src>     ：{len(bad_script)}  {"✅" if not bad_script else "❌"}')
print(f'  <link stylesheet>：{len(bad_link)}  {"✅" if not bad_link else "❌"}')
print(f'  零外部依赖：{"✅ 断网可用" if not (bad_http or bad_script or bad_link) else "❌ 存在外部依赖"}')
print()
# ── 4. JS 语法校验（构建期拦下语法错误）──
import subprocess, tempfile
print()
print('  ── JS 语法校验 ──')
ok_all = True
for idx, blk in enumerate(re.findall(r'<script>([\s\S]*?)</script>', html)):
    with tempfile.NamedTemporaryFile('w', suffix='.js', delete=False, encoding='utf-8') as f:
        f.write(blk); tf = f.name
    r = subprocess.run(['node', '--check', tf], capture_output=True, text=True)
    if r.returncode == 0:
        print(f'     script[{idx}] {len(blk.splitlines()):5d} 行  ✅ 语法通过')
    else:
        ok_all = False
        print(f'     script[{idx}] ❌ 语法错误：')
        for L in (r.stderr or '').splitlines()[:8]:
            print('        ' + L)
    pathlib.Path(tf).unlink(missing_ok=True)
if not ok_all:
    import sys as _s
    print('\n  ❌ 存在 JS 语法错误，交付物不可用 —— 请先修复')
    _s.exit(2)

print('  ── 屏幕文件 ──')
for p in scrs:
    print(f'     {p.name:12s} {p.stat().st_size/1024:6.1f} KB')
if len(scrs) < 8:
    print(f'  ⚠️ 只找到 {len(scrs)} 个屏幕文件，预期 8 个')


# ── 6. 交付内容合规门禁：界面内不得出现演示/评审字眼与真实姓名 ──
BAN = ['采购需求', '系统演示', '演示原型', '演示环境', '演示脚本', '演示', '投标',
       '三级审核', '初审', '复审', '终审',
       '张建平', '李文婧', '王振国', '陈立言', '赵海涛', '刘思远']
print()
print('  ── 交付内容合规校验 ──')
_bad = [(w, len(re.findall(w, html))) for w in BAN]
_bad = [(w, n) for w, n in _bad if n]
if _bad:
    for w, n in _bad:
        print(f'     [X] 「{w}」出现 {n} 次')
    print('\n  [X] 交付物含违规字眼，按真实系统交付前必须清除')
    import sys as _s2
    _s2.exit(3)
print(f'     [OK] {len(BAN)} 类敏感词全部为 0（界面按真实系统呈现，无完整姓名、无审核层级残留）')

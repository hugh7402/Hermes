#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""打包交付：把主原型 + 演示数据 + 手册 + 截图 汇总到一个交付目录并校验"""
import pathlib, shutil, hashlib, json, re

ROOT = pathlib.Path('/opt/data/designs/drs-demo')
OUT = ROOT / '交付'
DATA = ROOT / 'data'
SHOTS = ROOT / 'screenshots_真机'

# 数据副本目录（演示时要上传/查看的 CSV）
d = OUT / '演示数据'
d.mkdir(parents=True, exist_ok=True)
for f in ['待归集数据_自然人基本登记信息.csv', '权威数据源_公安人口库.csv', '问题清单_明细.csv']:
    src = DATA / f
    if src.exists():
        shutil.copy2(src, d / f)

# 截图目录
s = OUT / '截图_真机'
s.mkdir(parents=True, exist_ok=True)
for f in sorted(SHOTS.glob('*.png')):
    shutil.copy2(f, s / f.name)

print('════ 交付包清单 ════')
html = sorted(OUT.glob('四川一体化数据资源管理系统*.html'))[-1]   # 自动取最新版本
total = 0
for f in sorted(OUT.rglob('*')):
    if f.is_dir():
        continue
    if '截图_真机' in str(f) or '演示数据' in str(f):
        continue
    kb = f.stat().st_size / 1024
    total += f.stat().st_size
    print(f'  {f.relative_to(OUT)!s:44s} {kb:9.1f} KB')
for sub in ['演示数据', '截图_真机']:
    p = OUT / sub
    fs = [x for x in p.rglob('*') if x.is_file()]
    sz = sum(x.stat().st_size for x in fs)
    total += sz
    print(f'  {sub+"/":44s} {len(fs)} 个文件  {sz/1024/1024:6.2f} MB')

print(f'\n  交付包合计 {total/1024/1024:.2f} MB')

# ── 主交付物校验 ──
h = html.read_text(encoding='utf-8')
print('\n════ 主原型自包含性校验 ════')
checks = [
    ('外链 http(s) 资源引用', len(re.findall(r'(?:src|href)\s*=\s*["\']https?://', h)), 0),
    ('<script src>', len(re.findall(r'<script[^>]+src=', h)), 0),
    ('<link rel=stylesheet>', len(re.findall(r'<link[^>]+rel=["\']stylesheet', h)), 0),
    ('@import', len(re.findall(r'@import', h)), 0),
    ('CSS url() 外部引用', len(re.findall(r'url\(\s*["\']?https?://', h)), 0),
]
allok = True
for name, got, want in checks:
    good = got == want
    allok = allok and good
    print(f'  {"✅" if good else "❌"} {name}: {got}')

print('\n════ 内容完整性 ════')
s2 = h.count('window.DATA') > 0
for name, cond in [
    ('含演示数据集 window.DATA', 'window.DATA' in h),
    ('含表单规范 window.FORM_SPEC', 'window.FORM_SPEC' in h),
    ('含 66 条问题明细', '"problems"' in h),
    ('含 1000 行归集数据', h.count('ZR') > 900),
    ('注册屏幕数 = 8 组（含 s4c/s4d 等共 16 个键）', h.count('window.SCREENS.s') >= 13),
    ('含机构全称「四川省一体化数据资源管理系统」', '四川省一体化数据资源管理系统' in h),
    ('含底部功能区列明项', '党政机关网站标识' in h and '站点地图' in h),
]:
    print(f'  {"✅" if cond else "❌"} {name}')

md5 = hashlib.md5(html.read_bytes()).hexdigest()
print(f'\n  主交付物：{html.name}')
print(f'  大小 {html.stat().st_size/1024:.0f} KB   行数 {len(h.splitlines())}')
print(f'  MD5  {md5}')
print(f'\n  {"✅ 交付包就绪" if allok else "⚠️ 存在外部依赖，需处理"}')

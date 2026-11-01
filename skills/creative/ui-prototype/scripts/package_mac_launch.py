#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""打包 macOS 演示启动包：交付 HTML + 启动脚本 → zip（保留执行位）+ tar.gz。

用法:
    python3 package_mac_launch.py <交付.html> <项目名> <新版本号> [--src-template <上一版启动包目录>]

行为：
  1) 以 --src-template（上一版启动包目录）为模板，拷 serve.py / 启动.command / 启动.sh / 使用说明.md；
     没有模板时只放 index.html 并在输出里提醒补齐启动脚本。
  2) HTML 落成 index.html，**校验 MD5 与交付版一致**。
  3) 包内所有文件里的旧版本号→新版本号（使用说明.md / 启动脚本常有残留）。
  4) zip 用 zipfile 手工写 ZipInfo，.command/.sh 设 0755 执行位——本机通常没有 zip 命令，
     且微信 + macOS 只看执行位，丢了双击不响应。
  5) 另出一份 .tar.gz（mac 双击可解压）。
"""
import argparse
import hashlib
import pathlib
import re
import shutil
import subprocess
import zipfile

PKG_FILES = ['serve.py', '启动.command', '启动.sh', '使用说明.md']
OUT_ROOT = pathlib.Path('/opt/data/OutPut Box')


def md5(p: pathlib.Path) -> str:
    return hashlib.md5(p.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('html')
    ap.add_argument('name')
    ap.add_argument('ver')
    ap.add_argument('--src-template', default='')
    ap.add_argument('--old-ver', default='V2.9')
    a = ap.parse_args()

    html = pathlib.Path(a.html).resolve()
    pkg = OUT_ROOT / f'{a.name}-启动包_mac版_{a.ver}'
    if pkg.exists():
        shutil.rmtree(pkg)
    pkg.mkdir(parents=True)

    if a.src_template:
        tmpl = pathlib.Path(a.src_template)
        for f in PKG_FILES:
            src = tmpl / f
            if src.exists():
                shutil.copy2(src, pkg / f)
    shutil.copy2(html, pkg / 'index.html')

    if md5(pkg / 'index.html') != md5(html):
        raise SystemExit('  ❌ index.html 与交付版 MD5 不一致')
    print(f'  ✅ index.html MD5 一致：{md5(html)}')

    for f in pkg.iterdir():
        if f.suffix.lower() in ('.md', '.command', '.sh'):
            txt = f.read_text(encoding='utf-8', errors='ignore')
            new = re.sub(re.escape(a.old_ver), a.ver, txt)
            if new != txt:
                f.write_text(new, encoding='utf-8')
                print(f'  ✅ {f.name}: {a.old_ver} → {a.ver}')
    for f in pkg.iterdir():
        left = re.findall(re.escape(a.old_ver), f.read_text(encoding='utf-8', errors='ignore')) if f.is_file() else []
        if left:
            print(f'  ⚠️ {f.name} 仍有 {len(left)} 处 {a.old_ver}')

    zpath = pkg.with_suffix('.zip')
    if zpath.exists():
        zpath.unlink()
    with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for f in sorted(pkg.rglob('*')):
            if not f.is_file():
                continue
            arc = pathlib.Path(pkg.name) / f.relative_to(pkg)
            info = zipfile.ZipInfo(str(arc))
            mode = 0o755 if f.name.endswith(('.command', '.sh')) else 0o644
            info.external_attr = mode << 16          # ← 执行位：丢了 mac 双击无效
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, f.read_bytes())
    print(f'  ✅ {zpath.name}  {zpath.stat().st_size/1024:.0f}KB')

    tpath = pkg.with_suffix('.tar.gz')
    subprocess.run(['tar', '-czf', str(tpath), '-C', str(pkg.parent), pkg.name], check=True)
    print(f'  ✅ {tpath.name}  {tpath.stat().st_size/1024:.0f}KB')

    with zipfile.ZipFile(zpath) as z:
        for i in z.infolist():
            print(f'     {oct(i.external_attr >> 16)[-3:]}  {i.filename}')


if __name__ == '__main__':
    main()

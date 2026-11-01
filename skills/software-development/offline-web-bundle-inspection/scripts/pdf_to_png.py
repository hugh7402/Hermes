#!/usr/bin/env python3
"""把 printToPDF 导出的 PDF 批量转成 PNG，并标出“哪页才有内容”。

用法:
    python3 pdf_to_png.py <pdf 或 目录> [--dpi 140]

为什么要这个脚本：单页 HTML 动辄 10MB+，直接 Page.captureScreenshot 会 60s 超时；
改走 printToPDF 再用 PyMuPDF 转图又快又稳。但 paperHeight 算不准时内容会被推到第 2 页，
第 1 页往往是空白（几十 KB）——所以本脚本会把每页 PNG 的体积打印出来，体积大的才是有内容的那页。
"""
import sys
import pathlib

import fitz  # PyMuPDF


def convert(pdf: pathlib.Path, outdir: pathlib.Path, dpi: int) -> list[tuple[int, pathlib.Path, int, int]]:
    outdir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(pdf)
    made = []
    for i, page in enumerate(doc, 1):
        pix = page.get_pixmap(dpi=dpi)
        out = outdir / f'{pdf.stem}_p{i}.png'
        pix.save(out)
        made.append((i, out, pix.width, pix.height))
    doc.close()
    return made


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if not args:
        print(__doc__)
        return 2
    dpi = 140
    for a in sys.argv[1:]:
        if a.startswith('--dpi'):
            dpi = int(a.split('=', 1)[1]) if '=' in a else dpi
    dpi_arg = next((a for a in sys.argv if a.startswith('--dpi')), None)
    if dpi_arg and ' ' in dpi_arg:
        dpi = int(dpi_arg.split()[1])
    elif '--dpi' in sys.argv:
        i = sys.argv.index('--dpi')
        if i + 1 < len(sys.argv):
            dpi = int(sys.argv[i + 1])

    target = pathlib.Path(args[0]).expanduser()
    if not target.exists():
        print(f'  不存在: {target}')
        return 1
    pdfs = sorted(target.glob('*.pdf')) if target.is_dir() else [target]
    if not pdfs:
        print('  没有 PDF')
        return 1

    outdir = (target if target.is_dir() else target.parent) / 'shots'
    for pdf in pdfs:
        made = convert(pdf, outdir, dpi)
        print(f'=== {pdf.name}  {len(made)} 页 ===')
        best = max(made, key=lambda m: m[1].stat().st_size)
        for i, out, w, h in made:
            kb = out.stat().st_size / 1024
            mark = '  ← 有内容' if out == best[1] else ('' if kb > 60 else '  (空白)')
            print(f'  第{i}页 {w}x{h}  {kb:8.0f}KB  {out.name}{mark}')
    print(f'\n输出目录: {outdir}')
    return 0


if __name__ == '__main__':
    sys.exit(main())

#!/usr/bin/env python3
"""分页溢出「隔离实验」—— 定量定位到底是哪一块放不下。

什么时候用：某一块整组掉到下一页，而且看起来“只差一点点”。**别猜**，跑这个。

用法:
    probe_pagebreak.py <快照.html> [--block .acts] [--page 1440x940]
    probe_pagebreak.py _shots/1_目录总账.html --block .foot

原理：对同一份快照注入**单条** CSS，逐个渲染，记录「页数 + 第 1 页内容最底 y」。

判读规则（输出末尾会自动重复一遍）:
    · 隐藏某块后页数变 1        → 就是那块放不下（不是它前面的内容有问题）
    · 该块 padding 归零后变 1   → 只差几个 pt，从该块的 padding / 内部行高里省
    · 页面加高 100pt 后内容最底只多一点点 → 确认是真溢出，不是分页副作用

关键性质：**`white-space:nowrap` 的块不会被拆分**，放不下就整块搬走 ——
所以「只差 1pt」也会整块跳页，看上去像「突然多出一整页」。此时不要大改，省 3-5pt 即可。

依赖: weasyprint, pymupdf (import fitz)
"""
import argparse
import pathlib
import sys

import fitz
from weasyprint import HTML

PROBE_DIR = pathlib.Path('/tmp/_pagebreak_probe')


def build_cases(block, page_size):
    q = f'{block} ' if block else '.x '   # 无 block 时用不存在的选择器，用例退化成空操作
    return {
        '0_原样':                 '',
        f'1_隐藏{q.strip()}':      f'{q}{{display:none !important}}',
        f'2_{q.strip()}padding0':  f'{q}{{padding:0 !important;margin:0 !important}}',
        f'3_{q.strip()}去nowrap':  f'{q}{{white-space:normal !important}}',
        '4_页面加高100pt':        f'@page{{size:{page_size[0]}px {page_size[1] + 100}px !important}}',
    }


def run(src, cases):
    base = src.read_text(encoding='utf-8')
    PROBE_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    for tag, css in cases.items():
        html = base if not css else base.replace('</head>', f'<style>{css}</style></head>')
        f = PROBE_DIR / f'{tag}.html'
        f.write_text(html, encoding='utf-8')
        pdf = PROBE_DIR / f'{tag}.pdf'
        try:
            HTML(filename=str(f), base_url=str(src.parent)).write_pdf(str(pdf))
            d = fitz.open(str(pdf))
            y1 = max((w[3] for w in d[0].get_text('words')), default=0.0)
            p2 = ''
            if d.page_count > 1:
                p2 = d[1].get_text().strip().replace('\n', ' | ')[:44]
            rows.append((tag, d.page_count, y1, p2))
            d.close()
        except Exception as e:
            rows.append((tag, -1, 0.0, f'{type(e).__name__}: {str(e)[:50]}'))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('snapshot', help='导出的快照 HTML')
    ap.add_argument('--block', default='', help='怀疑放不下的那块的选择器，如 .acts')
    ap.add_argument('--page', default='1440x940', help='目标 CSS px，如 1440x940')
    a = ap.parse_args()

    page = tuple(int(x) for x in a.page.lower().split('x'))
    src = pathlib.Path(a.snapshot)
    if not src.exists():
        print(f"  ❌ 找不到 {src}")
        return 2

    rows = run(src, build_cases(a.block, page))
    page_pt = page[1] * 0.75
    print(f"  {src.name}   页高 {page_pt:.0f}pt")
    print(f"  第1页内容最底离 {page_pt:.0f} 越远 = 有整块被搬到下一页（块不可拆）\n")
    for tag, n, y1, p2 in rows:
        pages = f'{n} 页' if n >= 0 else '❌ 渲染失败'
        print(f"  {tag:24s} {pages:8s} 第1页最底 {y1:6.1f}pt   {p2}")

    print("\n  判读：隐藏某块后页数变 1 → 就是那块放不下；"
          "该块 padding 归零后变 1 → 只差几个 pt。"
          "\n  注意：white-space:nowrap 的块不会被拆分，只差 1pt 也会整块跳页。")
    return 0


if __name__ == '__main__':
    sys.exit(main())

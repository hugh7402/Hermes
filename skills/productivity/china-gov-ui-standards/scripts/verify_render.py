#!/usr/bin/env python3
"""原型交付前量化验收 —— 六道验收里能自动化的那几道。

用法:
    verify_render.py <快照目录或单个.pdf> [--size 1440x940] [--expect expect.json]
    verify_render.py _shots/ --size 1440x940 --expect expect.json

expect.json（可选；不给就跳过关键短语检查）:
    {"1_目录总账": ["数据资源目录台账", "上一页", "共 14 项"],
     "2_目录档案": ["字段清单", "变更沿革"]}

检查项:
    1) 页数 == 1       （>1 = 有内容溢出视口；overflow:hidden 挡不住分页）
    2) 页面尺寸 == 目标 CSS px × 0.75
    3) 文字重叠 == 0   （bbox 相交面积 / 较小者 > 0.30 判重叠）
    4) 关键短语齐全    （给了 --expect 才检查）

退出码: 0 = 全通过 / 1 = 有失败
依赖: pymupdf (import fitz)
"""
import argparse
import glob
import itertools
import json
import os
import sys

import fitz

OVERLAP_RATIO = 0.30   # 相交面积 / 较小者 > 此值 判为重叠
PT_PER_CSSPX = 0.75    # WeasyPrint 用 pt，1 CSS px = 0.75pt


def check_one(pdf_path, size, expect):
    name = os.path.splitext(os.path.basename(pdf_path))[0]
    d = fitz.open(pdf_path)
    pg = d[0]
    fails = []

    # 1) 页数
    if d.page_count != 1:
        fails.append(f"页数={d.page_count}（内容溢出视口）")

    # 2) 尺寸
    exp_w, exp_h = size[0] * PT_PER_CSSPX, size[1] * PT_PER_CSSPX
    if abs(pg.rect.width - exp_w) >= 2 or abs(pg.rect.height - exp_h) >= 2:
        fails.append(f"页面 {pg.rect.width:.0f}×{pg.rect.height:.0f}pt，期望 {exp_w:.0f}×{exp_h:.0f}"
                     f"（若是 595×842 说明没指定 @page，按 A4 重排了）")

    # 3) 文字重叠
    words = pg.get_text('words')
    overlaps = []
    for a, b in itertools.combinations(words, 2):
        ra, rb = fitz.Rect(a[:4]), fitz.Rect(b[:4])
        if not ra.intersects(rb):
            continue
        inter = (ra & rb).get_area()
        smaller = min(ra.get_area(), rb.get_area())
        if smaller > 0 and inter / smaller > OVERLAP_RATIO:
            overlaps.append((a[4], b[4], round(inter / smaller, 2)))
    if overlaps:
        fails.append(f"文字重叠 {len(overlaps)} 处: {overlaps[:4]}")

    # 4) 关键短语
    txt = ''.join(p.get_text() for p in d)
    keys = (expect or {}).get(name, [])
    miss = [k for k in keys if k not in txt]
    if miss:
        fails.append(f"缺短语: {miss}")

    npages = d.page_count
    d.close()

    flag = '✅' if not fails else '❌'
    tail = f"  短语 {len(keys) - len(miss)}/{len(keys)}" if keys else ''
    print(f"  {flag} {name:26s} {npages}页  {len(words):4d}词{tail}")
    for f in fails:
        print(f"       └─ {f}")
    return not fails


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('target', help='快照目录 或 单个 PDF')
    ap.add_argument('--size', default='1440x940', help='目标 CSS px，如 1440x940')
    ap.add_argument('--expect', help='关键短语 JSON 文件')
    a = ap.parse_args()

    size = tuple(int(x) for x in a.size.lower().split('x'))
    expect = json.load(open(a.expect, encoding='utf-8')) if a.expect else None

    if os.path.isdir(a.target):
        pdfs = sorted(glob.glob(os.path.join(a.target, '*.pdf')))
    else:
        pdfs = [a.target]
    if not pdfs:
        print(f"  ⚠️ {a.target} 下没有 PDF —— 先跑渲染脚本把快照转成 PDF")
        return 1

    print(f"验收目标: {a.target}   画布 {size[0]}×{size[1]} CSS px")
    ok = sum(check_one(p, size, expect) for p in pdfs)
    bad = len(pdfs) - ok
    print(f"\n  {ok} 通过 / {bad} 失败")
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SVG→PPTX 导出后的后处理与校验（ppt-master 的 svg_to_pptx 产物专用）

为什么需要这一步 —— svg_to_pptx 的输出有两处必改：

1. 每个 run 的 latin 字体被写成 `Segoe UI`。中文有 eastAsia 兑着看不出问题，
   但数字、英文、页码会挂到 Segoe UI 上；macOS 无此字体 → 掉字/回退。
2. 相关联的形状被压成 <p:grpSp> GROUP。直接迭代 slide.shapes 只能看到顶层，
   组内文字查不到，会误判成“文字丢了”。

另外 SVG 管线不走母版，品牌 logo / 装饰线 / 页码需手动补回（本脚本 --logo）。

用法：
    # 统一字体（推荐同时补 logo）
    python3 pptx_postfix.py deck.pptx --font "Microsoft YaHei" --logo logo.png

    # 只校验，不改
    python3 pptx_postfix.py deck.pptx --verify-only

    # 校验时限定允许色板（交付前卡颜色纪律）
    python3 pptx_postfix.py deck.pptx --verify-only \
        --palette E60012 A0000C F04A55 FBD5D8 FDF3F4 1A1A1A 595959 FFFFFF
"""
import argparse
import collections
import re
import sys
import zipfile

from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches


def walk(shapes, out=None):
    """递归展开所有形状，包括 GROUP 内部。校验文字必须用它，不能只看顶层。"""
    if out is None:
        out = []
    for sh in shapes:
        out.append(sh)
        if sh.shape_type == MSO_SHAPE_TYPE.GROUP:
            walk(sh.shapes, out)
    return out


def iter_runs(prs):
    for sl in prs.slides:
        for sh in walk(sl.shapes):
            if not sh.has_text_frame:
                continue
            for p in sh.text_frame.paragraphs:
                for r in p.runs:
                    if r.text.strip():
                        yield sl, sh, r


def unify_font(prs, font):
    """每个 run 的 latin / ea / cs 全写同一字体；顺序必须 latin → ea → cs。"""
    n = 0
    for _, _, r in iter_runs(prs):
        rPr = r._r.get_or_add_rPr()
        for tag in ('a:latin', 'a:ea', 'a:cs'):
            el = rPr.find(qn(tag))
            if el is None:
                el = rPr.makeelement(qn(tag), {})
                rPr.append(el)
            el.set('typeface', font)
        n += 1
    return n


def add_logo(prs, logo_path, x_px, y_px, w_px, h_px, slide_index=0):
    """补回品牌 logo。SVG 管线丢了母版元素，这一步不能省；并置于最上层。"""
    sl = prs.slides[slide_index]
    pic = sl.shapes.add_picture(
        logo_path,
        Inches(x_px / 96.0), Inches(y_px / 96.0),
        width=Inches(w_px / 96.0), height=Inches(h_px / 96.0),
    )
    sl.shapes._spTree.remove(pic._element)
    sl.shapes._spTree.append(pic._element)
    return pic


def verify(path, palette=None):
    prs = Presentation(path)
    z = zipfile.ZipFile(path)
    ok = True

    print('══ 形状与文本 ══')
    for idx, sl in enumerate(prs.slides, 1):
        SW = Emu(prs.slide_width).inches
        SH = Emu(prs.slide_height).inches
        allsh = walk(sl.shapes)
        top = len(sl.shapes)
        groups = sum(1 for s in allsh if s.shape_type == MSO_SHAPE_TYPE.GROUP)
        pics = sum(1 for s in allsh if s.shape_type == MSO_SHAPE_TYPE.PICTURE)
        textsh = [s for s in allsh if s.has_text_frame and s.text_frame.text.strip()]
        print(f'  第{idx}页 {SW:.2f}×{SH:.2f} | 顶层 {top} | 组 {groups} | 含组共 {len(allsh)}'
              f' | 文本块 {len(textsh)} | 图片 {pics}（品牌 logo 属正常）')

        out = []
        for s in allsh:
            try:
                l, t = Emu(s.left).inches, Emu(s.top).inches
                w, h = Emu(s.width).inches, Emu(s.height).inches
            except TypeError:
                continue
            if l < -0.01 or t < -0.01 or l + w > SW + 0.01 or t + h > SH + 0.01:
                out.append((round(l, 2), round(t, 2), round(l + w, 2), round(t + h, 2)))
        print(f'  越界 {len(out)}' + ('  ✅' if not out else f'  ⚠️ {out[:5]}'))
        ok = ok and not out

    print('\n══ 字体 ══')
    fc = collections.Counter()
    for _, _, r in iter_runs(prs):
        rPr = r._r.find(qn('a:rPr'))
        ea = rPr.find(qn('a:ea')).get('typeface') if (rPr is not None and rPr.find(qn('a:ea')) is not None) else None
        fc[(r.font.name, ea)] += 1
    for k, v in fc.most_common():
        flag = '' if k[0] == k[1] else '  ⚠️ latin/eastAsia 不一致，中文/数字会不同面'
        print(f'  (latin={k[0]}, ea={k[1]}) ×{v}{flag}')
    if 'Segoe UI' in {k[0] for k in fc}:
        print('  ⚠️ 出现 Segoe UI：svg_to_pptx 的默认值，macOS 无此字体，用 --font 统一掉')
        ok = False

    print('\n══ 用色 ══')
    for idx, sl in enumerate(prs.slides, 1):
        xml = z.read(f'ppt/slides/slide{idx}.xml').decode('utf-8')
        cols = collections.Counter(re.findall(r'srgbClr val="([0-9A-Fa-f]{6})"', xml))
        print(f'  第{idx}页 {dict(cols)}')
        if palette:
            allow = {c.upper() for c in palette}
            bad = [c for c in cols if c.upper() not in allow]
            print('  色板外色值：' + ('无 ✅' if not bad else f'{bad} ⚠️'))
            ok = ok and not bad

    print('\n══ 文本全文（含组内）══')
    for idx, sl in enumerate(prs.slides, 1):
        print(f'  ── 第{idx}页 ──')
        for s in walk(sl.shapes):
            if s.has_text_frame and s.text_frame.text.strip():
                print('   ·', s.text_frame.text.replace('\n', ' ')[:80])

    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('pptx')
    ap.add_argument('--font', default=None, help='统一 latin/ea/cs 到这个字体')
    ap.add_argument('--logo', default=None, help='品牌 logo 图片路径（SVG 管线必补）')
    ap.add_argument('--logo-box', nargs=4, type=float, metavar=('X', 'Y', 'W', 'H'),
                    default=[1128, 24, 112, 21], help='logo 位置尺寸，单位 px（1280×720 坐标系）')
    ap.add_argument('--verify-only', action='store_true')
    ap.add_argument('--palette', nargs='*', default=None, help='允许的色值（不带#）')
    a = ap.parse_args()

    if not a.verify_only:
        prs = Presentation(a.pptx)
        if a.font:
            print(f'  ✅ {unify_font(prs, a.font)} 个 run 的 latin/ea/cs 统一为 {a.font}')
        if a.logo:
            add_logo(prs, a.logo, *[int(v) for v in a.logo_box])
            print(f'  ✅ 已补 logo {a.logo} @ {a.logo_box}')
        prs.save(a.pptx)

    ok = verify(a.pptx, a.palette)
    print('\n' + ('✅ 校验通过' if ok else '⚠️ 有问题，见上'))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())

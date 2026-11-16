#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a Chinese (CJK) .docx with correct east-Asian fonts and gov-document defaults.

Why this exists: `docx_create.py` sets only `run.font.name`, which sets the Latin
face. Chinese runs then fall back to the theme font, so a spec asking for 仿宋
opens in Word as 宋体. Every run here writes w:ascii / w:hAnsi / w:eastAsia / w:cs
together, so the requested face actually applies to CJK glyphs.

Usage:
    python cn_docx.py spec.json out.docx

Spec (all keys optional except `blocks`):
{
  "page":   {"margins_mm": {"top":37,"bottom":35,"left":28,"right":26}},   # A4 implied
  "title":  ["第一行标题", "第二行标题"],          # centred, title_font
  "title_font": {"name":"方正小标宋简体","size":22},
  "subtitle": "（说明行，楷体灰字）",
  "footer_page_numbers": true,                     # renders  — PAGE —
  "normal_font": {"name":"仿宋_GB2312","size":16},
  "blocks": [
    {"type":"h1", "text":"第一部分  数据治理"},
    {"type":"h2", "text":"一、总览", "note":"【主要屏 · 370字】"},
    {"type":"p",  "text":"正文段落…"},
    {"type":"p",  "text":"不缩进段落", "indent":false, "font":"楷体_GB2312", "size":12, "color":[96,96,96]},
    {"type":"table", "header":["屏号","原字数"], "rows":[["一","244"]],
     "widths_mm":[60,25], "cell_font":{"name":"仿宋","size":10}, "bold_last_row":true}
  ]
}

Blank lines inside a `p` text split into separate paragraphs (same as the rest).
"""
import json
import sys

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Mm, Pt, RGBColor

FONTS = ('w:ascii', 'w:hAnsi', 'w:eastAsia', 'w:cs')
A4 = (210, 297)


def set_font(run, name, size, bold=False, color=None):
    """Set a run's font on every script slot so CJK glyphs use `name` too."""
    run.font.name = name
    run.font.size = Pt(size)
    run.font.bold = bold
    if color:
        run.font.color.rgb = RGBColor(*color)
    rpr = run._element.get_or_add_rPr()
    rf = rpr.find(qn('w:rFonts'))
    if rf is None:
        rf = OxmlElement('w:rFonts')
        rpr.append(rf)
    for attr in FONTS:
        rf.set(qn(attr), name)


def style_default_font(doc, name, size):
    """Also fix the Normal style, or empty paragraphs still fall back."""
    st = doc.styles['Normal']
    st.font.name = name
    st.font.size = Pt(size)
    rpr = st.element.get_or_add_rPr()
    rf = rpr.find(qn('w:rFonts'))
    if rf is None:
        rf = OxmlElement('w:rFonts')
        rpr.append(rf)
    for attr in FONTS:
        rf.set(qn(attr), name)


def add_field(paragraph, instr, font, size):
    """Insert a Word field (PAGE, NUMPAGES, TOC …) — Word computes it on open."""
    run = paragraph.add_run()
    begin = OxmlElement('w:fldChar')
    begin.set(qn('w:fldCharType'), 'begin')
    instr_el = OxmlElement('w:instrText')
    instr_el.set(qn('xml:space'), 'preserve')
    instr_el.text = instr
    end = OxmlElement('w:fldChar')
    end.set(qn('w:fldCharType'), 'end')
    run._r.append(begin)
    run._r.append(instr_el)
    run._r.append(end)
    set_font(run, font, size)
    return run


def add_para(doc, text, font, size, bold=False, indent=True,
             align=None, line=28, color=None, space_before=0, space_after=0):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_before = Pt(space_before)
    pf.space_after = Pt(space_after)
    if line:
        pf.line_spacing = Pt(line)
    if indent:
        pf.first_line_indent = Pt(size * 2)   # 2 characters at that point size
    if align is not None:
        p.alignment = align
    set_font(p.add_run(text), font, size, bold, color)
    return p


def build(spec, out):
    normal = spec.get('normal_font', {'name': '仿宋_GB2312', 'size': 16})
    doc = Document()

    sec = doc.sections[0]
    sec.page_width, sec.page_height = Mm(A4[0]), Mm(A4[1])
    m = spec.get('page', {}).get('margins_mm', {})
    sec.top_margin = Mm(m.get('top', 37))
    sec.bottom_margin = Mm(m.get('bottom', 35))
    sec.left_margin = Mm(m.get('left', 28))
    sec.right_margin = Mm(m.get('right', 26))
    style_default_font(doc, normal['name'], normal['size'])

    if spec.get('footer_page_numbers', True):
        fp = doc.sections[0].footer.paragraphs[0]
        fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        set_font(fp.add_run('— '), '宋体', 13)
        add_field(fp, ' PAGE ', '宋体', 13)
        set_font(fp.add_run(' —'), '宋体', 13)

    tf = spec.get('title_font', {'name': '方正小标宋简体', 'size': 22})
    titles = spec.get('title') or []
    if isinstance(titles, str):
        titles = [titles]
    for i, t in enumerate(titles):
        add_para(doc, t, tf['name'], tf['size'], indent=False,
                 align=WD_ALIGN_PARAGRAPH.CENTER, line=36,
                 space_after=6 if i == len(titles) - 1 else 0)

    if spec.get('subtitle'):
        add_para(doc, spec['subtitle'], '楷体_GB2312', 12, indent=False,
                 align=WD_ALIGN_PARAGRAPH.CENTER, line=20,
                 color=(0x60, 0x60, 0x60), space_after=14)

    for b in spec.get('blocks', []):
        kind = b.get('type', 'p')

        if kind == 'h1':
            add_para(doc, b['text'], b.get('font', '黑体'), b.get('size', 16),
                     indent=False, line=30, space_after=4)

        elif kind == 'h2':
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(b.get('space_before', 8))
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.line_spacing = Pt(b.get('line', 28))
            set_font(p.add_run(b['text']), b.get('font', '黑体'), b.get('size', 15))
            if b.get('note'):
                set_font(p.add_run('　　' + b['note']), '楷体_GB2312', 10.5,
                         color=(0x88, 0x88, 0x88))

        elif kind == 'p':
            for seg in [s.strip() for s in b['text'].split('\n') if s.strip()]:
                add_para(doc, seg,
                         b.get('font', normal['name']),
                         b.get('size', normal['size']),
                         bold=b.get('bold', False),
                         indent=b.get('indent', True),
                         line=b.get('line', 28),
                         color=tuple(b['color']) if b.get('color') else None)

        elif kind == 'table':
            cf = b.get('cell_font', {'name': '仿宋', 'size': 10})
            header = b.get('header') or []
            rows = b.get('rows') or []
            table = doc.add_table(rows=1, cols=len(header))
            table.style = b.get('style', 'Table Grid')
            for i, h in enumerate(header):
                _cell(table.rows[0].cells[i], h, cf['name'], cf['size'] + .5, True,
                      WD_ALIGN_PARAGRAPH.CENTER, b)
            for ri, row in enumerate(rows):
                cells = table.add_row().cells
                last = ri == len(rows) - 1
                bold = bool(b.get('bold_last_row')) and last
                for ci, val in enumerate(row[:len(header)]):
                    _cell(cells[ci], str(val), cf['name'], cf['size'], bold,
                          None, b, force_center=bold)
            if b.get('widths_mm'):
                for ci, w in enumerate(b['widths_mm']):
                    for row in table.rows:
                        row.cells[ci].width = Mm(w)
        else:
            raise ValueError('unknown block type: %r' % kind)

    doc.save(out)
    return out


def _cell(cell, text, font, size, bold, align, block, force_center=False):
    cell.text = ''
    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(1)
    p.paragraph_format.space_after = Pt(1)
    p.paragraph_format.line_spacing = Pt(14)
    if align is not None:
        p.alignment = align
    elif force_center:
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    color = None
    # per-cell colour: block["cell_colors"][row_index][col_index]
    set_font(p.add_run(text), font, size, bold, color)


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    spec = json.loads(open(sys.argv[1], encoding='utf-8').read())
    out = build(spec, sys.argv[2])
    print(json.dumps({'ok': True, 'output': out}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())

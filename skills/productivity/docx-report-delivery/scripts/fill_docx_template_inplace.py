#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""在用户给的空模板 docx 上就地填充内容，保留模板原有格式。

用法：
    python3 fill_docx_template_inplace.py 模板.docx 输出.docx content.json \
        [--replace "汇报时间：2026年9月=汇报时间：2026年10月"] \
        [--drop-prefix "1-2 个重点产品" --drop-prefix "重点商机 / 项目"] \
        [--ea-font 仿宋] [--size 12] [--line 1.2] [--indent-pt 24]

content.json：{"章节标题原文": ["正文段1", "正文段2", ...], ...}
    键必须与模板里标题段落的 text.strip() **完全相等**；值按顺序插入到该标题之后。

要点（都是坑）：
  * 按标题**倒序**插入，正序会让后面标题的段落对象错位。
  * 深拷贝标题段 -> 删光 run -> add_run(text) -> 重新设字体/字号/行距。
  * 模板自带的填写提示语（"1-2 个重点产品，"之类）必须删掉，否则会进成品。
  * section.*_margin 可能是 None，打印时先判空。
"""
import argparse
import copy
import json
import shutil
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Pt
from docx.text.paragraph import Paragraph


def set_run_font(run, ea_font, size_pt):
    run.font.size = Pt(size_pt)
    run.font.name = 'Times New Roman'
    rpr = run._element.get_or_add_rPr()
    rpr.rFonts.set(qn('w:eastAsia'), ea_font)


def style_body(p, ea_font, size_pt, line, space_pt, indent_pt):
    pf = p.paragraph_format
    pf.alignment = WD_ALIGN_PARAGRAPH.LEFT
    pf.space_before = Pt(space_pt)
    pf.space_after = Pt(space_pt)
    pf.line_spacing = line
    pf.first_line_indent = Pt(indent_pt) if indent_pt else None
    for r in p.runs:
        set_run_font(r, ea_font, size_pt)
    return p


def insert_after(anchor, text, ea_font, size_pt, line, space_pt, indent_pt):
    new_p = copy.deepcopy(anchor._p)
    anchor._p.addnext(new_p)
    p = Paragraph(new_p, anchor._parent)
    for r in list(p.runs):
        r._element.getparent().remove(r._element)
    p.add_run(text)
    return style_body(p, ea_font, size_pt, line, space_pt, indent_pt)


def replace_paragraph_text(p, new_text, ea_font, size_pt):
    """整段替换：保留第一个 run 的格式，清掉其它 run。"""
    if not p.runs:
        p.add_run(new_text)
    else:
        p.runs[0].text = new_text
        for r in p.runs[1:]:
            r.text = ''
    for r in p.runs:
        set_run_font(r, ea_font, size_pt)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('template')
    ap.add_argument('output')
    ap.add_argument('content_json')
    ap.add_argument('--replace', action='append', default=[], metavar='OLD=NEW')
    ap.add_argument('--drop-prefix', action='append', default=[], metavar='PREFIX')
    ap.add_argument('--ea-font', default='仿宋')
    ap.add_argument('--size', type=float, default=12.0)
    ap.add_argument('--line', type=float, default=1.2)
    ap.add_argument('--space-pt', type=float, default=6.0)
    ap.add_argument('--indent-pt', type=float, default=24.0, help='首行缩进磅值，0=不缩进')
    a = ap.parse_args()

    out = Path(a.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(a.template, out)
    doc = Document(str(out))
    content = json.loads(Path(a.content_json).read_text(encoding='utf-8'))

    # 1) 表头等整段替换
    for pair in a.replace:
        old, _, new = pair.partition('=')
        for p in doc.paragraphs:
            if p.text.strip().startswith(old.strip()):
                replace_paragraph_text(p, new, a.ea_font, a.size)
                break

    # 2) 删掉模板自带的填写提示语
    dropped = 0
    for p in list(doc.paragraphs):
        t = p.text.strip()
        if t and any(t.startswith(x) for x in a.drop_prefix):
            p._element.getparent().remove(p._element)
            dropped += 1

    # 3) 按标题倒序插入正文
    targets = [(p, p.text.strip()) for p in doc.paragraphs if p.text.strip() in content]
    missing = [k for k in content if not any(k == kk for _, kk in targets)]
    for anchor, key in reversed(targets):
        cur = anchor
        for line_text in content[key]:
            cur = insert_after(cur, line_text, a.ea_font, a.size, a.line, a.space_pt, a.indent_pt)

    doc.save(str(out))

    # 4) 回读校验
    chk = Document(str(out))
    print(json.dumps({
        'output': str(out),
        'paragraphs': len(chk.paragraphs),
        'hints_dropped': dropped,
        'headings_missing': missing,
    }, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

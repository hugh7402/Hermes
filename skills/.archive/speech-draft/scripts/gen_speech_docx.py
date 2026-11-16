# -*- coding: utf-8 -*-
"""公文格式发言稿生成器（含字数 + 预计时长统计）

用法：
    1. 改下面 TITLE / SUB / DATE / BODY / OUT_NAME 变量
    2. cd /opt/data/.tmp_tests && export PATH=/opt/data/.venv/bin:$PATH && python3 gen_speech_docx.py
    3. 输出 docx 到 /opt/data/OutPut Box/<子目录>/，并打印字数与预计朗读时长

格式：方正小标宋 22pt 标题 / 楷体 15pt 副标题 / 仿宋 16pt 正文（首行缩进 2 字符、行距 1.5）/ A4 公文页边距
字数基准：中文口播 ≈ 230 字/分钟（慢 200 / 快 260）
"""
import os

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

# ============ 只改这一段 ============
TITLE = '在×××会议上的发言'          # 两行用 \n 拆行
SUB = '××单位'
DATE = '2026年×月×日'
OUT_DIR = '/opt/data/OutPut Box/发言稿'
OUT_NAME = '发言稿.docx'

# kind: '称呼' | '小标题' | '正文'
BODY = [
    ('称呼', '尊敬的各位领导、各位同仁：'),
    ('正文', '大家上午好！下面我代表××单位，围绕收获体会、取得成果、下一步思路举措作简要汇报。'),

    ('小标题', '一、关于收获体会'),
    ('正文', '（写"看到什么 → 与本单位的关联 → 与上位规划的衔接"，不要写"收获很大"这类套话）'),

    ('小标题', '二、关于取得成果'),
    ('正文', '（写具体做法 + 一手数字：系统数量、设备构成、人员配置、接待量、达成意向数；缺数据用 【待填】 占位，不要编）'),

    ('小标题', '三、关于下一步工作的思路和举措'),
    ('正文', '一是××××。'),
    ('正文', '二是××××。'),
    ('正文', '三是××××。'),

    ('正文', '最后表个态。××单位将一如既往……汇报完毕，谢谢大家！'),
]
# ==================================

CPM = 230  # 中文字/分钟


def set_font(run, name='仿宋', size=16, bold=False):
    run.font.name = name
    run.font.size = Pt(size)
    run.font.bold = bold
    run._element.rPr.rFonts.set(qn('w:eastAsia'), name)


def build():
    doc = Document()

    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21), Cm(29.7)
    sec.top_margin, sec.bottom_margin = Cm(3.7), Cm(3.5)
    sec.left_margin, sec.right_margin = Cm(2.8), Cm(2.6)

    style = doc.styles['Normal']
    style.font.name = '仿宋'
    style.font.size = Pt(16)
    style._element.rPr.rFonts.set(qn('w:eastAsia'), '仿宋')

    for line in TITLE.split('\n'):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(6)
        p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
        set_font(p.add_run(line), '方正小标宋简体', 22, True)

    for txt in (SUB, DATE):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(4)
        set_font(p.add_run(txt), '楷体', 15, False)

    doc.add_paragraph()

    for kind, text in BODY:
        p = doc.add_paragraph()
        pf = p.paragraph_format
        pf.line_spacing = 1.5
        pf.space_after = Pt(0)
        if kind == '称呼':
            pf.first_line_indent = 0
            set_font(p.add_run(text), '仿宋', 16, False)
        elif kind == '小标题':
            pf.first_line_indent = Pt(32)
            pf.space_before = Pt(6)
            set_font(p.add_run(text), '黑体', 16, False)
        else:
            pf.first_line_indent = Pt(32)
            set_font(p.add_run(text), '仿宋', 16, False)

    os.makedirs(OUT_DIR, exist_ok=True)
    out = os.path.join(OUT_DIR, OUT_NAME)
    doc.save(out)
    return out


def stats():
    """总字数 / 分段字数（【待填】 不计入）"""
    total = 0
    sections = {}
    current = '开场'
    for kind, text in BODY:
        n = len(text.replace('【待填】', ''))
        if kind == '小标题':
            current = text.strip()
            sections[current] = 0
        else:
            sections[current] = sections.get(current, 0) + n
        total += n
    return total, sections


if __name__ == '__main__':
    out = build()
    total, sections = stats()
    print('已生成:', out)
    print('正文字数（不含【待填】）:', total)
    print('预计朗读时长: %.1f 分钟（按 %d 字/分钟）' % (total / CPM, CPM))
    print('--- 分段字数 ---')
    for k, v in sections.items():
        print('  %s: %d 字 (~%.1f 分钟)' % (k, v, v / CPM))
    if total > 1200:
        print('⚠️ 超过 5 分钟稿的建议上限（1200 字），按段落比例精简')

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""演示脚本生成器（系统演示口播稿）：docx + md，自带字数与时长核算

用法：改下面 RATE / CAP / INTRO / STEPS / CLOSING / OUT 六个地方，直接跑：
    cd /opt/data/.tmp_tests && export PATH=/opt/data/.venv/bin:$PATH && python3 <裸名>.py

设计要点（踩过的坑，别改掉）：
  · RATE 用**用户给的**语速（用户说 250 就 250，没说按 230）
  · CAP = 时限(分) × RATE，写满到上限会挤掉操作停顿 → 正文留 3–8% 余量
  · 每步 talk 就是那一节的字数预算，写完看打印的逐段字数再补/删，别凭语感
  · assert 在最后，超限直接失败（提示删内容，不是改语速）
"""
import pathlib
import re

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor

RATE = 250          # 字/分钟（以用户给的为准）
MINUTES = 10        # 时限
CAP = RATE * MINUTES  # 字数上限
OUT = pathlib.Path('/opt/data/designs/<项目>/演示脚本')

INTRO = """开场：一句点明演示范围、按什么条款顺序走、用哪套演示数据集。"""

STEPS = [
    dict(title="<条款号>-1　<步骤名>",
         screen="【<系统>】<模块 ＞ 页面>　路由 /xxxx",
         ops=["以「<角色>」进入…", "点击【<按钮>】…", "核对…状态为「…」"],
         talk="""本步逐字口播稿。术语、按钮名、数字必须能在真实界面上找到。"""),
]

CLOSING = """收尾：按条款顺序逐条复述演示了什么 + 数据来源说明 + 致谢。"""


def cn(s):
    return len(re.findall(r'[\u4e00-\u9fff]', s))


def main():
    rows = [('开场', '首页', cn(INTRO))]
    for s in STEPS:
        rows.append((s['title'].split('\u3000')[0], s['screen'].split('\u3000')[0], cn(s['talk'])))
    rows.append(('收尾', '末屏', cn(CLOSING)))
    total = sum(r[2] for r in rows)

    md = ['# <系统名> · 演示脚本', '',
          f'> 顺序：严格按需求条目逐步走｜语速 {RATE} 字/分钟（口播共 {total} 字 ≈ {total/RATE:.1f} 分钟）', '',
          '| 环节 | 屏幕 | 口播字数 | 时长 |', '|---|---|---|---|']
    for name, scr, n in rows:
        md.append(f'| {name} | {scr} | {n} | {n/RATE*60:.0f} 秒 |')
    md += [f'| **合计** | — | **{total}** | **{total/RATE:.1f} 分钟** |', '', '## 开场', '', INTRO, '']
    for s in STEPS:
        md += [f"## {s['title']}", '', f"**屏幕**：{s['screen']}", '', '**关键操作**：']
        md += [f'{i}) {o}' for i, o in enumerate(s['ops'], 1)]
        md += ['', '**口播稿**：', '', s['talk'], '']
    md += ['## 收尾', '', CLOSING, '']
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / '演示脚本.md').write_text('\n'.join(md), encoding='utf-8')

    doc = Document()
    st = doc.styles['Normal']
    st.font.name = '宋体'
    st.font.size = Pt(11)
    st.element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')

    def para(text, size=11, bold=False, font='宋体', align=None, color=None):
        p = doc.add_paragraph()
        r = p.add_run(text)
        r.bold = bold
        r.font.size = Pt(size)
        r.font.name = font
        r.element.rPr.rFonts.set(qn('w:eastAsia'), font)
        if color:
            r.font.color.rgb = RGBColor(*color)
        if align:
            p.alignment = align

    para('<系统名> · 演示脚本', 18, True, '黑体', WD_ALIGN_PARAGRAPH.CENTER)
    para(f'{MINUTES} 分钟版｜语速 {RATE} 字/分钟｜口播共 {total} 字 ≈ {total/RATE:.1f} 分钟', 10,
         align=WD_ALIGN_PARAGRAPH.CENTER, color=(0xC0, 0x00, 0x00))
    doc.add_paragraph()
    para('一、时长核算表', 13, True, '黑体')
    t = doc.add_table(rows=1, cols=4)
    t.style = 'Table Grid'
    for i, h in enumerate(['环节', '屏幕 / 系统', '口播字数', '时长']):
        t.rows[0].cells[i].text = h
    for name, scr, n in rows + [('合计', '—', total)]:
        cells = t.add_row().cells
        for i, v in enumerate([name, scr, str(n), f'{n/RATE*60:.0f} 秒']):
            cells[i].text = v
    doc.add_paragraph()
    para('二、开场', 13, True, '黑体')
    para(INTRO)
    doc.add_paragraph()
    para('三、演示步骤', 13, True, '黑体')
    for s in STEPS:
        para(s['title'], 12, True, '黑体')
        para('屏幕：' + str(s['screen']), 10, True)
        para('关键操作：', 10, True)
        for i, o in enumerate(s['ops'], 1):
            para(f'{i}) {o}', 10)
        para('口播稿：', 10, True)
        para(str(s['talk']))
        doc.add_paragraph()
    para('四、收尾', 13, True, '黑体')
    para(CLOSING)
    doc.save(OUT / '演示脚本.docx')

    print('  ── 口播字数核算 ──')
    for name, scr, n in rows:
        print(f'    {name:<10} {n:>5} 字  ≈ {n/RATE*60:>3.0f} 秒')
    print(f'    {"合计":<10} {total:>5} 字  ≈ {total/RATE:.1f} 分钟（上限 {CAP} 字 / {MINUTES} 分钟）')
    assert total <= CAP, f'超时：{total} 字 > {CAP} 字，删内容（不要改语速）'
    print(f'  ✅ 未超上限（余量 {CAP-total} 字，留给操作停顿）')


if __name__ == '__main__':
    main()

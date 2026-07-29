#!/usr/bin/env python3
"""
陕西智慧民政项目日报生成脚本
用法：python3 generate_report.py <xlsx文件路径>
输出：/opt/data/OutPut Box/陕西智慧民政项目日报-<日期>.docx
依赖：uv pip install python-docx（已安装于 /opt/data/.venv）
"""
import sys, os, re, zipfile, xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from collections import defaultdict

# ══════ 依赖检查 ══════
try:
    from docx import Document
    from docx.shared import Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.oxml.ns import qn
except ImportError:
    print("❌ 缺少 python-docx，请执行: uv pip install python-docx")
    sys.exit(1)

# ══════ 参数 ══════
if len(sys.argv) < 2:
    print("用法: python3 generate_report.py <xlsx文件路径>")
    sys.exit(1)

xlsx_path = sys.argv[1]

# 从文件名提取日期
m = re.search(r'双周任务和问题清单-(\d{8})', os.path.basename(xlsx_path))
if not m:
    print("❌ 文件名中未找到日期，请确认文件名包含'双周任务和问题清单-YYYYMMDD'")
    sys.exit(1)
date_str = m.group(1)
report_date = datetime.strptime(date_str, '%Y%m%d')

print(f"📅 报告日期: {date_str}")
print(f"📂 源文件: {xlsx_path}")

# ══════ Excel解析 ══════
def xl_to_date(s):
    if not s or not s.strip(): return None
    try:
        d = float(s)
        if d < 1: return None
        return datetime(1899, 12, 30) + timedelta(days=d)
    except: return None

with zipfile.ZipFile(xlsx_path) as z:
    ns = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    ss = ET.fromstring(z.read('xl/sharedStrings.xml'))
    ss_list = []
    for si in ss.findall('.//s:si', ns):
        texts = [t.text or '' for t in si.iter('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t')]
        ss_list.append(''.join(texts))

    def cv(c):
        v = c.find('s:v', ns); t = c.get('t', '')
        if v is not None and v.text:
            if t == 's': return ss_list[int(v.text)] if int(v.text) < len(ss_list) else v.text
            return v.text
        return ''

    # ── 读取Sheet2: 权威负责人映射 ──
    person_map = {}
    try:
        root2 = ET.fromstring(z.read('xl/worksheets/sheet2.xml'))
        for row in root2.findall('.//s:row', ns):
            cells = row.findall('s:c', ns); cm = {}
            for c in cells:
                cl = ''.join(filter(str.isalpha, c.get('r', ''))); cm[cl] = cv(c)
            sys_n = cm.get('A', '').replace('\n', ' ').strip()
            prs = cm.get('B', '').strip()
            if sys_n and prs:
                person_map[sys_n] = prs
    except KeyError:
        pass  # Sheet2不存在时用Sheet1

    # ── 读取Sheet1: 双周任务清单 ──
    root1 = ET.fromstring(z.read('xl/worksheets/sheet1.xml'))
    rows_data = root1.findall('.//s:row', ns)

    status_count = {}
    person_tasks = defaultdict(lambda: defaultdict(lambda: {'total': 0, '已完成': 0, '已延期': 0, '未开始': 0, '进行中': 0, '延期风险': 0}))
    delay_issues = []
    risk_issues = []

    for r in rows_data[1:]:
        cells = r.findall('s:c', ns); cm = {}
        for c in cells:
            cl = ''.join(filter(str.isalpha, c.get('r', ''))); cm[cl] = cv(c)

        sys_name = cm.get('D', '').replace('\n', ' ').strip()
        if not sys_name:
            continue

        status = cm.get('K', '').strip()
        date_serial = cm.get('J', '').strip()

        # ❗ 问题描述: 延期/风险任务只从L列("现存问题")读取
        problem = cm.get('L', '').strip()

        # 负责人: Sheet2映射优先, 再Sheet1 I列
        person_raw = cm.get('I', '').strip()
        owner = person_map.get(sys_name, person_raw) if person_raw else '未指定'

        # 曾祥发/高凯悦拆分
        if '、' in owner:
            parts = [p.strip() for p in owner.split('、')]
            if '曾祥发' in parts and '高凯悦' in parts:
                if '公共支撑' in sys_name:
                    owner = '曾祥发'
                elif '民政大数据' in sys_name:
                    owner = '高凯悦'
                else:
                    owner = parts[0]
            else:
                owner = parts[0]

        task_date = xl_to_date(date_serial)
        if not task_date or task_date > report_date:
            continue

        s = status if status else '未填写'
        status_count[s] = status_count.get(s, 0) + 1

        person_tasks[owner][sys_name]['total'] += 1
        if s in person_tasks[owner][sys_name]:
            person_tasks[owner][sys_name][s] += 1

        if s == '已延期':
            delay_issues.append({'system': sys_name, 'person': owner, 'issues': problem})
        elif s == '延期风险':
            risk_issues.append({'system': sys_name, 'person': owner, 'issues': problem})

    person_delay = defaultdict(list)
    for it in delay_issues: person_delay[it['person']].append(it)
    person_risk = defaultdict(list)
    for it in risk_issues: person_risk[it['person']].append(it)

total = sum(v['total'] for sd in person_tasks.values() for v in sd.values())
done = status_count.get('已完成', 0); delay = status_count.get('已延期', 0)
nstart = status_count.get('未开始', 0); ip = status_count.get('进行中', 0); risk = status_count.get('延期风险', 0)

# 负责人排序
person_order = ['侯帅帅', '帅航', '闫帅', '陈彬', '王紫薇', '曾祥发', '杜纯', '李思萌', '高凯悦', '侯涛', '王雨阳']
person_order = [p for p in person_order if p in person_tasks]
person_order += [p for p in person_tasks if p not in person_order]

person_systems_list = []
for p in person_order:
    systems = []
    for sn, v in sorted(person_tasks[p].items(), key=lambda x: -x[1]['total']):
        systems.append({
            'name': sn, 'total': v['total'], 'done': v['已完成'],
            'delay': v['已延期'], 'not_start': v['未开始'], 'in_prog': v['进行中'], 'risk': v['延期风险'],
        })
    person_systems_list.append((p, systems))

# ══════ 生成Word文档 ══════
doc = Document(); s = doc.styles['Normal']
s.font.name = 'Microsoft YaHei'; s.font.size = Pt(10)
s.element.rPr.rFonts.set(qn('w:eastAsia'), 'Microsoft YaHei')

def sc(cell, text, bold=False, align=None, size=None):
    cell.text = ''; p = cell.paragraphs[0]
    if align: p.alignment = align
    r = p.add_run(str(text))
    if bold: r.bold = True
    if size: r.font.size = Pt(size)

# 标题
doc.add_heading('陕西智慧民政项目日报', level=0).alignment = WD_ALIGN_PARAGRAPH.CENTER
p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run(f'日期：{report_date.strftime("%Y年%m月%d日")}    参会人员：邵雷、侯涛、帅航、王紫薇、李思萌、闫帅、王雨阳')
r.font.size = Pt(10); r.font.color.rgb = RGBColor(80, 80, 80)
doc.add_paragraph()

# 一、总体情况
doc.add_heading('一、总体情况', level=1)
p = doc.add_paragraph()
p.add_run(f'截至今日，双周任务清单中应于{report_date.strftime("%Y年%m月%d日")}前完成的任务共 ')
r = p.add_run(f'{total} 项'); r.bold = True; p.add_run('，分布如下：')

t = doc.add_table(rows=1, cols=3); t.style = 'Light Grid Accent 1'; t.alignment = WD_TABLE_ALIGNMENT.CENTER
for i, h in enumerate(['状态', '数量', '占比']): sc(t.rows[0].cells[i], h, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
items = [('✅ 已完成', done), ('🔄 进行中', ip), ('❌ 未开始', nstart), ('🔴 已延期', delay)]
if risk: items.append(('⚠️ 延期风险', risk))
for label, n in items:
    row = t.add_row().cells; sc(row[0], label); sc(row[1], str(n), align=WD_ALIGN_PARAGRAPH.CENTER); sc(row[2], f'{round(n/total*100)}%', align=WD_ALIGN_PARAGRAPH.CENTER)

# 二、分项情况
doc.add_heading('二、分项情况', level=1)
HEADERS = ['系统', '总数', '已完成', '已延期', '未开始', '进行中', '延期风险', '完成率']

for p_name, systems in person_systems_list:
    p_total = sum(s['total'] for s in systems); p_done = sum(s['done'] for s in systems)
    p_delay = sum(s['delay'] for s in systems); p_ns = sum(s['not_start'] for s in systems)
    p_ip = sum(s['in_prog'] for s in systems); p_risk = sum(s['risk'] for s in systems)
    p_rate = f'{round(p_done/p_total*100)}%' if p_total > 0 else '0%'

    doc.add_heading(f'🔵 {p_name}（{len(systems)}个系统，共 {p_total} 项任务）', level=2)

    t = doc.add_table(rows=2+len(systems), cols=8); t.style = 'Light Grid Accent 1'; t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(HEADERS): sc(t.rows[0].cells[i], h, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, size=9)
    for idx, s in enumerate(systems):
        row = t.rows[1+idx].cells; sr = f'{round(s["done"]/s["total"]*100)}%' if s['total'] > 0 else '0%'
        sc(row[0], s['name'], size=9); sc(row[1], str(s['total']), align=WD_ALIGN_PARAGRAPH.CENTER, size=9)
        sc(row[2], str(s['done']), align=WD_ALIGN_PARAGRAPH.CENTER, size=9)
        sc(row[3], str(s['delay']), align=WD_ALIGN_PARAGRAPH.CENTER, size=9)
        sc(row[4], str(s['not_start']), align=WD_ALIGN_PARAGRAPH.CENTER, size=9)
        sc(row[5], str(s['in_prog']), align=WD_ALIGN_PARAGRAPH.CENTER, size=9)
        sc(row[6], str(s['risk']), align=WD_ALIGN_PARAGRAPH.CENTER, size=9)
        sc(row[7], sr, align=WD_ALIGN_PARAGRAPH.CENTER, size=9)

    sr = t.rows[-1].cells; sc(sr[0], '小计', bold=True, size=9)
    for ci, val in enumerate([p_total, p_done, p_delay, p_ns, p_ip, p_risk, p_rate], 1):
        sc(sr[ci], str(val), bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, size=9)
    for cell in t.rows[-1].cells:
        shd = cell._tc.get_or_add_tcPr()
        el = shd.makeelement(qn('w:shd'), {qn('w:val'): 'clear', qn('w:fill'): 'DCE6F1', qn('w:color'): 'auto'})
        shd.append(el)

    # 存在问题
    p_delay_items = person_delay.get(p_name, [])
    p_risk_items = person_risk.get(p_name, [])
    if p_delay_items or p_risk_items:
        p = doc.add_paragraph(); r = p.add_run('存在问题：'); r.bold = True; r.font.size = Pt(9); r.font.color.rgb = RGBColor(200, 0, 0)
        for item in p_delay_items:
            txt = item['issues'].strip() if item['issues'] else ''
            if txt:
                doc.add_paragraph(f'  🔴 {item["system"]}：{txt}', style='List Bullet')
        for item in p_risk_items:
            txt = item['issues'].strip() if item['issues'] else ''
            if txt:
                doc.add_paragraph(f'  ⚠️ {item["system"]}：{txt}', style='List Bullet')
    doc.add_paragraph()

# 保存
out_dir = '/opt/data/OutPut Box'
os.makedirs(out_dir, exist_ok=True)
out_path = f'{out_dir}/陕西智慧民政项目日报-{date_str}.docx'
doc.save(out_path)
print(f'\n✅ 日报已生成: {out_path}')
print(f'   {os.path.getsize(out_path)/1024:.1f} KB')
print(f'   {total}项任务, {len(person_systems_list)}位负责人')
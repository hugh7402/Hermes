#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成《政务数据目录编目模板》.xlsx —— 字段直接取自原型 form_spec，保证与原型一致。
   工作表1 = 政务数据目录编目模板（一行一条目录，含 6 个属性组全部要素）
   工作表2 = 数据项（按目录名称挂接）
"""
import json
import pathlib
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

ROOT = pathlib.Path('/opt/data/designs/drs-demo')
OUT = ROOT / '交付' / '政务数据目录编目模板.xlsx'

spec = json.load(open(ROOT / 'data' / 'form_spec.json', encoding='utf-8'))
groups = [g for g in spec if not g.get('isTable')]
fields = [(g.get('name', ''), f) for g in groups for f in g['fields']]
print(f'要素字段：{len(fields)} 个 · {len(groups)} 个属性组')

# ── 6 条样例目录（与演示数据同源）───────────────────────────────
SAMPLES = [
    ('四川省自然人基本登记信息', '四川省公安厅', '四川省人口基础信息库', '民生保障'),
    ('四川省自然人身份证件信息', '四川省公安厅', '四川省人口基础信息库', '民生保障'),
    ('四川省出生医学证明信息', '四川省卫生健康委员会', '妇幼健康信息系统', '民生保障'),
    ('四川省自然人生理体征信息', '四川省卫生健康委员会', '居民健康档案系统', '医疗卫生'),
    ('四川省死亡注销户籍信息', '四川省公安厅', '四川省人口基础信息库', '民生保障'),
    ('四川省死亡医学证明信息', '四川省卫生健康委员会', '死亡医学证明管理系统', '医疗卫生'),
]

# 关键字段的样例取值（按标签匹配，避免依赖 idx 顺序）
KEY = {
    '数据目录名称': lambda i: SAMPLES[i][0],
    '数据提供单位': lambda i: SAMPLES[i][1],
    '数据来源系统': lambda i: SAMPLES[i][2],
    '数据所属领域': lambda i: SAMPLES[i][3],
    '数据摘要': lambda i: f"{SAMPLES[i][0]}的要素信息，用于支撑政务数据共享与业务协同。",
    '数据目录编码': lambda i: '',
    '目录来源': lambda i: '手工新增',
    '数据来源系统所属分类': lambda i: '国直' if '人口基础信息库' in SAMPLES[i][2] else '省直',
    '数据所在层级': lambda i: '省级',
    '数据存储方式': lambda i: '数据库',
    '存储方式格式类型': lambda i: 'mysql',
    '数据加工程度': lambda i: '融合数据',
    '数据更新频率': lambda i: '每日',
    '数据更新频率说明': lambda i: '每天 2:00 更新前一天数据',
    '是否电子证照': lambda i: '否',
    '是否允许回流': lambda i: '是',
    '回流切分字段': lambda i: '户籍地省市县代码',
    '共享属性': lambda i: '有条件共享',
    '共享方式': lambda i: '依申请共享',
    '共享频率': lambda i: '实时',
    '开放属性': lambda i: '有条件开放',
    '开放方式': lambda i: '依申请开放',
    '是否发布': lambda i: '是',
    '不予发布原因': lambda i: '',
    '事项名称': lambda i: '自然人身份信息核验',
    '事项编码': lambda i: '510000000001',
}


def value_for(label, i, f):
    if label in KEY:
        return KEY[label](i)
    vals = [v for v in (f.get('values') or []) if str(v).strip()]
    if vals:
        return vals[0]
    return ''


wb = Workbook()

# ══ 工作表 1：编目模板 ══
ws = wb.active
ws.title = '政务数据目录编目模板'
THIN = Side(style='thin', color='B7C7DA')
BD = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
H1 = PatternFill('solid', fgColor='D6E4F5')   # 属性组行
H2 = PatternFill('solid', fgColor='EAF1FA')   # 字段名行
HINT = PatternFill('solid', fgColor='FFF8E6')  # 填写说明行（示例）

ws.cell(1, 1, '政务数据目录编目模板').font = Font(bold=True, size=14, color='015293')
ws.cell(2, 1, '填写说明：① 一行填写一条数据目录；② 带 * 为必填项，带 ◐ 为条件必填项；'
              '③ 数据项请在「数据项」工作表中按目录名称填写，系统导入时自动挂接。').font = Font(size=10, color='B26A00')

# 属性组行（第 4 行）+ 字段名行（第 5 行）
r_grp, r_fld = 4, 5
col = 1
for g in groups:
    gname = g.get('name', '')
    start = col
    for f in g['fields']:
        MARK = '*' if f.get('required') == 'req' else ('◐' if f.get('required') == 'cond' else '')
        c = ws.cell(r_fld, col, MARK + str(f['label']))
        c.font = Font(bold=True, size=10, color='015293')
        c.fill = H2
        c.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        c.border = BD
        ws.column_dimensions[get_column_letter(col)].width = max(11, min(22, len(str(f['label'])) * 2.1))
        col += 1
    cg = ws.cell(r_grp, start, gname)
    cg.font = Font(bold=True, size=11, color='FFFFFF')
    cg.fill = PatternFill('solid', fgColor='4E8FDE')
    cg.alignment = Alignment(horizontal='center', vertical='center')
    if col - 1 > start:
        ws.merge_cells(start_row=r_grp, start_column=start, end_row=r_grp, end_column=col - 1)
    for cc in range(start, col):
        ws.cell(r_grp, cc).border = BD
ws.row_dimensions[r_fld].height = 34

# 样例数据行
for i in range(len(SAMPLES)):
    col = 1
    for g in groups:
        for f in g['fields']:
            v = value_for(str(f['label']), i, f)
            c = ws.cell(r_fld + 1 + i, col, v)
            c.font = Font(size=10)
            c.border = BD
            col += 1
last_data_row = r_fld + len(SAMPLES)
for i in range(len(SAMPLES)):
    ws.cell(r_fld + 1 + i, 1).fill = HINT
ws.freeze_panes = ws.cell(r_fld + 1, 3)

# ══ 工作表 2：数据项 ══
ws2 = wb.create_sheet('数据项')
ITEM_COLS = ['数据目录名称', '数据项中文名称', '数据项英文名称', '数据类型', '长度',
             '是否主键', '是否必填', '共享属性', '共享条件', '开放属性', '开放条件', '数据项描述']
for j, t in enumerate(ITEM_COLS, 1):
    c = ws2.cell(1, j, t)
    c.font = Font(bold=True, size=10, color='FFFFFF')
    c.fill = PatternFill('solid', fgColor='4E8FDE')
    c.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    c.border = BD
    ws2.column_dimensions[get_column_letter(j)].width = max(12, len(t) * 2.2)

# 取原型里现成的自然人 15 项数据项作为样例，挂到第 1 条目录上
_ds = json.load(open(ROOT / 'data' / 'demo_dataset.json', encoding='utf-8'))
first_items = (_ds.get('catalog') or {}).get('items') or []
if not first_items:
    first_items = [{'cn': '自然人唯一标识', 'en': 'person_uid', 'type': 'varchar', 'len': '64',
                    'pk': '是', 'req': '是', 'desc': '自然人唯一标识'}]

for k, it in enumerate(first_items):
    row = [SAMPLES[0][0], it.get('cn', ''), it.get('en', ''), it.get('type', 'varchar'),
           it.get('len', ''), it.get('pk', '否'), it.get('req', '否'),
           it.get('share', '有条件共享'), it.get('share_cond', '依申请共享'),
           it.get('open', '有条件开放'), it.get('open_cond', '依申请开放'),
           it.get('desc', '')]
    for j, v in enumerate(row, 1):
        c = ws2.cell(2 + k, j, v)
        c.font = Font(size=10)
        c.border = BD
ws2.freeze_panes = 'A2'

OUT.parent.mkdir(parents=True, exist_ok=True)
wb.save(OUT)
print(f'✅ 已生成：{OUT}')
print(f'   工作表1「{ws.title}」：{len(fields)} 要素列 × {len(SAMPLES)} 条样例目录')
print(f'   工作表2「数据项」：{len(first_items)} 行（挂接「{SAMPLES[0][0]}」）')
print(f'   大小 {OUT.stat().st_size / 1024:.1f} KB')

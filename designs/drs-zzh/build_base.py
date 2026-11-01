#!/usr/bin/env python3
"""生成「四川省数字政府项目作战图」数据底盘 Excel。

数据来源（三份输入）：
1. 时间计划里程碑：项目作战图-20261024.xlsx（39 项任务 + 周粒度甘特，2026-10-26 ~ 2027-05-31）
2. 验收成效指标：验收成效指标1101.xlsx（运营 62 条 + 平台建设 64 条）
3. 人员构成：组织架构图（领导组 / PMO / 基础设施 22 人 / 项目实施 203 人）
"""
import json
import pathlib
from datetime import date, timedelta

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

SRC_ZZT = '/opt/data/cache/documents/native-inputs/b4e2655aac7ca6a1f0d214122cfa13f354736413af1eb84b29b4098e34f2d83c/doc_96630c3ac184_四川省一体化数据资源管理系统-项目作战图-20261024(1).xlsx'
SRC_ZB = '/opt/data/cache/documents/native-inputs/4e9df6514a731cd1e66dbcca9a4ecb44161d2343d5612dee246dbb14b23c40c1/doc_9782bfeb1898_验收成效指标1101.xlsx'
OUT = pathlib.Path('/opt/data/designs/drs-zzh/作战图数据底盘.xlsx')

HEAD_FILL = PatternFill('solid', fgColor='1F4E79')
HEAD_FONT = Font(color='FFFFFF', bold=True, size=10)
SUB_FILL = PatternFill('solid', fgColor='DDEBF7')
THIN = Side(style='thin', color='BFBFBF')
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
TODO = '【待填】'

# 任务号 -> (责任组, 责任人, 执行成员)
DUTY = {
    1: ('综合保障', '张科', '杨俊梅、何茜茜'),
    2: ('PMO办公室', '康晓宇', '张谊、徐鹏、朱宇、成勇、钟嘉'),
    3: ('PMO办公室', '康晓宇', TODO),
    4: ('架构组', '陈俊雄', '康晓宇（邵雷）、数重 1 人、川数 姚兴龙'),
    5: ('架构组', '陈俊雄', '康晓宇（邵雷）、数重 1 人'),
    6: ('主体平台组', '易志伟', '联通 张权、川数 韩弋林、浪潮 18 人、数重+阿里 43 人'),
    7: ('应用组', '张权', '川数 1 人、国脉 6 人、中智软件 4 人、足迹 6 人、待定 12 人'),
    8: ('主体平台组', '易志伟', '应用组 张权'),
    9: ('数据组', '杨金伟', '联通 靳爱辉、川数 李倩、数重 9 人、联通 15 人'),
    10: ('数据组', '杨金伟', '联通 靳爱辉、浪潮 4 人、高德 3 人'),
    11: ('数据组', '杨金伟', '数重 9 人、川数 6 人'),
    12: ('数据组', '杨金伟', '三合力通 4 人、映潮 2 人'),
    13: ('数据组', '杨金伟', '测绘+超图 2 人、中智软件 2 人'),
    14: ('数据组', '杨金伟', '数重 9 人、川数 6 人'),
    15: ('数据组', '杨金伟', '数重 9 人、年化 8 人'),
    16: ('数据组', '杨金伟', '联通 15 人、川数 6 人'),
    17: ('数据组', '杨金伟', '国脉 2 人、乐云 2 人'),
    18: ('数据组', '杨金伟', '川数 6 人'),
    19: ('数据组', '杨金伟', '川数 6 人、联通 15 人'),
    20: ('数据组', '杨金伟', '数重 9 人、乐云 2 人'),
    21: ('数据组', '杨金伟', '联通 15 人、中智软件 2 人'),
    22: ('数据组', '杨金伟', '测绘+超图 2 人、高德 3 人'),
    23: ('数据组', '杨金伟', '数重 9 人、年化 8 人'),
    24: ('安全组', '阿里（XXX）', '安恒 4 人、川数 1 人'),
    25: ('标准组', '纪加兴', '联通 1 人、川数 1 人、国脉 1 人'),
    26: ('数据组', '杨金伟', '高德 3 人、映潮 2 人'),
    27: ('云技术组', '夏枭', '联通 4 人（含复用 1 人、新招 3 人）'),
    28: ('云交付组', '曹高山', '联通 3 人、新招 3 人、阿里 2 人'),
    29: ('云交付组', '曹高山', '联通 3 人、阿里 2 人'),
    30: ('云交付组', '曹高山', '联通 3 人、新招 3 人、阿里 2 人'),
    31: ('云交付组', '曹高山', '联通、阿里、川数'),
    32: ('云交付组', '曹高山', '联通、阿里、川数'),
    33: ('PMO办公室', '康晓宇', '架构组、各建设组'),
    34: ('安全组', '阿里（XXX）', '安恒 4 人、川数 1 人'),
    35: ('主体平台组', '易志伟', '各建设组'),
    36: ('PMO办公室', '康晓宇', '架构组、各建设组'),
    37: ('应用组', '张权', '综合保障 张科、国脉 6 人'),
    38: ('应用组', '张权', '综合保障、数据组'),
    39: ('应用组', '张权', '综合保障、数据组'),
}

# 任务号 -> 关联的运营指标主线
LINK = {
    9: '数据编目', 10: '数据归集', 11: '一数一源一标准', 12: '数据质量',
    13: '基础库', 14: '主题库', 15: '专题库', 16: '数据共享', 17: '数据开放',
    18: '数据供需', 19: '数据回流', 20: '公共数据（数据要素市场化）',
    21: '高效办成一件事', 22: '重点应用场景', 23: '安全保障', 25: '标准规范',
    26: '数据采购', 34: '安全保障',
}

MILESTONES = [
    ('M1', '2026-12-31', '年度目标节点', '主体/非主体平台开发测试完成，专属云基础环境就绪，各数据资源建设达成年底成效目标',
     '运营指标 2026 年底阶段目标值全部达成；平台建设完成开发对接测试及安全测评，具备上线运行条件'),
    ('M2', '2027-02-28', '系统初验', '初验（含初验准备、初验会议），专属云上线验证完成、迁移方案验证完成',
     '初验通过；平台上线运行；运营指标达成初验阶段目标值'),
    ('M3', '2027-03-31', '迁移实施完成', '正式迁移实施完成，双轨并行验证、第三方测评（软件测评、等保、密评）开展',
     '迁移实施完成率 100%；第三方测评启动'),
    ('M4', '2027-05-15', '系统终验', '终验准备、终验；原系统下线；系统试运行及功能完善完成',
     '终验通过；原系统下线；运营指标达成终验阶段目标值（专属云）'),
    ('M5', '2027-05-31', '全面推广', '系统全面推广使用；标准规范贯标落地；培训推广完成',
     '推广范围覆盖省直部门；标准规范贯标完成'),
]

ORG = [
    ('领导组', '组长', '谭明', '副组长：陈燕芬、杨荫飞、王青、王辉；成员：彭强（王怡）、李波、李冬冬、康晓宇、沙淑霞、邱巍、贺虎、周丹丹、姚兴龙'),
    ('综合保障', '负责人', '张科', '杨俊梅、何茜茜（负责整体商务沟通、流程等）'),
    ('PMO办公室', '成员', '康晓宇', '张谊、徐鹏、朱宇、张科、邵雷（王君）、成勇、钟嘉'),
    ('基础设施板块', '云架构师', '方荣增', '运维经理 周鑫、项目经理 曹高山、技术经理 夏枭；共计 22 人'),
    ('  云技术组', '组长', '夏枭', '5 人：联通 4 人（复用 1 人、新招 3 人）'),
    ('  云交付组', '组长', '曹高山', '6 人：联通 3 人、新招 3 人、阿里 2 人'),
    ('  云运营组', '组长', '刘成立', '3 人：联通 2 人、新招 2 人'),
    ('  云运维组', '组长', '李鹏勇', '8 人：联通 2 人、新招 2 人、阿里 5 人'),
    ('项目实施板块', '项目经理', '李齐、钟嘉（联通）', '数重 江胤锐、川数 何原炬、阿里 董静宜/汪雨鑫；共计 203 人'),
    ('  架构组', '组长', '陈俊雄（阿里）', '4 人：康晓宇（邵雷，联通）、数重 1 人、姚兴龙（川数）'),
    ('  主体平台组', '组长', '易志伟（数重）', '69 人：联通 张权、川数 韩弋林、安恒 2 人、浪潮 18 人、数重+阿里 43 人、年化 3 人'),
    ('  应用组', '组长', '张权（联通）', '53 人：川数 1 人、待定 12 人、联通 18 人、测绘+超图 3 人、国脉 6 人、中智软件 4 人、足迹 6 人、浪潮 3 人'),
    ('  数据组', '组长', '杨金伟（数重）', '67 人：数重 9、联通 15、浪潮 4、测绘+超图 2、三合力通 4、高德 3、映潮 2、川数 6、中智软件 2、足迹 1、乐云 2、年化 8、国脉 2'),
    ('  安全组', '组长', '阿里（XXX）', '6 人：安恒 4 人、川数 1 人'),
    ('  标准组', '组长', '纪加兴（数重）', '4 人：联通 1 人、川数 1 人、国脉 1 人'),
]


def serial_to_date(v):
    if isinstance(v, (int, float)):
        return date(1899, 12, 30) + timedelta(days=int(v))
    return None


def parse_gantt():
    wb = load_workbook(SRC_ZZT, data_only=True)
    ws = wb['Sheet1']
    weeks = {}
    for c in range(4, 36):
        dt = serial_to_date(ws.cell(3, c).value)
        if dt:
            weeks[c] = dt
    bars = {}
    for m in ws.merged_cells.ranges:
        if m.min_row >= 4 and m.max_col >= 4 and m.min_col <= 35:
            s, e = weeks.get(m.min_col), weeks.get(m.max_col)
            if s and e:
                bars.setdefault(m.min_row, []).append((s, e))
    tasks = []
    cur_cat = ''
    for r in range(4, ws.max_row + 1):
        no = ws.cell(r, 1).value
        cat = ws.cell(r, 2).value
        name = ws.cell(r, 3).value
        if cat:
            cur_cat = str(cat).replace('\n', '').strip()
        if not name or not no:
            continue
        no = int(no)
        segs = sorted(bars.get(r, []))
        if not segs:
            # 没有合并条：取该行实际有文字的格子所在周（里程碑式单点）
            hit = [c for c in range(4, 36) if ws.cell(r, c).value and c in weeks]
            if hit:
                segs = [(weeks[min(hit)], weeks[max(hit)])]
        start = segs[0][0] if segs else None
        end = max(e for _, e in segs) if segs else None
        tasks.append({
            'no': no, 'cat': cur_cat, 'name': str(name).replace('\n', '').strip(),
            'start': start, 'end': end, 'segs': segs,
        })
    wb.close()
    return tasks, sorted(weeks.values())


def read_ops():
    wb = load_workbook(SRC_ZB, data_only=True)
    ws = wb['验收成效指标-运营']
    out, cur_main, cur_task = [], '', ''
    for r in range(3, ws.max_row + 1):
        no, main, task, item = ws.cell(r, 1).value, ws.cell(r, 2).value, ws.cell(r, 3).value, ws.cell(r, 4).value
        if main:
            cur_main = str(main).strip()
        if task:
            cur_task = str(task).strip()
        if not (no or task or item):
            continue
        out.append({
            'no': no, '主线': cur_main, '任务': cur_task,
            '验收指标': str(item or '').strip(),
            '2026底': str(ws.cell(r, 5).value or '').strip(),
            '2027-02': str(ws.cell(r, 6).value or '').strip(),
            '2027-05': str(ws.cell(r, 7).value or '').strip(),
            '需协同': str(ws.cell(r, 8).value or '').strip(),
            '依据': str(ws.cell(r, 9).value or '').strip(),
            '验证': str(ws.cell(r, 10).value or '').strip(),
        })
    wb.close()
    return out


def read_platform():
    wb = load_workbook(SRC_ZB, data_only=True)
    ws = wb['验收成效指标-平台建设']
    anchor = {}
    for m in ws.merged_cells.ranges:
        if m.min_col <= 8 <= m.max_col:
            for r in range(m.min_row, m.max_row + 1):
                anchor[r] = m.min_row
    out, cur_sys, cur_cls, cur_blk = [], '', '', ''
    for r in range(3, ws.max_row + 1):
        no = ws.cell(r, 1).value
        if ws.cell(r, 2).value:
            cur_cls = str(ws.cell(r, 2).value).strip()
        if ws.cell(r, 3).value:
            cur_blk = str(ws.cell(r, 3).value).strip()
        if ws.cell(r, 4).value:
            cur_sys = str(ws.cell(r, 4).value).strip()
        if not no:
            continue
        out.append({
            'no': int(no), '分类': cur_cls, '板块': cur_blk, '系统': cur_sys,
            '子系统': str(ws.cell(r, 5).value or '/').strip(),
            '建设内容': str(ws.cell(r, 6).value or '').strip(),
            '应用场景': str(ws.cell(r, 7).value or '').strip(),
            '评价与验收标准': str(ws.cell(anchor.get(r, r), 8).value or '').strip(),
        })
    wb.close()
    return out


def style_sheet(ws, widths, freeze='A2', wrap_cols=()):
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[ws.cell(1, i).column_letter].width = w
    for c in range(1, len(widths) + 1):
        cell = ws.cell(1, c)
        cell.fill = HEAD_FILL
        cell.font = HEAD_FONT
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    ws.row_dimensions[1].height = 30
    for row in ws.iter_rows(min_row=1, max_row=ws.max_row, max_col=len(widths)):
        for cell in row:
            cell.border = BORDER
            if cell.row > 1:
                cell.alignment = Alignment(vertical='top', wrap_text=cell.column in wrap_cols)
    ws.freeze_panes = freeze
    ws.auto_filter.ref = ws.dimensions


def main():
    tasks, weeks = parse_gantt()
    ops = read_ops()
    plat = read_platform()
    wb = Workbook()

    # ── Sheet1 任务台账
    ws = wb.active
    ws.title = '任务台账'
    ws.append(['序号', '工作分类', '工作任务', '责任组', '责任人', '执行成员',
               '计划开始', '计划完成', '工期(周)', '关联运营指标主线',
               '当前进度%', '状态', '问题与风险', '备注'])
    for t in tasks:
        g, owner, members = DUTY.get(t['no'], (TODO, TODO, TODO))
        dur = round((t['end'] - t['start']).days / 7) + 1 if t['start'] and t['end'] else None
        ws.append([
            t['no'], t['cat'], t['name'], g, owner, members,
            t['start'].isoformat() if t['start'] else TODO,
            t['end'].isoformat() if t['end'] else TODO,
            dur, LINK.get(t['no'], ''),
            None, '未开始', '', '',
        ])
    style_sheet(ws, [6, 12, 34, 13, 14, 34, 12, 12, 8, 22, 9, 9, 20, 16], freeze='D2', wrap_cols=(3, 6))

    # ── Sheet2 里程碑
    ws = wb.create_sheet('里程碑')
    ws.append(['节点', '目标日期', '节点名称', '交付内容', '验收标准', '责任人', '当前状态'])
    for code, dt, name, deliver, crit in MILESTONES:
        ws.append([code, dt, name, deliver, crit, '康晓宇（PMO）', '未开始'])
    style_sheet(ws, [7, 12, 14, 46, 46, 14, 10], freeze='A2', wrap_cols=(4, 5))

    # ── Sheet3 组织架构
    ws = wb.create_sheet('组织架构')
    ws.append(['部门/组', '角色', '姓名', '说明'])
    for row in ORG:
        ws.append(list(row))
    style_sheet(ws, [16, 12, 20, 82], freeze='A2', wrap_cols=(4,))

    # ── Sheet4 运营成效指标
    ws = wb.create_sheet('运营成效指标')
    ws.append(['序号', '运营主线', '运营任务', '验收指标（建成要件）',
               '2026年底目标值', '2027年2月初验目标值', '2027年5月终验目标值',
               '需协同条件', '依据条款/标准', '验证方法'])
    for o in ops:
        ws.append([o['no'], o['主线'], o['任务'], o['验收指标'], o['2026底'],
                   o['2027-02'], o['2027-05'], o['需协同'], o['依据'], o['验证']])
    style_sheet(ws, [6, 16, 20, 40, 36, 36, 36, 24, 24, 24], freeze='D2',
                wrap_cols=(4, 5, 6, 7, 8, 9, 10))

    # ── Sheet5 平台建设指标
    ws = wb.create_sheet('平台建设指标')
    ws.append(['序号', '分类', '板块', '系统', '子系统', '建设内容',
               '应用场景', '评价与验收标准'])
    for p in plat:
        ws.append([p['no'], p['分类'], p['板块'], p['系统'], p['子系统'],
                   p['建设内容'], p['应用场景'], p['评价与验收标准']])
    style_sheet(ws, [6, 18, 22, 24, 12, 46, 40, 56], freeze='D2', wrap_cols=(6, 7, 8))

    # ── Sheet6 使用说明
    ws = wb.create_sheet('使用说明')
    ws.append(['项目', '说明'])
    notes = [
        ('这份表是什么', '作战图的数据底盘。作战图页面直接读取本文件渲染，改这里就等于改图。'),
        ('三个必改列', '责任人、计划开始/完成、当前进度%。这三列决定图上显示什么。'),
        ('进度%怎么填', '填 0-100 的整数。图上按百分比给任务条填充，超期未完成显示红色。'),
        ('状态怎么填', '只能填：未开始 / 进行中 / 已完成 / 已超期 / 已暂停。其他写法图上不认。'),
        ('任务台账加行', '可以直接往下加行，序号接着往下编，作战图会自动包含。'),
        ('运营成效指标', '来自验收成效指标-运营 sheet，三个节点目标值不要改列名。'),
        ('平台建设指标', '来自验收成效指标-平台建设 sheet，含运营成效引用句。'),
        ('组织架构', '人员构成较粗，具体到执行人还需要各组补充；责任人为组长。'),
        ('改了之后怎么看图', '双击打开作战图 HTML → 页面自动读取同目录的 作战图数据底盘.xlsx；'
                            '如果没读到，点页面右上角「载入数据」选择本文件即可。'),
    ]
    for k, v in notes:
        ws.append([k, v])
    style_sheet(ws, [18, 100], freeze='A2', wrap_cols=(2,))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    wb.save(OUT)
    print(f'已生成: {OUT}')
    print(f'  任务台账 {len(tasks)} 行')
    print(f'  里程碑 {len(MILESTONES)} 行')
    print(f'  组织架构 {len(ORG)} 行')
    print(f'  运营成效指标 {len(ops)} 行')
    print(f'  平台建设指标 {len(plat)} 行')
    print(f'  周轴 {weeks[0]} ~ {weeks[-1]}（{len(weeks)} 周）')
    miss = [t['no'] for t in tasks if not t['start']]
    if miss:
        print(f'  ⚠️ 无甘特条的任务号: {miss}')
    json.dump({'tasks': [{**t, 'start': t['start'].isoformat() if t['start'] else None,
                          'end': t['end'].isoformat() if t['end'] else None,
                          'segs': [[a.isoformat(), b.isoformat()] for a, b in t['segs']]} for t in tasks],
               'weeks': [w.isoformat() for w in weeks]},
              open('/opt/data/designs/drs-zzh/_tasks.json', 'w'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""作战图数据底盘 v2：为「领导驾驶舱 + PMO 下钻」补齐字段。

在 v1 基础上新增：
  所属系统      —— 任务归到哪个系统（下钻第二层）
  关联建设项     —— 平台建设指标序号，用于从任务跳到具体建设内容
  计划进度%     —— 按日期自动算（Excel 公式）
  实际进度%     —— PMO 每周填报（黄色底）
  偏差          —— 自动算 = 实际 - 计划
  指标当前完成情况 —— 两张指标表各加一列，PMO 填
"""
import json
import pathlib
from datetime import date, timedelta

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

SRC_ZZT = '/opt/data/cache/documents/native-inputs/b4e2655aac7ca6a1f0d214122cfa13f354736413af1eb84b29b4098e34f2d83c/doc_96630c3ac184_四川省一体化数据资源管理系统-项目作战图-20261024(1).xlsx'
SRC_ZB = '/opt/data/cache/documents/native-inputs/c30b4f9d3bad9ca157b403a7082d4460d769e6721f277e018b67e4a06f896640/doc_4128fecb4055_验收成效指标1101-1206.xlsx'
OUT = pathlib.Path('/opt/data/designs/drs-zzh/作战图数据底盘.xlsx')

HEAD_FILL = PatternFill('solid', fgColor='1F4E79')
HEAD_FONT = Font(color='FFFFFF', bold=True, size=10)
TODO_FILL = PatternFill('solid', fgColor='FFF2CC')
THIN = Side(style='thin', color='BFBFBF')
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
TODO = '【待填】'
NONE_SYS = '无对应系统（缺口）'

# 任务号 -> (责任组, 责任人, 执行成员, 所属系统, 关联建设项序号, 关联运营主线)
DUTY = {
    1: ('综合保障', '张科', '杨俊梅、何茜茜', '合同与商务', '—', ''),
    2: ('PMO办公室', '康晓宇', '张谊、徐鹏、朱宇、成勇、钟嘉', '项目管理', '—', ''),
    3: ('PMO办公室', '康晓宇', TODO, '项目管理', '—', ''),
    4: ('架构组', '陈俊雄', '康晓宇（邵雷）、数重 1 人、川数 姚兴龙', '总体架构设计', '—', ''),
    5: ('架构组', '陈俊雄', '康晓宇（邵雷）、数重 1 人', '总体架构设计', '—', ''),
    6: ('主体平台组', '易志伟', '联通 张权、川数 韩弋林、浪潮 18 人、数重+阿里 43 人', '主体平台（编目/归集/治理/共享）', '49,50,51,54,57', '数据编目'),
    7: ('应用组', '张权', '川数 1 人、国脉 6 人、中智软件 4 人、足迹 6 人、待定 12 人', '非主体平台（应用服务）', '39-45,48', '重点应用场景'),
    8: ('主体平台组', '易志伟', '应用组 张权', '平台上线验证', '—', ''),
    9: ('数据组', '杨金伟', '联通 靳爱辉、川数 李倩、数重 9 人、联通 15 人', '数据编目 / 数据全景地图', '49,62', '数据编目'),
    10: ('数据组', '杨金伟', '联通 靳爱辉、浪潮 4 人、高德 3 人', '数据归集 / 数据高铁', '57,55', '数据归集'),
    11: ('数据组', '杨金伟', '数重 9 人、川数 6 人', '一数一源管理系统 / 数据治理系统', '50,51', '一数一源一标准'),
    12: ('数据组', '杨金伟', '三合力通 4 人、映潮 2 人', '数据质量评估 / 数据治理系统', '54,51', '数据质量'),
    13: ('数据组', '杨金伟', '测绘+超图 2 人、中智软件 2 人', '数据融合分析（基础库）', '52', '基础库'),
    14: ('数据组', '杨金伟', '数重 9 人、川数 6 人', '数据融合分析（主题库）', '52', '主题库'),
    15: ('数据组', '杨金伟', '数重 9 人、年化 8 人', '数据融合分析 / 模型管理', '52,59', '专题库'),
    16: ('数据组', '杨金伟', '联通 15 人、川数 6 人', '数据共享（升级）/ 共享门户 / 数据服务管理', '29,36,60', '数据共享'),
    17: ('数据组', '杨金伟', '国脉 2 人、乐云 2 人', '数据开放（升级）/ 开放门户', '30,37,38', '数据开放'),
    18: ('数据组', '杨金伟', '川数 6 人', '数据供需对接', '56', '数据供需'),
    19: ('数据组', '杨金伟', '川数 6 人、联通 15 人', '数据共享（升级）/ 平台协同', '36,64', '数据回流'),
    20: ('数据组', '杨金伟', '数重 9 人、乐云 2 人', '公共数据授权运营 / 授权运营门户 / 数据资源调查', '32,47,58', '公共数据（数据要素市场化）'),
    21: ('数据组', '杨金伟', '联通 15 人、中智软件 2 人', '政务服务应用服务', '40', '高效办成一件事'),
    22: ('数据组', '杨金伟', '测绘+超图 2 人、高德 3 人', '应用服务（空间/商贸/地址码/人房/决策）', '39,42,43,44,48', '重点应用场景'),
    23: ('数据组', '杨金伟', '数重 9 人、年化 8 人', '网络和数据安全中心 / 网络安全 / 数据安全', '4-28', '安全保障'),
    24: ('安全组', '阿里（XXX）', '安恒 4 人、川数 1 人', NONE_SYS, '—', '安全保障（商密改造）'),
    25: ('标准组', '纪加兴', '联通 1 人、川数 1 人、国脉 1 人', NONE_SYS, '—', '标准规范'),
    26: ('数据组', '杨金伟', '高德 3 人、映潮 2 人', NONE_SYS, '—', '数据采购'),
    27: ('云技术组', '夏枭', '联通 4 人（含复用 1 人、新招 3 人）', '专属云基础设施', '—', ''),
    28: ('云交付组', '曹高山', '联通 3 人、新招 3 人、阿里 2 人', '专属云安评', '—', '安全保障'),
    29: ('云交付组', '曹高山', '联通 3 人、阿里 2 人', '专属云迁移', '—', ''),
    30: ('云交付组', '曹高山', '联通 3 人、新招 3 人、阿里 2 人', '专属云迁移', '—', ''),
    31: ('云交付组', '曹高山', '联通、阿里、川数', '专属云迁移', '—', ''),
    32: ('云交付组', '曹高山', '联通、阿里、川数', '专属云迁移', '—', ''),
    33: ('PMO办公室', '康晓宇', '架构组、各建设组', '双轨并行验证', '—', ''),
    34: ('安全组', '阿里（XXX）', '安恒 4 人、川数 1 人', '第三方测评（软件/等保/密评）', '4-28', '安全保障'),
    35: ('主体平台组', '易志伟', '各建设组', '系统功能完善', '—', ''),
    36: ('PMO办公室', '康晓宇', '架构组、各建设组', '初验 / 终验', '—', ''),
    37: ('应用组', '张权', '综合保障 张科、国脉 6 人', '培训推广', '—', ''),
    38: ('应用组', '张权', '综合保障、数据组', '培训推广', '—', ''),
    39: ('应用组', '张权', '综合保障、数据组', '培训推广', '—', ''),
}

MILESTONES = [
    ('M1', '2026-12-31', '年度目标节点', '主体/非主体平台开发测试完成，专属云基础环境就绪，各数据资源建设达成年底成效目标',
     '运营指标 2026 年底阶段目标值全部达成；平台建设完成开发对接测试及安全测评', '康晓宇'),
    ('M2', '2027-02-28', '系统初验', '初验（含初验准备、初验会议），专属云上线验证完成、迁移方案验证完成',
     '初验通过；平台上线运行；运营指标达成初验阶段目标值', '康晓宇'),
    ('M3', '2027-03-31', '迁移实施完成', '正式迁移实施完成，双轨并行验证、第三方测评开展',
     '迁移实施完成率 100%；第三方测评启动', '曹高山'),
    ('M4', '2027-05-15', '系统终验', '终验准备、终验；原系统下线；系统试运行及功能完善完成',
     '终验通过；原系统下线；运营指标达成终验阶段目标值（专属云）', '康晓宇'),
    ('M5', '2027-05-31', '全面推广', '系统全面推广使用；标准规范贯标落地；培训推广完成',
     '推广范围覆盖省直部门；标准规范贯标完成', '张权'),
]

ORG = [
    ('领导组', '组长', '谭明', '', '副组长：陈燕芬、杨荫飞、王青、王辉；成员：彭强（王怡）、李波、李冬冬、康晓宇、沙淑霞、邱巍、贺虎、周丹丹、姚兴龙'),
    ('综合保障', '负责人', '张科', 3, '杨俊梅、何茜茜（负责整体商务沟通、流程等）'),
    ('PMO办公室', '成员', '康晓宇', 8, '张谊、徐鹏、朱宇、张科、邵雷（王君）、成勇、钟嘉'),
    ('基础设施板块', '云架构师', '方荣增', 22, '运维经理 周鑫、项目经理 曹高山、技术经理 夏枭；板块合计 22 人（5 人复用、7 人复用阿里、需招聘 10 人）'),
    ('云技术组', '组长', '夏枭', 5, '联通 4 人（复用 1 人、新招 3 人）'),
    ('云交付组', '组长', '曹高山', 6, '联通 3 人、新招 3 人、阿里 2 人'),
    ('云运营组', '组长', '刘成立', 3, '联通 2 人、新招 2 人'),
    ('云运维组', '组长', '李鹏勇', 8, '联通 2 人、新招 2 人、阿里 5 人'),
    ('项目实施板块', '项目经理', '李齐、钟嘉（联通）', 203, '数重 江胤锐、川数 何原炬、阿里 董静宜/汪雨鑫；板块合计 203 人（建设迁移 126 + 运营运维 77）'),
    ('架构组', '组长', '陈俊雄（阿里）', 4, '康晓宇（邵雷，联通）、数重 1 人、姚兴龙（川数）'),
    ('主体平台组', '组长', '易志伟（数重）', 69, '联通 张权、川数 韩弋林、安恒 2 人、浪潮 18 人、数重+阿里 43 人、年化 3 人'),
    ('应用组', '组长', '张权（联通）', 53, '川数 1 人、待定 12 人、联通 18 人、测绘+超图 3 人、国脉 6 人、中智软件 4 人、足迹 6 人、浪潮 3 人'),
    ('数据组', '组长', '杨金伟（数重）', 67, '数重 9、联通 15、浪潮 4、测绘+超图 2、三合力通 4、高德 3、映潮 2、川数 6、中智软件 2、足迹 1、乐云 2、年化 8、国脉 2'),
    ('安全组', '组长', '阿里（XXX）', 6, '安恒 4 人、川数 1 人'),
    ('标准组', '组长', '纪加兴（数重）', 4, '联通 1 人、川数 1 人、国脉 1 人'),
]


def serial_to_date(v):
    if isinstance(v, (int, float)):
        return date(1899, 12, 30) + timedelta(days=int(v))
    return None


def parse_gantt():
    wb = load_workbook(SRC_ZZT, data_only=True)
    ws = wb['Sheet1']
    weeks = {c: serial_to_date(ws.cell(3, c).value) for c in range(4, 36)}
    weeks = {k: v for k, v in weeks.items() if v}
    bars = {}
    for m in ws.merged_cells.ranges:
        if m.min_row >= 4 and m.max_col >= 4 and m.min_col <= 35:
            s, e = weeks.get(m.min_col), weeks.get(m.max_col)
            if s and e:
                bars.setdefault(m.min_row, []).append((s, e))
    tasks, cur_cat = [], ''
    for r in range(4, ws.max_row + 1):
        no, cat, name = ws.cell(r, 1).value, ws.cell(r, 2).value, ws.cell(r, 3).value
        if cat:
            cur_cat = str(cat).replace('\n', '').strip()
        if not name or not no:
            continue
        no = int(no)
        segs = sorted(bars.get(r, []))
        if not segs:
            hit = [c for c in range(4, 36) if ws.cell(r, c).value and c in weeks]
            if hit:
                segs = [(weeks[min(hit)], weeks[max(hit)])]
        tasks.append({'no': no, 'cat': cur_cat, 'name': str(name).replace('\n', '').strip(),
                      'start': segs[0][0] if segs else None,
                      'end': max(e for _, e in segs) if segs else None})
    wb.close()
    return tasks, sorted(weeks.values())


def read_ops():
    wb = load_workbook(SRC_ZB, data_only=True)
    ws = wb['验收成效指标-运营']
    out, cur_m, cur_t = [], '', ''
    for r in range(3, ws.max_row + 1):
        no, m, t, it = ws.cell(r, 1).value, ws.cell(r, 2).value, ws.cell(r, 3).value, ws.cell(r, 4).value
        if m:
            cur_m = str(m).strip()
        if t:
            cur_t = str(t).strip()
        if not (no or t or it):
            continue
        out.append({'no': no, '主线': cur_m, '任务': cur_t, '指标': str(it or '').strip(),
                    '2026底': str(ws.cell(r, 5).value or '').strip(),
                    '2027-02': str(ws.cell(r, 6).value or '').strip(),
                    '2027-05': str(ws.cell(r, 7).value or '').strip(),
                    '需协同': str(ws.cell(r, 8).value or '').strip(),
                    '依据': str(ws.cell(r, 9).value or '').strip(),
                    '验证': str(ws.cell(r, 10).value or '').strip()})
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
        out.append({'no': int(no), '分类': cur_cls, '板块': cur_blk, '系统': cur_sys,
                    '子系统': str(ws.cell(r, 5).value or '/').strip(),
                    '建设内容': str(ws.cell(r, 6).value or '').strip(),
                    '应用场景': str(ws.cell(r, 7).value or '').strip(),
                    '评价与验收标准': str(ws.cell(anchor.get(r, r), 8).value or '').strip()})
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
    ws.row_dimensions[1].height = 32
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

    ws = wb.active
    ws.title = '任务台账'
    ws.append(['序号', '工作分类', '工作任务', '所属系统', '责任组', '责任人', '执行成员',
               '计划开始', '计划完成', '工期(周)', '计划进度%', '实际进度%', '状态',
               '偏差', '关联运营主线', '关联建设项', '问题与风险'])
    for t in tasks:
        g, owner, members, sysname, plink, link = DUTY.get(t['no'], (TODO,) * 6)
        dur = round((t['end'] - t['start']).days / 7) + 1 if t['start'] and t['end'] else None
        r = ws.max_row + 1
        ws.append([t['no'], t['cat'], t['name'], sysname, g, owner, members,
                   t['start'].isoformat() if t['start'] else TODO,
                   t['end'].isoformat() if t['end'] else TODO,
                   dur, None, None, '未开始', None, link, plink, ''])
        ws.cell(r, 11).value = (f'=IF(OR(H{r}="",I{r}=""),0,'
                                f'MEDIAN(0,100,ROUND((TODAY()-DATEVALUE(H{r}))/'
                                f'MAX(1,DATEVALUE(I{r})-DATEVALUE(H{r}))*100,0)))')
        ws.cell(r, 14).value = f'=IF(L{r}="","未填报",L{r}-K{r})'
        ws.cell(r, 12).fill = TODO_FILL
        ws.cell(r, 12).alignment = Alignment(horizontal='center')
    style_sheet(ws, [6, 12, 30, 26, 11, 13, 28, 11, 11, 8, 9, 9, 9, 9, 18, 12, 16],
                freeze='E2', wrap_cols=(3, 4, 7))

    ws = wb.create_sheet('里程碑')
    ws.append(['节点', '目标日期', '节点名称', '交付内容', '验收标准', '责任人', '当前状态'])
    for code, dt, name, deliver, crit, own in MILESTONES:
        ws.append([code, dt, name, deliver, crit, own, '未开始'])
    style_sheet(ws, [7, 12, 14, 46, 46, 12, 10], freeze='A2', wrap_cols=(4, 5))

    ws = wb.create_sheet('组织架构')
    ws.append(['部门/组', '角色', '姓名', '人数', '说明'])
    for unit, role, name, cnt, note in ORG:
        ws.append([unit, role, name, cnt, note])
    style_sheet(ws, [16, 12, 20, 8, 86], freeze='A2', wrap_cols=(5,))

    ws = wb.create_sheet('运营成效指标')
    ws.append(['序号', '运营主线', '运营任务', '验收指标（建成要件）',
               '2026年底目标值', '2027年2月初验目标值', '2027年5月终验目标值',
               '当前完成情况', '需协同条件', '依据条款/标准', '验证方法'])
    for o in ops:
        ws.append([o['no'], o['主线'], o['任务'], o['指标'], o['2026底'],
                   o['2027-02'], o['2027-05'], '', o['需协同'], o['依据'], o['验证']])
        ws.cell(ws.max_row, 8).fill = TODO_FILL
    style_sheet(ws, [6, 16, 20, 38, 34, 34, 34, 22, 22, 22, 22], freeze='D2',
                wrap_cols=(4, 5, 6, 7, 8, 9, 10, 11))

    ws = wb.create_sheet('平台建设指标')
    ws.append(['序号', '分类', '板块', '系统', '子系统', '建设内容', '应用场景',
               '评价与验收标准', '当前完成情况'])
    for p in plat:
        ws.append([p['no'], p['分类'], p['板块'], p['系统'], p['子系统'],
                   p['建设内容'], p['应用场景'], p['评价与验收标准'], ''])
        ws.cell(ws.max_row, 9).fill = TODO_FILL
    style_sheet(ws, [6, 18, 22, 24, 12, 46, 38, 54, 22], freeze='D2', wrap_cols=(6, 7, 8, 9))

    ws = wb.create_sheet('使用说明')
    ws.append(['项目', '说明'])
    notes = [
        ('这份表干什么', '作战图/驾驶舱的数据底盘。页面直接读这份 Excel 渲染，改这里就等于改图。'),
        ('PMO 每周要填的列', '任务台账的「实际进度%」「状态」「问题与风险」，以及两张指标表的「当前完成情况」。黄色底就是要填的。'),
        ('实际进度%', '填 0-100 整数。留空 = 未填报，驾驶舱单独统计，不当成 0。'),
        ('状态', '只能填：未开始 / 进行中 / 已完成 / 已超期 / 已暂停。'),
        ('计划进度%', '自动算，别手改。按今天在计划工期内的时间占比得出。'),
        ('偏差', '自动算 = 实际进度 - 计划进度。判定：≥0 正常、-1~-15 预警、<-15 延期。'),
        ('所属系统', '下钻的第二层。改这里可以把任务归到别的系统下。'),
        ('关联建设项', '对应「平台建设指标」序号，用于从任务跳到具体建设内容。'),
        ('加任务', '任务台账往下加行，序号接着编，「所属系统」「责任组」必填。'),
        ('指标两张表', '来自验收成效指标 1101-1206，列名别改。'),
    ]
    for k, v in notes:
        ws.append([k, v])
    style_sheet(ws, [22, 100], freeze='A2', wrap_cols=(2,))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    wb.save(OUT)
    print(f'已生成 {OUT}')
    print(f'  任务台账 {len(tasks)} 行（含所属系统 / 计划进度公式 / 偏差公式）')
    print(f'  里程碑 {len(MILESTONES)} · 组织架构 {len(ORG)} · 运营指标 {len(ops)} · 平台建设 {len(plat)}')
    print(f'  周轴 {weeks[0]} ~ {weeks[-1]}（{len(weeks)} 周）')
    json.dump({'tasks': [{**t, 'start': t['start'].isoformat() if t['start'] else None,
                          'end': t['end'].isoformat() if t['end'] else None} for t in tasks],
               'weeks': [w.isoformat() for w in weeks]},
              open('/opt/data/designs/drs-zzh/_tasks.json', 'w'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()

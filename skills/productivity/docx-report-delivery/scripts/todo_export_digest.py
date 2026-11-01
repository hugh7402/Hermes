#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""待办导出(.xls) → 季度条目摘要；草稿字数三口径统计。

用法:
    python3 todo_export_digest.py <todo.xls> [--start 2026-07-01] [--end 2026-09-30]
    python3 todo_export_digest.py --count <草稿.txt>

要点（详见 references/performance-summary-sources.md 第 6、7 节）:
  · 真 BIFF(OLE2) .xls，用 xlrd 读全部行；markitdown 也能读但筛不了行。
  · 不能只筛 分类=='工作' —— 导出里有空分类行，严格等于会静默丢掉真实工作项。
  · 清单通常不是全集，务必交叉验证：微信落盘 /opt/data/cache/documents/、知识库 01-WeiXin/、双周月报。
  · 字数按「含标点」严口径卡 300，报数时三个口径都给。
"""
import argparse
import re
import sys
from collections import Counter

NONWORK = ('生活',)          # 只排除明确的非工作分类，其余（含空分类）全留
LIMIT = 300


def read_rows(path):
    try:
        import xlrd
    except ImportError:
        sys.exit('需要 xlrd：pip install xlrd')
    sh = xlrd.open_workbook(path).sheet_by_index(0)
    hdr = [str(sh.cell_value(0, c)).strip() for c in range(sh.ncols)]
    rows = []
    for r in range(1, sh.nrows):
        d = {}
        for i, h in enumerate(hdr):
            v = sh.cell_value(r, i)
            if isinstance(v, float) and v == int(v):
                v = int(v)
            d[h] = str(v).strip() if v not in ('', None) else ''
        rows.append(d)
    return hdr, rows


def zi(s):
    """含标点字数（不计空白）。"""
    return len(re.sub(r'\s', '', s))


def han(s):
    """汉字/字母/数字数（不含标点）。"""
    return len(re.findall(r'[\u4e00-\u9fffA-Za-z0-9]', s))


def digest(path, start, end):
    hdr, rows = read_rows(path)
    print(f'表头: {hdr}\n共 {len(rows)} 条')
    print('分类分布:', dict(Counter(r.get('分类', '') for r in rows)))
    sel = [r for r in rows
           if (not start or r['日期'] >= start) and (not end or r['日期'] <= end)]
    work = [r for r in sel if r.get('分类', '') not in NONWORK]
    rng = f'{start or "—"} ~ {end or "—"}'   # 先算好：f-string 表达式里别写转义引号（3.12 以下 SyntaxError）
    print(f'\n区间 {rng}: 共 {len(sel)} 条，非生活类 {len(work)} 条')
    typo = [r for r in work if not r.get('分类')]
    if typo:
        print(f'⚠️ {len(typo)} 条分类为空 —— 必须保留，否则会漏真实工作项：')
        for r in typo:
            print(f"    {r['日期']}  {r['事件内容']}")
    print()
    for r in sorted(work, key=lambda x: x['日期']):
        bits = [r['事件内容']]
        for k in ('描述', '子任务'):
            if r.get(k):
                bits.append(f'{k}:{r[k]}')
        done = '✓' if r.get('是否完成') in ('True', '1', '是') else '○'
        print(f"  {r['日期']} {done} {' | '.join(bits)}")
    if len(work) < 8:
        print('\n⚠️ 区间内条目偏少 —— 这份清单通常不是全集，请交叉验证：')
        print('   /opt/data/cache/documents/（微信落盘）· 知识库 01-WeiXin/ · 双周与月度报告')


def count(path):
    t = open(path, encoding='utf-8').read()
    lines = [l for l in t.split('\n') if l.strip()]
    body = '\n'.join(lines[1:]).strip() if lines else ''
    print(f'全文  含标点 {zi(t)} ／ 不含标点 {han(t)}')
    print(f'正文（去掉首行标题）含标点 {zi(body)} ／ 不含标点 {han(body)}')
    print('\n按段:')
    for l in lines:
        print(f'  {zi(l):>4}  {l[:38]}')
    if zi(t) <= LIMIT:
        print(f'\n✅ 含标点全文 {zi(t)} ≤ {LIMIT}')
    else:
        print(f'\n❌ 超 {zi(t) - LIMIT} 字（含标点口径 {zi(t)} > {LIMIT}）')
        print('   压缩顺序：①删跨项重复表述 ②删动词软垫词 ③砍限定词 ④同级合并。别删条目。')
    return 0 if zi(t) <= LIMIT else 1


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('path', nargs='?', help='todo 导出 .xls 路径')
    ap.add_argument('--start', default='', help='起始日期 YYYY-MM-DD')
    ap.add_argument('--end', default='', help='结束日期 YYYY-MM-DD')
    ap.add_argument('--count', metavar='DRAFT', help='改跑字数统计模式')
    a = ap.parse_args()
    if a.count:
        sys.exit(count(a.count))
    if not a.path:
        ap.print_help()
        sys.exit(2)
    digest(a.path, a.start, a.end)

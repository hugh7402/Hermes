#!/usr/bin/env python3
"""OCR 快检：基于 pdf_scan_report.csv 统计真正缺 md 的文件。
用法: python3 quick_check.py [/tmp/pdf_scan_report.csv]
输出: SUSPECT 总数 / 已有完整 md / 真缺列表（文件名+页数+md大小+flag）
规范化规则必须与 re_ocr_cloud.py 一致，否则误报。
"""
import csv, re, os, sys
from pathlib import Path

CONCEPTS = '/opt/data/Obsidian Vault/Obsidian Vault/concepts'
report = sys.argv[1] if len(sys.argv) > 1 else '/tmp/pdf_scan_report.csv'


def normalize_name(s):
    s = re.sub(r'^[\d一二三四五六七八九十百]+[\.、]?\s*', '', s)
    s = s.replace('（', '(').replace('）', ')')
    s = re.sub(r'[《》"\' ]', '', s)
    return s


def build_md_index():
    idx = {}
    for f in os.listdir(CONCEPTS):
        if not f.endswith('.md'):
            continue
        idx[normalize_name(Path(f).stem)] = os.path.getsize(os.path.join(CONCEPTS, f))
    return idx


def md_ok(md_index, pdf_path, pages):
    n = normalize_name(Path(pdf_path).stem)
    if n in md_index:
        size = md_index[n]
    else:
        best = None
        for key, size in md_index.items():
            if n and len(n) >= 6 and (n in key or key in n):
                if best is None or len(key) > len(best[0]):
                    best = (key, size)
        if not best:
            return False, 0
        size = best[1]
    return size >= max(3000, pages * 150), size


def main():
    if not os.path.exists(report):
        print(f"❌ 报告不存在: {report} → 先跑 scan_pdfs.py 重扫")
        return 1
    md_index = build_md_index()
    total = suspect = ok = missing = 0
    missing_list = []
    with open(report, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            total += 1
            flag = row.get('flag', '')
            if flag in ('SUSPECT', 'EMPTY') or flag.startswith('ERR'):
                suspect += 1
                pages = int(row.get('pages', 0) or 0)
                good, size = md_ok(md_index, row.get('file', ''), pages)
                if good:
                    ok += 1
                else:
                    missing += 1
                    missing_list.append((row.get('file', '')[:60], pages, size, flag))
    print(f"扫描PDF总数: {total}")
    print(f"SUSPECT/EMPTY/ERR: {suspect}")
    print(f"已有完整md: {ok}")
    print(f"仍缺md: {missing}")
    for f, p, s, fl in missing_list:
        print(f"  {f} | {p}页 | md={s}B | {fl}")
    return 0


if __name__ == '__main__':
    sys.exit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""估算重 OCR 工作量：把污染笔记映射回源 PDF，统计总页数"""
import json, os, glob, re, sys

rows = json.load(open('/opt/data/.tmp_tests/ocr_noise.json'))
V = '/opt/data/Obsidian Vault/Obsidian Vault/concepts/'
BACKUP = '/opt/data/WebChat BackUp/文档'

# 建 源PDF 索引（按文件名 stem）
pdfs = {}
for p in glob.glob(os.path.join(BACKUP, '**', '*.pdf'), recursive=True):
    pdfs[os.path.basename(p)] = p
for p in glob.glob(os.path.join(BACKUP, '**', '*.PDF'), recursive=True):
    pdfs[os.path.basename(p)] = p
print(f"备份目录里的 PDF 总数: {len(pdfs)}")

try:
    import fitz
except ImportError:
    print("需要 pymupdf"); sys.exit(1)

sev = [r for r in rows if r['ratio'] < 0.3]
mid = [r for r in rows if 0.3 <= r['ratio'] < 0.6]
matched, unmatched = [], []
total_pages = 0
for r in rows:
    md = os.path.join(V, r['file'])
    src = None
    # 从 md 正文的「原始文件」行取源文件名
    try:
        s = open(md, encoding='utf-8', errors='ignore').read()[:1200]
        m = re.search(r'\*\*原始文件\*\*：(.+?)\s*$', s, re.M)
        if m:
            name = m.group(1).strip().strip('`')
            if name.endswith('.pdf') or name.endswith('.PDF'):
                src = pdfs.get(name)
    except Exception:
        pass
    if src and os.path.exists(src):
        try:
            n = len(fitz.open(src))
        except Exception:
            n = 0
        matched.append((r, src, n))
        total_pages += n
    else:
        unmatched.append(r)

print(f"\n能定位到源 PDF 的: {len(matched)} 篇 / 定位不到: {len(unmatched)} 篇")
print(f"需要重 OCR 的**总页数: {total_pages} 页**")
per_page = 4.6   # 百炼 qwen-vl-ocr 实测 ≈4.6s/页（150dpi）
print(f"按 4.6 s/页 单线程估算 ≈ {total_pages*per_page/3600:.1f} 小时")
print(f"按 6 路并发估算          ≈ {total_pages*per_page/6/3600:.1f} 小时")
print(f"按 12 路并发估算         ≈ {total_pages*per_page/12/3600:.1f} 小时")

# 成本：qwen-vl-ocr 约 0.3 元/M prompt token，单页约 1500 token（150dpi）
tok = total_pages * 1500
print(f"\n百炼 qwen-vl-ocr 成本估算: {tok/1e6:.2f}M token ≈ ¥{tok/1e6*0.5:.2f}（按 0.5 元/M 上限）")

print("\n=== 严重污染且能定位源 PDF（页数 top 20）===")
for r, src, n in sorted(matched, key=lambda x: -x[2])[:20]:
    if r['ratio'] < 0.3:
        print(f"  {n:4d}页  {r['ratio']*100:4.1f}%  {r['file'][:56]}")

json.dump([{'file': r['file'], 'ratio': r['ratio'], 'src': src, 'pages': n}
           for r, src, n in matched] + [{'file': r['file'], 'ratio': r['ratio'],
           'src': None, 'pages': 0} for r in unmatched],
          open('/opt/data/.tmp_tests/reocr_plan.json', 'w'), ensure_ascii=False, indent=1)
print("\n计划已写 /opt/data/.tmp_tests/reocr_plan.json")

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""宽松匹配：为「无源 PDF」的 37 篇找出真正的源 PDF"""
import json, os, re, glob

V = '/opt/data/Obsidian Vault/Obsidian Vault/concepts/'
BACKUP = '/opt/data/WebChat BackUp/文档'

def norm(s):
    s = str(s).lower()
    s = re.sub(r'\.(pdf|md|docx?|pptx?|xlsx?)$', '', s)
    s = re.sub(r'[\s\-_—–·、,，。.()（）【】\[\]《》""\'\'：:；;！!？?]+', '', s)
    return s

# 建 PDF 索引：归一化名 → 路径
pdfs = {}
for p in glob.glob(os.path.join(BACKUP, '**', '*.[pP][dD][fF]'), recursive=True):
    pdfs.setdefault(norm(os.path.basename(p)), []).append(p)
print(f"备份目录 PDF: {len(pdfs)} 个不同名（文件总数 {sum(len(v) for v in pdfs.values())}）")

plan = json.load(open('/opt/data/.tmp_tests/reocr_plan.json'))
targets = [e for e in plan if not e['src']]
print(f"待匹配: {len(targets)} 篇\n")

matched, unmatched = [], []
for e in targets:
    md = V + e['file']
    cands = []
    # 候选1: 文件名 stem
    cands.append(os.path.splitext(e['file'])[0])
    try:
        s = open(md, encoding='utf-8', errors='ignore').read()[:1500]
        m = re.search(r'\*\*原始文件\*\*：(.+?)\s*$', s, re.M)
        if m:
            # 去掉 .md / .pdf 后缀后重试（原始文件行常写 .md 但实际是 .pdf）
            cands.append(os.path.splitext(m.group(1).strip().strip('`'))[0])
        t = re.search(r'^title:\s*"?([^"\n]+)"?\s*$', s, re.M)
        if t:
            cands.append(t.group(1).strip())
    except Exception:
        pass

    hit = None
    for c in cands:
        n = norm(c)
        if n in pdfs:
            hit = pdfs[n][0]; break
    if not hit:
        # 模糊：归一化后互相包含且长度接近
        for c in cands:
            n = norm(c)
            if len(n) < 8:
                continue
            for k, v in pdfs.items():
                if (n in k or k in n) and abs(len(n) - len(k)) <= 8:
                    hit = v[0]; break
            if hit: break
    if hit:
        matched.append((e['file'], hit))
    else:
        unmatched.append(e['file'])

print(f"✅ 新匹配到源 PDF: {len(matched)} 篇")
for f, p in matched:
    print(f"   {f[:52]}\n      → {os.path.basename(p)[:70]}")
print(f"\n❌ 仍无源: {len(unmatched)} 篇")
for f in unmatched:
    print(f"   {f[:70]}")

json.dump([{'file': f, 'src': p} for f, p in matched],
          open('/opt/data/.tmp_tests/reocr_plan2.json', 'w'), ensure_ascii=False, indent=1)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修复阶段 A 的副作用：把误插到文件头的标记行，挪回 frontmatter 之后"""
import json, os, re

V = '/opt/data/Obsidian Vault/Obsidian Vault/concepts/'
plan = json.load(open('/opt/data/.tmp_tests/reocr_plan.json'))
targets = [e for e in plan if not e['src']]

MARK = re.compile(r'^> \*\*已剥离OCR布局标记\*\*：[^\n]*\n')
fixed = 0
for e in targets:
    p = V + e['file']
    if not os.path.exists(p):
        continue
    s = open(p, encoding='utf-8').read()
    if not s.startswith('>'):       # 只有被破坏的才修
        continue
    m = MARK.match(s)
    if not m:
        continue
    marker_line = m.group(0)
    rest = s[len(marker_line):]
    # rest 应以 frontmatter '---' 开头
    if not rest.startswith('---'):
        print(f"  ⚠️ 结构异常，跳过 {e['file'][:50]}")
        continue
    # 找 frontmatter 结束（第 2 个 '---'）
    lines = rest.split('\n')
    end = None
    for i in range(1, len(lines)):
        if lines[i].rstrip() == '---':
            end = i; break
    if end is None:
        print(f"  ⚠️ 无 fm 结束标记，跳过 {e['file'][:50]}")
        continue
    # 把标记行插到 fm 结束后（body 之前）
    new_lines = lines[:end+1] + ['', marker_line.rstrip('\n')] + lines[end+1:]
    open(p, 'w', encoding='utf-8').write('\n'.join(new_lines))
    fixed += 1

print(f"修复 {fixed}/{len(targets)} 篇（标记行挪到 frontmatter 之后）")

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第三遍：兜底剥离正文里剩下的广告（以「数据资产入表…17301209296」为锚，行内非贪婪）"""
import os, re, glob, sys

V = '/opt/data/Obsidian Vault/Obsidian Vault/concepts'
DRY = '--apply' not in sys.argv

PATTERNS = [
    # 以广告开头词为锚，到手机号结束；中间最多 45 字
    re.compile(r'数据资产入表[^\n]{0,45}?17301209296\s*[（(]?\s*同微信\s*[)）]?'),
    re.compile(r'数据资产入表[^\n]{0,30}?课程培训[^\n]{0,8}'),
    re.compile(r'第\s*\d+\s*页\s*,?\s*共\s*\d+\s*页(?=数据资产入表)'),
    # 纯残留
    re.compile(r'(?:电话|联系人|联系电话|负责人|咨询)[:：]?\s*陈阳\s*17301209296\s*[（(]?\s*同微信\s*[)）]?'),
    re.compile(r'9月成都首席数据官研修班[^\n]{0,30}?咨询'),
]

changed = removed = 0
for p in sorted(glob.glob(os.path.join(V, '*.md'))):
    try:
        s = open(p, encoding='utf-8').read()
    except Exception:
        continue
    lines = s.split('\n')
    start = 0
    if lines and lines[0].strip() == '---':
        for i in range(1, len(lines)):
            if lines[i].strip() == '---':
                start = i + 1
                break
    out, local = [], 0
    for i, ln in enumerate(lines):
        if i < start:
            out.append(ln); continue
        new = ln
        for pat in PATTERNS:
            new, n = pat.subn('', new)
            local += n
        new = re.sub(r'[ \t]{2,}', ' ', new).rstrip()
        out.append(new)
    if local:
        changed += 1; removed += local
        if not DRY:
            open(p, 'w', encoding='utf-8').write('\n'.join(out))

print(f"{'[DRY-RUN]' if DRY else '[已应用]'} 改动 {changed} 文件，剥离 {removed} 处")

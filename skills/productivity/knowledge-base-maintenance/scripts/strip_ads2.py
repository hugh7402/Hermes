#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第二遍：剥离**行内嵌**的营销广告子串（保留同一行的正文文字）

第一遍只删了独立成行的广告；OCR 常把页脚广告与正文粘在一行，
所以这里按子串精确剥离，且不动其他文字。作者署名前言之类的真实段落保留。
"""
import os, re, glob, sys

V = '/opt/data/Obsidian Vault/Obsidian Vault/concepts'
DRY = '--apply' not in sys.argv

# 按"锚定手机号/公众号"的精确模式剥离，不做泛化匹配
SUBS = [
    # 入表/首席数据官课程广告（可出现在行中任意位置）
    re.compile(r'数据资产入表(?:项目)?(?:咨询|资产)?[、，]?\s*(?:首席数据官)?(?:课程)?培训[:：]\s*陈阳\s*17301209296\s*[（(]?同微信[)）]?'),
    re.compile(r'(?:电话|联系人|负责人)[:：]\s*陈阳\s*17301209296\s*[（(]?同微信[)）]?'),
    re.compile(r'陈阳\s*17301209296\s*[（(]同微信[)）]?'),
    re.compile(r'17301209296\s*[（(]?同微信[)）]?'),
    # 公众号水印
    re.compile(r'[·•×Xx]?\s*公众号\s*[·:：]?\s*数据资产管理大讲堂'),
    re.compile(r'数据资产管理大讲堂'),
    # 独立成行的残留
]
LINE_PAT = [
    re.compile(r'^\s*陈阳老师\s*$'),
    re.compile(r'^\s*陈阳\s*$'),
    re.compile(r'^\s*-?\s*陈阳\s*$'),
]

changed = removed_sub = 0
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
        if any(pat.match(ln.strip()) for pat in LINE_PAT):
            local += 1; continue
        new = ln
        for pat in SUBS:
            new, n = pat.subn('', new)
            local += n
        new = re.sub(r'[ \t]{2,}', ' ', new).rstrip()
        if new.strip() in ('', '-', '---'):      # 剥空后只剩符号的行直接删
            if ln.strip() and new.strip() != '---':
                local += 1
                continue
        out.append(new)
    if local:
        changed += 1
        removed_sub += local
        if not DRY:
            open(p, 'w', encoding='utf-8').write('\n'.join(out))

print(f"{'[DRY-RUN]' if DRY else '[已应用]'} 改动 {changed} 个文件，剥离广告片段 {removed_sub} 处")
if DRY:
    print("（加 --apply 才写入）")

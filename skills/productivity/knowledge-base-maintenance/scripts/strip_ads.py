#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""清理源文档里的营销水印/广告行（逐行匹配，绝不碰 frontmatter）

来源：数据资产类 PDF 的页眉页脚硬广告，被 OCR 逐页吸进正文，
全库 336 个文件、约 3 万处。也是 2026-10-01 那条幽灵关联的产生原因。
"""
import os, re, glob, json, sys

V = '/opt/data/Obsidian Vault/Obsidian Vault/concepts'
DRY = '--apply' not in sys.argv

PATTERNS = [
    # 陈阳 的入表/首席数据官课程广告（全库 3 万处的元凶）
    re.compile(r'^.{0,60}陈阳.{0,30}1?7301209296.{0,30}$'),
    # 公众号引流（267 处 + 6 处）
    re.compile(r'^\s*公众号[·:：]\s*数据资产管理大讲堂\s*$'),
    re.compile(r'^.{0,40}阅览更多报告.{0,40}微信公众号\s*$'),
    re.compile(r'^.{0,20}扫码报名咨询.{0,20}$'),
]

# 先收集命中样本
hits = {}
total_removed = 0
files_changed = 0
for p in sorted(glob.glob(os.path.join(V, '*.md'))):
    try:
        s = open(p, encoding='utf-8').read()
    except Exception:
        continue
    lines = s.split('\n')
    # 跳过 frontmatter 区
    start = 0
    if lines and lines[0].strip() == '---':
        for i in range(1, len(lines)):
            if lines[i].strip() == '---':
                start = i + 1
                break
    kept, removed = [], 0
    for i, ln in enumerate(lines):
        if i >= start and any(pat.match(ln.strip()) for pat in PATTERNS):
            removed += 1
            if removed <= 2 and len(hits) < 12:
                hits.setdefault(os.path.basename(p), []).append(ln.strip()[:90])
            continue
        kept.append(ln)
    if removed:
        total_removed += removed
        files_changed += 1
        if not DRY:
            open(p, 'w', encoding='utf-8').write('\n'.join(kept))

print(f"{'[DRY-RUN]' if DRY else '[已应用]'} 命中文件 {files_changed} 个，删除广告行 {total_removed} 行")
print("\n样本：")
for f, v in list(hits.items())[:8]:
    print(f"  {f[:56]}")
    for x in v:
        print(f"      「{x}」")
if DRY:
    print("\n（加 --apply 才真正写入）")

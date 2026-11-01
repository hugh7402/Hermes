#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按《政务数据目录编目模板》生成约 100 条的归集离线数据（用于文件对接方式上传）
   取样自演示数据集，保持问题数据比例，便于现场演示治理环节。"""
import json
import pathlib
import csv

ROOT = pathlib.Path('/opt/data/designs/drs-demo')
OUT = ROOT / '交付' / '演示数据' / '归集离线数据_自然人基本登记信息_100条.csv'
SRC_CSV = ROOT / 'data' / '待归集数据_自然人基本登记信息.csv'

# 以现有演示数据文件为准（表头与字段完全一致）
with open(SRC_CSV, encoding='utf-8-sig', newline='') as f:
    rd = list(csv.reader(f))
hdr, body = rd[0], rd[1:]
print(f'源数据：{len(hdr)} 列 × {len(body)} 行')

# 等间隔取样 100 条（保留问题数据的自然比例）
step = max(1, len(body) // 100)
sample = [body[i] for i in range(0, len(body), step)][:100]
print(f'取样：每 {step} 行取 1 条 → {len(sample)} 条')

# 统计取样中的问题分布（供交付说明，不改数据）
ds = json.load(open(ROOT / 'data' / 'demo_dataset.json', encoding='utf-8'))
prob_rid = {p['_rid'] for p in ds['problems']}
# 按唯一标识匹配问题行（CSV 不含 _rid 列）
prob_keys = {p['key'] for p in ds['problems']}
key_i = hdr.index('自然人唯一标识')
n_prob = sum(1 for r in sample if r[key_i] in prob_keys)
print(f'取样中含问题数据：{n_prob} 条（源比例 {len(ds["problems"])}/{len(body)}）')

OUT.parent.mkdir(parents=True, exist_ok=True)
with open(OUT, 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f)
    w.writerow(hdr)
    w.writerows(sample)
print(f'✅ 已生成：{OUT}')
print(f'   大小 {OUT.stat().st_size / 1024:.1f} KB · {len(sample)} 条 × {len(hdr)} 列')
print(f'   表头：{hdr[:8]} …')

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""导出知识库巡检的**完整**问题清单

为什么需要它：`lint_vault.py` 的 main() 只印前 5 条（weak_tags 前 10 条），
后面是 `*...还有 N 篇*`。批量修复前不看全量清单会漏修。

用法：
    cd /opt/data && uv run --with pyyaml python3 \
        skills/productivity/knowledge-base-maintenance/scripts/vault_lint_dump.py

输出：
    /opt/data/.tmp_tests/vault_issues.json  （每个问题带 slug/title/path/正文体量/标签数）
    并打印按「正文体量」分档的清单，便于区分「真缺陷」与「<1KB 短表格文档（边缘态，不修）」

后续：取 no_fm ∪ no_tags ∪ no_summary ∪ weak_tags 的并集，**过滤掉 body_chars < 1000** 再跑 note_enhance。
"""
import json
import sys

sys.path.insert(0, '/opt/data')
import lint_vault as L  # noqa: E402

OUT = '/opt/data/.tmp_tests/vault_issues.json'
MIN_BODY = 1000   # 正文 <1KB 的短表格文档属边缘态，不修

notes = L.scan_all_notes()
orphans = L.check_orphans(notes)
# ⚠️ 必须传 extra_slugs：只索引 concepts/ 会把指向 01-WeiXin//00-INBOX/ 的链接误报为断链
broken = L.check_broken_links(notes, extra_slugs=L._all_vault_slugs())
no_fm, no_tags, no_summary, weak_tags = L.check_frontmatter(notes)


def pack(slug, extra=None):
    n = notes.get(slug, {})
    d = {
        'slug': slug,
        'title': n.get('title', ''),
        'path': n.get('path', ''),
        'body_chars': n.get('body_chars', 0),
        'n_tags': len(n.get('tags', []) or []),
        'n_summary': len(n.get('summary', []) or []),
    }
    if extra:
        d.update(extra)
    return d


data = {
    'summary': {
        'total_notes': len(notes),
        'orphans': len(orphans),
        'broken': len(broken),
        'no_fm': len(no_fm),
        'no_tags': len(no_tags),
        'no_summary': len(no_summary),
        'weak_tags': len(weak_tags),
    },
    'broken': [{'src': s, 'target': t} for s, t in broken],
    'no_fm': [pack(s) for s, _ in no_fm],
    'no_tags': [pack(s) for s, _ in no_tags],
    'no_summary': [pack(s) for s, _ in no_summary],
    'weak_tags': [pack(s, {'n_tags': c}) for s, c, _ in weak_tags],
    'orphans': [pack(s) for s in orphans],
}
json.dump(data, open(OUT, 'w'), ensure_ascii=False, indent=1)

print('=== 巡检完整清单 ===')
print(json.dumps(data['summary'], ensure_ascii=False, indent=1))
print(f"\n已写 {OUT}")

# 构建待修清单：并集，排除边缘态
union, reasons, marginal = {}, {}, []
for cat in ('no_fm', 'no_tags', 'no_summary', 'weak_tags'):
    for x in data[cat]:
        if x['body_chars'] < MIN_BODY:
            marginal.append((x['slug'], x['body_chars'], cat))
            continue
        union.setdefault(x['slug'], x)
        reasons.setdefault(x['slug'], set()).add(cat)

print(f"\n=== 待修 {len(union)} 篇（正文 ≥{MIN_BODY}B）===")
for s in sorted(union):
    print(f"  [{','.join(sorted(reasons[s])):26s}] {union[s]['body_chars']:7d}B  {s}")
print(f"\n=== 边缘态不修 {len(marginal)} 篇（正文 <{MIN_BODY}B）===")
for s, bc, cat in marginal:
    print(f"  {bc:5d}B  {s}")

# 给批量增强用的纯文件清单
json.dump({'files': sorted(union), 'reasons': {k: sorted(v) for k, v in reasons.items()}},
          open('/opt/data/.tmp_tests/vault_fixlist.json', 'w'), ensure_ascii=False, indent=1)
print('\n待修文件清单 → /opt/data/.tmp_tests/vault_fixlist.json')

# 断链详情（必须修到 0）
if data['broken']:
    print('\n=== 🚨 断链（必须修到 0）===')
    for x in data['broken']:
        print(f"  {x['src']} → [[{x['target']}]]")

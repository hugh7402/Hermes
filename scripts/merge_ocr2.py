"""合并 OCR 结果 v2：正文按页序分段，进度行仅用于确认页数"""
import re, json

parts = [
    ('/tmp/ocr_p1.txt', 0, 15),   # 页 1-15 (0-based 0..14)
    ('/tmp/ocr_p2.txt', 15, 30),  # 页 16-30
    ('/tmp/ocr_p3.txt', 30, 45),  # 页 31-45
    ('/tmp/ocr_p4.txt', 45, 57),  # 页 46-57
]

pages = {}
for path, start, end in parts:
    content = open(path, encoding='utf-8').read()
    # 找正文起点：跳过头部进度行（📸 开头或 缩进"第 N/57 页..."）
    lines = content.split('\n')
    body_start = None
    for idx, line in enumerate(lines):
        s = line.strip()
        if not s:
            continue
        if s.startswith('📸') or re.match(r'^第 \d+/57 页', s):
            continue
        body_start = idx
        break
    body = '\n'.join(lines[body_start:]).strip() if body_start is not None else ''
    # 按 --- 分隔段落
    segs = [s.strip() for s in re.split(r'\n\s*---\s*\n', body) if s.strip()]
    n_expected = end - start
    if len(segs) != n_expected:
        print(f'⚠️ {path}: 段落数 {len(segs)} != 预期 {n_expected}')
        # 退而求其次：逐段对应
    for k, seg in enumerate(segs):
        page_no = start + k + 1  # 1-based
        pages[page_no] = seg

# 覆盖补录页
retry = json.load(open('/tmp/ocr_retry.json', encoding='utf-8'))
for pg, text in retry.items():
    pages[int(pg)] = text.strip()

missing = [i for i in range(1, 58) if i not in pages]
empty = [i for i in range(1, 58) if not pages.get(i, '').strip()]
final_parts = []
for i in range(1, 58):
    t = pages.get(i, '').strip()
    if not t:
        t = f'[第 {i} 页：OCR 失败]'
    final_parts.append(t)

out = '/tmp/embodied_full.txt'
open(out, 'w', encoding='utf-8').write('\n\n---\n\n'.join(final_parts))
print(f'总页数: 57, 缺失: {missing or "无"}, 空页: {empty or "无"}')
print(f'总字数: {sum(len(p) for p in final_parts)}')
print(f'输出: {out}')

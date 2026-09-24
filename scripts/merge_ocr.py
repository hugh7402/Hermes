import re

parts = ['/tmp/ocr_p1.txt', '/tmp/ocr_p2.txt', '/tmp/ocr_p3.txt', '/tmp/ocr_p4.txt']
all_text = []
failed = []
total_ok = 0

for p in parts:
    content = open(p, encoding='utf-8').read()
    # 统计成功页
    total_ok += len(re.findall(r'✓', content))
    # 提取失败页标记
    for m in re.finditer(r'\[第 (\d+) 页 OCR 失败[^\]]*\]', content):
        failed.append((m.group(1), m.group(0)))
    # 取正文：从第一行开始到 EXIT= 之前，去掉进度行
    body_lines = []
    for line in content.split('\n'):
        line = line.strip()
        if not line:
            continue
        if line.startswith('📸') or line.startswith('📄') or line.startswith('第 ') or line.startswith('P'):
            continue
        if 'EXIT=' in line:
            break
        body_lines.append(line)
    all_text.append('\n'.join(body_lines))

merged = '\n\n---\n\n'.join(t for t in all_text if t.strip())

out = '/tmp/embodied_final.txt'
open(out, 'w', encoding='utf-8').write(merged)
print(f'成功页: {total_ok}/57')
print(f'失败页: {len(failed)}')
for pg, msg in failed:
    print(f'  {pg}: {msg[:80]}')
print(f'正文总字数: {len(merged)}')
print(f'输出: {out}')

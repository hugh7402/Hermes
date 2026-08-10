#!/usr/bin/env python3
"""独立校验：对比文档目录与 .ingested 日志，找出未处理文件"""
import hashlib
from pathlib import Path

BACKUP = Path('/opt/data/WebChat BackUp/文档')
LOG = Path('/opt/data/Obsidian Vault/Obsidian Vault/.ingested')

log = set(l.strip() for l in LOG.read_text(encoding='utf-8').splitlines() if l.strip())
print('日志哈希数(去空行):', len(log))

docs = sorted(f for f in BACKUP.rglob('*')
              if f.is_file() and f.suffix.lower() in ['.docx', '.pdf', '.pptx', '.xls', '.xlsx'])
print('文档总数:', len(docs))

unprocessed = []
for f in docs:
    h = hashlib.md5(f.read_bytes()).hexdigest()
    if h not in log:
        unprocessed.append(f)

print('未处理数:', len(unprocessed))
for f in unprocessed[:30]:
    print(' -', f.name, f'({f.stat().st_size/1024/1024:.1f} MB)')

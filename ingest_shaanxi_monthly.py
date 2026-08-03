"""陕西智慧民政一体化平台月度报告2026年7月 — MarkItDown 重新入库"""
import hashlib, re, os, sys
from pathlib import Path
from datetime import datetime

fp = "/opt/data/WebChat BackUp/文档/陕西智慧民政一体化平台月度报告2026年7月份.pdf"
VAULT = "/opt/data/Obsidian Vault/Obsidian Vault"
CONCEPTS = f"{VAULT}/concepts"
PROCESSED_LOG = f"{VAULT}/.ingested"

# ① MarkItDown 转换
print("① MarkItDown 转换...", flush=True)
from markitdown import MarkItDown
md = MarkItDown()
text = md.convert(fp).text_content
print(f"   提取 {len(text)} 字符", flush=True)

# ② 标题提取
first_line = next((l.strip() for l in text.splitlines() if l.strip()), "")
title = re.sub(r'^[#\s|]+', '', first_line).strip()
title = title.replace('|', '').strip()
if not title or len(title) > 60 or '2026' not in title:
    title = "陕西智慧民政一体化平台月度报告（2026年7月）"
print(f"   标题: {title}", flush=True)

# ③ 保存 md
safe = "陕西智慧民政一体化平台月度报告2026年7月.md"
content = f"# {title}\n\n> **原始文件**：{Path(fp).name}\n> **MarkItDown转换**：{datetime.now().strftime('%Y-%m-%d %H:%M')}（{len(text)}字符）\n\n---\n\n{text}\n"
Path(CONCEPTS, safe).write_text(content, encoding='utf-8')
print(f"③ md已保存: {safe} ({len(content)}字符)", flush=True)

# ④ 标记已处理
h = hashlib.md5(Path(fp).read_bytes()).hexdigest()
with open(PROCESSED_LOG, 'a') as f:
    f.write(f"{h}\n")
print(f"④ 已标记处理: {h[:12]}...", flush=True)
print("DONE", flush=True)

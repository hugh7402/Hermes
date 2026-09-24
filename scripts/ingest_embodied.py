"""手动入库：20260819_具身智能训练场研究报告2026年发布.pdf 的 OCR 结果"""
import os, re, subprocess, hashlib
from pathlib import Path
from datetime import datetime

VAULT = "/opt/data/Obsidian Vault/Obsidian Vault"
CONCEPTS = f"{VAULT}/concepts"
PROCESSED_LOG = f"{VAULT}/.ingested"
SRC_PDF = "/opt/data/WebChat BackUp/文档/20260819_具身智能训练场研究报告2026年发布.pdf"

text = open('/tmp/embodied_clean.txt', encoding='utf-8').read().strip()

# ---- 1. save_note 逻辑（与 ingest_docs.py 一致）----
filename = Path(SRC_PDF).name
safe_name = filename.replace(' ', '-').replace('/', '-')[:80]
path = os.path.join(CONCEPTS, safe_name)

source_line = f"> **原始文件**：{filename}"
has_h1 = any(line.startswith('# ') for line in text.split('\n'))
base_title = filename.rsplit('.', 1)[0]

if not has_h1:
    text = f"# {base_title}\n\n{source_line}\n\n---\n\n{text}"
else:
    lines = text.split('\n')
    for i, line in enumerate(lines):
        if line.startswith('# '):
            lines.insert(i+1, '')
            lines.insert(i+2, source_line)
            lines.insert(i+3, '')
            lines.insert(i+4, '---')
            break
    text = '\n'.join(lines)

Path(path).write_text(text, encoding='utf-8')
print(f"✅ 已保存: {path}")

# ---- 2. note_enhance ----
print("🤖 增强...")
r = subprocess.run(['python3', '/opt/data/note_enhance.py', Path(path).name],
                   cwd=CONCEPTS, timeout=300, capture_output=True, text=True)
print(r.stdout[-800:] if r.stdout else f"⚠️ 增强输出为空: {r.stderr[-300:]}")

# ---- 3. mark_processed ----
h = hashlib.md5(Path(SRC_PDF).read_bytes()).hexdigest()
processed = set()
if os.path.exists(PROCESSED_LOG):
    processed = set(open(PROCESSED_LOG).read().split())
if h not in processed:
    with open(PROCESSED_LOG, 'a') as f:
        f.write(f"{h}\n")
    print(f"✅ 已标记处理: {h}")
else:
    print("已存在标记")

# ---- 4. 更新 index.md ----
index_path = os.path.join(VAULT, 'index.md')
content = Path(index_path).read_text(encoding='utf-8')
entry = f"- [[{base_title}]] — 自动摄入"
if entry not in content:
    marker = '## 实体'
    content = content.replace(marker, f'{entry}\n\n{marker}')
    total = len(list(Path(CONCEPTS).glob('*.md')))
    content = re.sub(r'共 \d+ 页', f'共 {total} 页', content)
    content = re.sub(r'更新：\d{4}-\d{2}-\d{2}', f'更新：{datetime.now().strftime("%Y-%m-%d")}', content)
    Path(index_path).write_text(content, encoding='utf-8')
    print("✅ index.md 已更新")
else:
    print("index.md 已有该条目")

# ---- 5. 更新 log.md ----
log_path = os.path.join(VAULT, 'log.md')
today = datetime.now().strftime('%Y-%m-%d')
with open(log_path, 'a') as f:
    f.write(f"\n## [{today}] ingest | 自动入库 1 篇（OCR重试）\n- {filename}\n")
print("✅ log.md 已更新")

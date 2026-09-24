#!/bin/bash
# 批量重新增强：OCR 相关文件（328个）全部重跑 note_enhance（覆盖旧 frontmatter）
cd /opt/data
CONCEPTS="/opt/data/Obsidian Vault/Obsidian Vault/concepts"
LOG="/opt/data/enhance_rerun.log"

# 重新生成清单（用 scan report SUSPECT 匹配）
python3 - <<'EOF'
import os, csv, re
from pathlib import Path
CONCEPTS = "/opt/data/Obsidian Vault/Obsidian Vault/concepts"

def norm(s):
    s = re.sub(r'^[\d一二三四五六七八九十百]+[\.、]?\s*', '', s)
    s = s.replace('（','(').replace('）',')')
    s = re.sub(r'[《》"\' ]', '', s)
    s = re.sub(r'[\s\-_—–]+', '', s)
    return s

all_md = {norm(Path(f).stem): f for f in os.listdir(CONCEPTS) if f.endswith('.md')}
rows = list(csv.reader(open('/tmp/pdf_scan_report.csv')))
suspects = [r[0] for r in rows[1:] if r[5] == 'SUSPECT' and r[2] != '-1']
matched = []
for s in suspects:
    n = norm(Path(s).stem)
    md = all_md.get(n)
    if not md:
        for k, v in all_md.items():
            if len(n) >= 6 and (n in k or k in n):
                md = v
                break
    if md and md not in matched:
        matched.append(md)
Path("/tmp/ocr_rerun_enhance.txt").write_text("\n".join(sorted(matched)), encoding="utf-8")
print(f"待重新增强: {len(matched)} 个")
EOF

# 分批跑（每 8 个暂停 8s；日志落 /opt/data）
BATCH=8
COUNT=0
: > "$LOG"
while read -r fname; do
    [ -z "$fname" ] && continue
    COUNT=$((COUNT+1))
    echo "── 第 $COUNT 个: $fname ($(date '+%H:%M:%S'))" >> "$LOG"
    timeout 120 python3 /opt/data/note_enhance.py "$fname" >> "$LOG" 2>&1
    if [ $((COUNT % BATCH)) -eq 0 ]; then
        echo "── 已处理 $COUNT 个，暂停 8s" >> "$LOG"
        sleep 8
    fi
done < /tmp/ocr_rerun_enhance.txt

echo "✅ 全部完成，共处理 $COUNT 个 ($(date '+%H:%M:%S'))" >> "$LOG"

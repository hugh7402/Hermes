#!/bin/bash
# 批量增强：对无 frontmatter 的 md 跑 note_enhance.py（全部，含短文档）
cd /opt/data
CONCEPTS="/opt/data/Obsidian Vault/Obsidian Vault/concepts"

# 生成全量待增强清单（无 frontmatter 的全部 md）
python3 - <<'EOF'
import os
from pathlib import Path
CONCEPTS = "/opt/data/Obsidian Vault/Obsidian Vault/concepts"
targets = []
for f in sorted(os.listdir(CONCEPTS)):
    if not f.endswith('.md'): continue
    p = os.path.join(CONCEPTS, f)
    try:
        head = open(p, encoding='utf-8').read(200)
    except: continue
    if not head.startswith('---'):
        targets.append(f)
Path("/tmp/enhance_all.txt").write_text("\n".join(targets), encoding="utf-8")
print(f"待增强: {len(targets)} 个")
EOF

# 分批跑（每 8 个暂停 8s，控制速率；日志落 /opt/data 防 /tmp 清空）
BATCH=8
COUNT=0
LOG="/opt/data/enhance_run.log"
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
done < /tmp/enhance_all.txt

echo "✅ 全部完成，共处理 $COUNT 个 ($(date '+%H:%M:%S'))" >> "$LOG"

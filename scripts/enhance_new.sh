#!/bin/bash
# 补增强：扫描 concepts/ 中缺少 tags 的笔记，调用 note_enhance
cd "/opt/data/Obsidian Vault/Obsidian Vault/concepts"
for f in *.md; do
    # 检查是否有 frontmatter tags
    has_tags=$(head -30 "$f" | grep -c "^  - " 2>/dev/null)
    if [ "$has_tags" -lt 5 ]; then
        echo "🤖 $f"
        python3 /opt/data/note_enhance.py "$f" 2>/dev/null
    fi
done
echo "✅ 补增强完成"

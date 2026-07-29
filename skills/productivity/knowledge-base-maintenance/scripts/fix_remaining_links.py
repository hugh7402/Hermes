"""
修复剩余断链：高引用建笔记，低引用移除 wikilink
"""
import re, os, yaml
from pathlib import Path
from collections import Counter

VAULT = "/opt/data/Obsidian Vault/Obsidian Vault"
CONCEPTS = Path(f"{VAULT}/concepts")

def main():
    all_slugs = set()
    for f in CONCEPTS.glob("*.md"):
        all_slugs.add(f.stem)

    broken = Counter()
    for f in CONCEPTS.glob("*.md"):
        c = f.read_text(encoding='utf-8')
        links = re.findall(r'\[\[([^\]|#]+)', c)
        for link in links:
            if link not in all_slugs and len(link) < 80:
                broken[link] += 1

    print(f"断链总数: {len(broken)} 处\n")

    need_creation = [(t, c) for t, c in broken.most_common() if c >= 3]
    need_removal = [(t, c) for t, c in broken.most_common() if c < 3]

    print("--- 高引用（建议建笔记）---")
    for t, c in need_creation:
        print(f"  [[{t}]] — 被 {c} 篇引用")

    print("\n--- 低引用（移除 wikilink）---")
    for t, c in need_removal:
        print(f"  [[{t}]] — 被 {c} 篇引用")

    # 移除低引用 wikilink
    if need_removal:
        targets_remove = [t for t, _ in need_removal]
        fixed_files = 0
        for f in CONCEPTS.glob("*.md"):
            c = f.read_text(encoding='utf-8')
            changed = False
            for target in targets_remove:
                pattern = f'\\[\\[{re.escape(target)}\\]\\]'
                count = len(re.findall(pattern, c))
                if count > 0:
                    c = re.sub(pattern, target, c)
                    changed = True
            if changed:
                f.write_text(c, encoding='utf-8')
                fixed_files += 1
        print(f"\n✅ 移除了 {len(targets_remove)} 个断链目标的引用（涉及 {fixed_files} 篇笔记）")

    # 创建高引用笔记
    if need_creation:
        first_target = need_creation[0][0]
        slug = first_target.replace(' ', '-').replace('/', '-')
        note_path = CONCEPTS / f"{slug}.md"
        if not note_path.exists():
            fm = f"""---
title: "{first_target}"
date: "2026/07/01"
source: "知识库运维"
tags:
  - 待分类
summary:
  - "待补充摘要"
related: []
---
# {first_target}

> 此笔记由知识库自动创建（{need_creation[0][1]} 篇其他笔记引用此页面）。
> 请补充具体内容。
"""
            note_path.write_text(fm, encoding='utf-8')
            print(f"\n✅ 创建笔记: [[{first_target}]]")

if __name__ == '__main__':
    main()

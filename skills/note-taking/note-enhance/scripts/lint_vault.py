"""
知识库健康巡检脚本
检查：孤立页面、断链、frontmatter 完整度、标签覆盖率、标签统计

用法：cd /opt/data && uv run --with pyyaml python3 lint_vault.py
"""
import os, re, yaml
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime

VAULT = "/opt/data/Obsidian Vault/Obsidian Vault"
CONCEPTS = f"{VAULT}/concepts"
NOW = datetime.now().strftime("%Y-%m-%d %H:%M")

def parse_frontmatter(content):
    fm = {}
    body_start = 0
    if content.startswith('---'):
        end = content.find('---', 3)
        if end > 0:
            try:
                fm = yaml.safe_load(content[3:end]) or {}
            except:
                pass
            body_start = len(content[:end+4].split('\n'))
    return fm, body_start

def scan_all_notes():
    notes = {}
    for md_file in Path(CONCEPTS).glob("*.md"):
        slug = md_file.stem
        try:
            content = md_file.read_text(encoding='utf-8')
        except:
            continue
        lines = content.split('\n')
        fm, body_start = parse_frontmatter(content)
        body = '\n'.join(lines[body_start:])
        
        body_links = re.findall(r'\[\[([^\]|#]+)', body)
        related_raw = fm.get('related', [])
        fm_links = []
        for r in related_raw:
            m = re.search(r'\[\[([^\]|#]+)', str(r))
            if m:
                fm_links.append(m.group(1))
        
        notes[slug] = {
            'title': fm.get('title', ''),
            'date': fm.get('date', ''),
            'tags': fm.get('tags', []),
            'summary': fm.get('summary', []),
            'outgoing_links': body_links + fm_links,
            'has_frontmatter': bool(fm),
        }
    return notes

def check_orphans(notes):
    inbound = defaultdict(set)
    for slug, note in notes.items():
        for target in note['outgoing_links']:
            inbound[target].add(slug)
    return [s for s in notes if s not in inbound]

def check_broken_links(notes):
    all_slugs = set(notes.keys())
    broken = []
    for slug, note in notes.items():
        for target in note['outgoing_links']:
            if target not in all_slugs and len(target) < 80:
                broken.append((slug, target))
    return broken

def check_frontmatter(notes):
    no_fm, no_tags, no_summary, weak_tags = [], [], [], []
    for slug, note in notes.items():
        if not note['has_frontmatter']:
            no_fm.append((slug, note['title']))
            continue
        if not note['tags']:
            no_tags.append((slug, note['title']))
        elif len(note['tags']) < 8:
            weak_tags.append((slug, len(note['tags']), note['title']))
        if not note['summary']:
            no_summary.append((slug, note['title']))
    return no_fm, no_tags, no_summary, weak_tags

def check_tag_stats(notes):
    tag_counter = Counter()
    for note in notes.values():
        for tag in note['tags']:
            tag_counter[tag] += 1
    return tag_counter.most_common(30)

def main():
    notes = scan_all_notes()
    print(f"# 知识库健康巡检报告")
    print(f"**巡检时间：** {NOW}")
    print(f"**笔记总数：** {len(notes)} 篇\n")
    
    orphans = check_orphans(notes)
    broken = check_broken_links(notes)
    no_fm, no_tags, no_summary, weak_tags = check_frontmatter(notes)
    tags = check_tag_stats(notes)
    
    print(f"## 断链：{len(broken)} 处")
    for src, target in broken[:10]:
        print(f"- {src} → [[{target}]]")
    if len(broken) > 10:
        print(f"  ...还有 {len(broken)-10} 处")
    
    print(f"\n## 无 Frontmatter：{len(no_fm)} 篇")
    for slug, title in no_fm[:10]:
        print(f"- {title or slug}")
    
    print(f"\n## 孤立页面：{len(orphans)} 篇")
    print(f"\n## 无标签：{len(no_tags)} | 无摘要：{len(no_summary)} | 标签不足：{len(weak_tags)}")
    
    print(f"\n## Top 20 标签")
    for tag, count in tags[:20]:
        print(f"- {tag}：{count} 篇")
    
    total = len(broken) + len(no_fm) + len(orphans) + len(no_tags) + len(no_summary)
    print(f"\n---\n**总问题：{total}**")

if __name__ == '__main__':
    main()

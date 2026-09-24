"""
知识库健康巡检脚本 v2
修正：入链检查含 frontmatter related 字段、Index 检查修复
"""
import os, re, yaml
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime

VAULT = "/opt/data/Obsidian Vault/Obsidian Vault"
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
    for md_file in Path(VAULT).glob("concepts/*.md"):
        slug = md_file.stem
        try:
            content = md_file.read_text(encoding='utf-8')
        except:
            continue
        lines = content.split('\n')
        fm, body_start = parse_frontmatter(content)
        body = '\n'.join(lines[body_start:])
        
        # wikilinks in body
        body_links = re.findall(r'\[\[([^\]|#]+)', body)
        # wikilinks in frontmatter related
        related_raw = fm.get('related', [])
        fm_links = []
        for r in related_raw:
            m = re.search(r'\[\[([^\]|#]+)', str(r))
            if m:
                fm_links.append(m.group(1))
        
        notes[slug] = {
            'path': str(md_file),
            'title': fm.get('title', ''),
            'date': fm.get('date', ''),
            'tags': fm.get('tags', []),
            'related': fm_links,
            'summary': fm.get('summary', []),
            'source': fm.get('source', ''),
            'body_chars': len(body),
            'lines': len(lines),
            'outgoing_links': body_links + fm_links,
            'has_frontmatter': bool(fm),
        }
    return notes

def check_orphans(notes):
    inbound = defaultdict(set)
    for slug, note in notes.items():
        for target in note['outgoing_links']:
            inbound[target].add(slug)
    orphans = [s for s in notes if s not in inbound]
    return orphans

def check_broken_links(notes):
    all_slugs = set(notes.keys())
    broken = []
    for slug, note in notes.items():
        for target in note['outgoing_links']:
            if target not in all_slugs and len(target) < 80:
                broken.append((slug, target))
    return broken

def check_frontmatter(notes):
    no_fm = []
    no_tags = []
    no_summary = []
    weak_tags = []
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
    
    # 1. 孤立页面
    orphans = check_orphans(notes)
    print(f"## 📌 孤立页面（零入链）：{len(orphans)} 篇\n")
    if orphans:
        for slug in orphans[:5]:
            n = notes[slug]
            print(f"- [[{n['title'] or slug}]]")
        if len(orphans) > 5:
            print(f"\n*...还有 {len(orphans)-5} 篇*\n")
    
    # 2. 断链
    broken = check_broken_links(notes)
    print(f"\n## 🔗 断链：{len(broken)} 处\n")
    for src, target in broken:
        print(f"- `{src}` → `[[{target}]]`（页面不存在）")
    
    # 3. Frontmatter
    no_fm, no_tags, no_summary, weak_tags = check_frontmatter(notes)
    print(f"\n## 📝 缺少 Frontmatter：{len(no_fm)} 篇\n")
    for slug, title in no_fm:
        print(f"- {title or slug}")
    print(f"\n## 🏷️ 无标签：{len(no_tags)} 篇\n")
    for slug, title in no_tags[:5]:
        print(f"- {title or slug}")
    if len(no_tags) > 5:
        print(f"\n*...还有 {len(no_tags)-5} 篇*\n")
    print(f"\n## 🏷️ 标签不足（<8个）：{len(weak_tags)} 篇\n")
    for slug, count, title in weak_tags[:10]:
        print(f"- {title or slug}（{count}个）")
    if len(weak_tags) > 10:
        print(f"\n*...还有 {len(weak_tags)-10} 篇*\n")
    print(f"\n## 📄 无摘要：{len(no_summary)} 篇\n")
    for slug, title in no_summary[:5]:
        print(f"- {title or slug}")
    if len(no_summary) > 5:
        print(f"\n*...还有 {len(no_summary)-5} 篇*\n")
    
    # 4. 标签统计
    tags = check_tag_stats(notes)
    print(f"\n## 🏷️ Top 30 标签\n")
    for tag, count in tags:
        print(f"- `{tag}`：{count} 篇")
    
    # 5. 汇总
    total = len(orphans) + len(broken) + len(no_fm) + len(no_tags) + len(no_summary)
    print(f"\n---\n")
    print(f"## 📊 总览\n")
    print(f"| 维度 | 数量 | 严重度 |")
    print(f"|------|------|--------|")
    print(f"| 🔗 断链 | {len(broken)} | {'🔴 高' if broken else '✅'} |")
    print(f"| 📝 无 Frontmatter | {len(no_fm)} | {'🔴 高' if no_fm else '✅'} |")
    print(f"| 🏷️ 无标签 | {len(no_tags)} | {'🔴 高' if no_tags else '✅'} |")
    print(f"| 📄 无摘要 | {len(no_summary)} | {'🟡 中' if no_summary else '✅'} |")
    print(f"| 📌 孤立页面 | {len(orphans)} | {'🟡 中' if orphans else '✅'} |")
    print(f"| 🏷️ 标签不足 | {len(weak_tags)} | {'🟢 低' if weak_tags else '✅'} |")
    print(f"\n**总问题：{total}**")

if __name__ == '__main__':
    main()

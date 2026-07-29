"""
修复 knowledge vault 中的断链
1. 建立 标题→slug 映射
2. 将 related 字段的 [[标题]] 替换为 [[slug]]
3. 修复缺失 frontmatter 的笔记

用法：cd /opt/data && uv run --with pyyaml python3 fix_links.py
"""
import os, re, yaml
from pathlib import Path
from collections import defaultdict

VAULT = "/opt/data/Obsidian Vault/Obsidian Vault"
CONCEPTS = f"{VAULT}/concepts"

def parse_frontmatter(content):
    fm = {}
    fm_end = 0
    if content.startswith('---'):
        end = content.find('---', 3)
        if end > 0:
            try:
                fm = yaml.safe_load(content[3:end]) or {}
            except:
                pass
            fm_end = end + 3
    return fm, fm_end

def build_title_map():
    title_to_slug = {}
    slug_to_title = {}
    for md_file in Path(CONCEPTS).glob("*.md"):
        slug = md_file.stem
        try:
            content = md_file.read_text(encoding='utf-8')
        except:
            continue
        fm, _ = parse_frontmatter(content)
        title = fm.get('title', '')
        if title:
            title_to_slug[title] = slug
            clean = title.strip().replace(' ', '-').replace('/', '-')
            title_to_slug[clean] = slug
        slug_to_title[slug] = title
    return title_to_slug, slug_to_title

def fix_related_link(wikilink_text, title_to_slug, all_slugs):
    main = wikilink_text.split('#')[0].strip()
    heading = wikilink_text[len(main):]
    
    if main in title_to_slug:
        return title_to_slug[main] + heading
    if main in all_slugs:
        return main + heading
    
    slugified = main.replace(' ', '-').replace('/', '-').replace('（', '(').replace('）', ')')
    if slugified in title_to_slug:
        return title_to_slug[slugified] + heading
    
    for slug in all_slugs:
        if main in slug or slug in main:
            return slug + heading
    
    no_space = main.replace(' ', '')
    for slug in all_slugs:
        if no_space in slug.replace(' ', '') or slug.replace(' ', '') in no_space:
            return slug + heading
    
    return None

def main():
    title_to_slug, slug_to_title = build_title_map()
    all_slugs = set(slug_to_title.keys())
    
    fixed_files = 0
    total_fixes = 0
    still_broken = 0
    missing_fm_fixed = 0
    
    for md_file in sorted(Path(CONCEPTS).glob("*.md")):
        slug = md_file.stem
        try:
            content = md_file.read_text(encoding='utf-8')
        except:
            continue
        
        fm, fm_end = parse_frontmatter(content)
        body = content[fm_end:]
        
        if not fm:
            title = slug
            for line in body.split('\n'):
                if line.startswith('# '):
                    title = line[2:].strip()
                    break
            new_fm = f"""---
title: \"{title}\"
date: \"2026/06/17\"
source: \"自动入库\"
tags:\n  - 待分类\nsummary:\n  - \"待补充摘要 ×\"\nrelated: []\n---
"""
            content = new_fm + body
            md_file.write_text(content, encoding='utf-8')
            print(f"+ 补全 frontmatter: {slug}")
            missing_fm_fixed += 1
            continue
        
        related = fm.get('related', [])
        if not related:
            continue
        
        new_related = []
        file_changed = False
        
        for item in related:
            m = re.search(r'\[\[([^\]]+)\]\]', str(item))
            if not m:
                new_related.append(item)
                continue
            
            original = m.group(1)
            fixed = fix_related_link(original, title_to_slug, all_slugs)
            
            if fixed and fixed != original:
                new_item = str(item).replace(f'[[{original}]]', f'[[{fixed}]]')
                new_related.append(new_item)
                file_changed = True
                total_fixes += 1
            elif fixed:
                new_related.append(item)
            else:
                new_related.append(item)
                still_broken += 1
        
        if file_changed:
            new_fm_block = yaml.dump(
                {k: v for k, v in fm.items() if k != 'related'},
                allow_unicode=True, default_flow_style=False, sort_keys=False
            )
            new_fm_block += 'related:\n'
            for r in new_related:
                new_fm_block += f'  - {r}\n'
            
            new_content = f'---\n{new_fm_block}---\n{body}'
            md_file.write_text(new_content, encoding='utf-8')
            fixed_files += 1
    
    print(f"\n修复断链：{total_fixes} 处（涉及 {fixed_files} 个文件）")
    print(f"补全 Frontmatter：{missing_fm_fixed} 篇")
    print(f"仍无法匹配：{still_broken} 处")

if __name__ == '__main__':
    main()

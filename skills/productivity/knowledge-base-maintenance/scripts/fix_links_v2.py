"""
修复知识库断链 v2 - 纯文本替换，不碰 YAML 解析
原理：直接读取 frontmatter 原始文本，
      将 [[不存在的wikilink]] 替换为 [[正确的slug]]
"""
import re, os
from pathlib import Path
from collections import defaultdict

VAULT = "/opt/data/Obsidian Vault/Obsidian Vault"
CONCEPTS = f"{VAULT}/concepts"

def build_slug_map():
    """建立 标题的各种变体 → slug 的映射"""
    map_variants = {}
    all_slugs = set()

    for md_file in sorted(Path(CONCEPTS).glob("*.md")):
        slug = md_file.stem
        all_slugs.add(slug)
        map_variants[slug] = slug
        clean = slug.replace('--', '-').replace(' -', '-').replace('- ', '-')
        if clean != slug:
            map_variants[clean] = slug
        no_space = slug.replace(' ', '')
        map_variants[no_space] = slug

        try:
            content = md_file.read_text(encoding='utf-8')
        except:
            continue
        m = re.search(r'^title:\s*"(.+?)"', content, re.MULTILINE)
        if m:
            title = m.group(1)
            map_variants[title] = slug
            clean_t = title.replace('--', '-').replace(' -', '-').replace('- ', '-')
            if clean_t != title:
                map_variants[clean_t] = slug
            space_t = title.replace(' ', '')
            map_variants[space_t] = slug

    return map_variants, all_slugs

def find_correct_slug(wikilink_text, slug_map, all_slugs):
    main = wikilink_text.split('#')[0].strip()
    if main in slug_map:
        return slug_map[main]
    if main in all_slugs:
        return main
    clean = re.sub(r'[\s\-—–]+', '-', main).strip('-')
    if clean in slug_map:
        return slug_map[clean]
    nos = main.replace(' ', '').replace('\u3000', '')
    if nos in slug_map:
        return slug_map[nos]
    candidates = []
    for slug in all_slugs:
        if len(main) >= 6 and len(slug) >= 6:
            common = longest_common_substr(main, slug)
            if common >= min(len(main), len(slug)) * 0.6:
                candidates.append((common, slug))
    if candidates:
        candidates.sort(key=lambda x: -x[0])
        return candidates[0][1]
    return None

def longest_common_substr(a, b):
    m, n = len(a), len(b)
    dp = [[0]*(n+1) for _ in range(m+1)]
    max_len = 0
    for i in range(1, m+1):
        for j in range(1, n+1):
            if a[i-1] == b[j-1]:
                dp[i][j] = dp[i-1][j-1] + 1
                max_len = max(max_len, dp[i][j])
    return max_len

def main():
    slug_map, all_slugs = build_slug_map()
    print(f"Slug 映射：{len(slug_map)} 条")
    print(f"Slug 总数：{len(all_slugs)} 个\n")

    fixed = 0
    still_broken = 0
    fixed_files = set()
    sample_broken = []

    for md_file in sorted(Path(CONCEPTS).glob("*.md")):
        try:
            content = md_file.read_text(encoding='utf-8')
        except:
            continue
        if not content.startswith('---'):
            continue
        lines = content.split('\n')
        fm_end = 0
        for i in range(1, len(lines)):
            if lines[i].rstrip() == '---':
                fm_end = sum(len(l) + 1 for l in lines[:i+1])
                break
        if fm_end == 0:
            continue
        frontmatter = content[:fm_end]

        links = re.findall(r'\[\[([^\]]+)\]\]', frontmatter)
        changed = False
        new_frontmatter = frontmatter

        for link in links:
            slug_candidate = link.split('#')[0].strip()
            if slug_candidate in all_slugs:
                continue
            correct = find_correct_slug(link, slug_map, all_slugs)
            if correct:
                new_frontmatter = new_frontmatter.replace(f'[[{link}]]', f'[[{correct}]]')
                fixed += 1
                changed = True
            else:
                still_broken += 1
                if len(sample_broken) < 20:
                    sample_broken.append((md_file.stem, link))

        if changed:
            new_content = new_frontmatter + content[fm_end:]
            md_file.write_text(new_content, encoding='utf-8')
            fixed_files.add(md_file.stem)

    print(f"## 修复结果")
    print(f"✅ 修复断链：{fixed} 处（涉及 {len(fixed_files)} 个文件）")
    print(f"⚠️ 仍无法匹配：{still_broken} 处")
    if sample_broken:
        print(f"\n### 仍无法匹配的示例：")
        for s, t in sample_broken[:20]:
            print(f"- {s} → [[{t}]]")

if __name__ == '__main__':
    main()

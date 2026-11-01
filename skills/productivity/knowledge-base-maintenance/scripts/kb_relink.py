#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""知识库链接修复：①主题索引页 ②反向补链

用法：
  python3 kb_relink.py --dry     只统计不改
  python3 kb_relink.py --apply   实际写入（先自动备份）
"""
import argparse
import re
import shutil
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

import yaml

VAULT = Path('/opt/data/Obsidian Vault/Obsidian Vault')
CONCEPTS = VAULT / 'concepts'
BACKUP_DIR = Path('/opt/data/.kb_backup')

FM_RE = re.compile(r'\A---\s*\n(.*?)\n---\s*\n', re.S)
LINK_RE = re.compile(r'\[\[([^\]|#\n]+?)(?:[|#][^\]]*)?\]\]')
MAX_BACKLINKS = 12          # 单篇最多补多少条反向链接，防枢纽页爆炸
MIN_GROUP = 5               # 索引页至少聚 5 篇才建
TAG_BLACKLIST = {'中国', '杭政秘', '无标签', 'doc', 'OCR', 'ocr'}


def load_notes():
    """返回 {stem: {path, fm_text, fm(dict|None), body, links(set), tags(list)}}"""
    notes = {}
    for p in sorted(CONCEPTS.glob('*.md')):
        try:
            txt = p.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            continue
        m = FM_RE.match(txt)
        fm_text, fm, body = '', None, txt
        if m:
            fm_text = m.group(1)
            body = txt[m.end():]
            try:
                fm = yaml.safe_load(fm_text) or {}
                if not isinstance(fm, dict):
                    fm = None
            except Exception:
                fm = None
        links = set()
        if fm:
            rel = fm.get('related') or []
            if isinstance(rel, str):
                rel = [rel]
            for r in rel:
                links |= {x.strip() for x in LINK_RE.findall(str(r))}
        # 正文里的链接也算（有些笔记写在正文）
        links |= {x.strip() for x in LINK_RE.findall(body)}
        tags = []
        if fm:
            t = fm.get('tags') or []
            if isinstance(t, str):
                t = [t]
            tags = [str(x).strip() for x in t if str(x).strip()]
        notes[p.stem] = {'path': p, 'fm_text': fm_text, 'fm': fm, 'body': body,
                         'links': links, 'tags': tags}
    return notes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--dry', action='store_true')
    args = ap.parse_args()
    apply = args.apply

    notes = load_notes()
    stems = set(notes)
    print(f'扫描 {len(notes)} 篇笔记')

    # 只保留指向真实笔记的链接
    valid = {}
    for s, n in notes.items():
        valid[s] = {l for l in n['links'] if l in stems and l != s}
    inbound = Counter()
    for s, ls in valid.items():
        for l in ls:
            inbound[l] += 1

    orphans = [s for s in notes if inbound[s] == 0]
    no_out = [s for s in orphans if not valid[s]]
    one_way = []   # (from, to) 需要反向补的
    for a, ls in valid.items():
        for b in ls:
            if a not in valid[b]:
                one_way.append((a, b))

    print(f'  孤立（零入链）: {len(orphans)}  其中完全孤立: {len(no_out)}')
    print(f'  单向链接对: {len(one_way)}')

    # ═══ 动作二：反向补链 ═══
    need_back = defaultdict(list)   # 目标笔记 -> [应回链的来源]
    for a, b in one_way:
        need_back[b].append(a)
    add_back = {}
    hub = []
    for b, srcs in need_back.items():
        srcs = sorted(set(srcs))
        if len(srcs) > MAX_BACKLINKS:
            hub.append((b, len(srcs)))
            srcs = srcs[:MAX_BACKLINKS]
        add_back[b] = srcs
    print(f'\n  动作二：需给 {len(add_back)} 篇补反向链接，共 {sum(len(v) for v in add_back.values())} 条')
    if hub:
        print(f'    跳过 {len(hub)} 个枢纽页（超过 {MAX_BACKLINKS} 条入链，补了会成噪音）:')
        for b, n in sorted(hub, key=lambda x: -x[1])[:5]:
            print(f'      {b[:44]} ← {n} 条')

    # ═══ 动作一：主题索引页 ═══
    # 两轮：先按每个标签统计孤立篇数，再让每篇归入"能命中的最大标签组"
    tag_count = Counter()
    for s in no_out:
        for t in notes[s]['tags']:
            if t not in TAG_BLACKLIST:
                tag_count[t] += 1
    big_tags = {t for t, n in tag_count.items() if n >= MIN_GROUP}
    groups = defaultdict(list)
    ungrouped = []
    for s in no_out:
        cand = [t for t in notes[s]['tags'] if t in big_tags]
        if cand:
            pick = max(cand, key=lambda t: tag_count[t])
            groups[pick].append(s)
        else:
            tg = [t for t in notes[s]['tags'] if t not in TAG_BLACKLIST]
            if tg:
                ungrouped.append(s)
    groups = {k: v for k, v in groups.items() if len(v) >= MIN_GROUP}
    covered = sum(len(v) for v in groups.values())
    print(f'\n  动作一：可建索引页 {len(groups)} 个，覆盖 {covered} / {len(no_out)} 篇完全孤立')
    print(f'    仍有 {len(ungrouped)} 篇标签过于零散，进不了索引（保留为孤立）')
    for k, v in sorted(groups.items(), key=lambda x: -len(x[1]))[:15]:
        print(f'    {k:16s} {len(v):>3} 篇')

    if not apply:
        print('\n[空跑] 未写入任何文件。加 --apply 执行。')
        return

    # ── 备份
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    tgt = BACKUP_DIR / f'concepts_{stamp}'
    shutil.copytree(CONCEPTS, tgt)
    print(f'\n已备份到 {tgt}')

    # ── 执行动作二
    written = 0
    failed = []
    for b, srcs in add_back.items():
        p = notes[b]['path']
        fm = notes[b]['fm']
        if fm is None:
            failed.append((b, '无 frontmatter 或 YAML 解析失败'))
            continue
        old = p.read_text(encoding='utf-8', errors='ignore')
        cur = fm.get('related') or []
        if isinstance(cur, str):
            cur = [cur]
        cur_list = [str(x) for x in cur]
        add = [f'"[[{s}]]"' for s in srcs]
        new_list = cur_list + add
        # 重建 related 段
        block = 'related:\n' + '\n'.join('  - ' + x for x in new_list)
        if notes[b]['fm_text'] and re.search(r'^related:', notes[b]['fm_text'], re.M):
            new_fm = re.sub(r'^related:\n(?:[ \t]+-[^\n]*\n?)*', block + '\n',
                            notes[b]['fm_text'], count=1, flags=re.M)
        else:
            new_fm = notes[b]['fm_text'].rstrip('\n') + '\n' + block
        new_txt = '---\n' + new_fm + '\n---\n' + notes[b]['body']
        try:
            m = FM_RE.match(new_txt)
            yaml.safe_load(m.group(1))
        except Exception as e:
            failed.append((b, f'YAML 校验失败: {e}'))
            continue
        p.write_text(new_txt, encoding='utf-8')
        written += 1
    print(f'\n动作二完成：写入 {written} 篇，失败 {len(failed)} 篇')
    for b, why in failed[:6]:
        print(f'  跳过 {b[:40]}: {why}')

    # ── 执行动作一
    made = []
    for tag, members in groups.items():
        fname = f'索引-{tag}.md'
        fpath = CONCEPTS / fname
        if fpath.exists():
            continue
        rel = '\n'.join(f'  - "[[{m}]]"' for m in sorted(members))
        body_lines = [f'# {tag} · 主题索引', '',
                      f'> 本篇由知识库巡检自动生成于 {datetime.now():%Y-%m-%d}，'
                      f'汇集标签为「{tag}」的 {len(members)} 篇笔记，用于把它们接入双向链接网络。', '',
                      '## 收录笔记', '']
        for m in sorted(members):
            body_lines.append(f'- [[{m}]]')
        body_lines += ['', '## 说明', '',
                       '这些笔记此前零入链，属于孤立页面。本索引是它们唯一的入链入口；'
                       '后续新增同类笔记时，直接补到上面的列表即可。']
        txt = ('---\n'
               f'title: "{tag} · 主题索引"\n'
               f'date: {datetime.now():%Y/%m/%d}\n'
               'tags:\n'
               f'  - 索引\n  - {tag}\n'
               'summary:\n'
               f'  - "「{tag}」主题下 {len(members)} 篇笔记的汇总入口 ×"\n'
               'related:\n'
               f'{rel}\n'
               '---\n\n' + '\n'.join(body_lines) + '\n')
        fpath.write_text(txt, encoding='utf-8')
        made.append((tag, len(members), fname))
    print(f'\n动作一完成：新建索引页 {len(made)} 个')
    for tag, n, f in made:
        print(f'  {f}  收录 {n} 篇')

    # ── 总索引
    if made:
        master = CONCEPTS / '00-知识库主题索引.md'
        rel = '\n'.join(f'  - "[[索引-{t}]]"' for t, _, _ in made)
        lines = ['# 知识库主题索引', '',
                 f'> 自动生成于 {datetime.now():%Y-%m-%d}。按标签聚类的入口页。', '',
                 '## 主题', '']
        for t, n, _ in made:
            lines.append(f'- [[索引-{t}]]（{n} 篇）')
        txt = ('---\n'
               'title: "知识库主题索引"\n'
               f'date: {datetime.now():%Y/%m/%d}\n'
               'tags:\n  - 索引\n  - 导航\n'
               'summary:\n  - "知识库所有主题索引页的汇总入口 ×"\n'
               'related:\n'
               f'{rel}\n'
               '---\n\n' + '\n'.join(lines) + '\n')
        master.write_text(txt, encoding='utf-8')
        print(f'\n总索引已生成: {master.name}')

    print(f'\n备份位置: {tgt}')


if __name__ == '__main__':
    main()

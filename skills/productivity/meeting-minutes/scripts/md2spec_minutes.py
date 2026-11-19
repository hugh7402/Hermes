#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""会议纪要 markdown → cn_docx.py 的 JSON spec

用法:
    python3 md2spec_minutes.py <纪要.md> <spec.json> [标题] [副标题]

然后:
    python3 skills/productivity/docx/scripts/cn_docx.py <spec.json> <输出.docx>

映射约定（对应 skill 的交付要求：黑体标题 / 仿宋正文 / 楷体排引述）:
    # 第一个        → title（spec 顶层）
    ##             → h1 黑体
    ###            → h2 黑体（小一号）
    > 引述          → p，楷体_GB2312（录音原话、领导讲话）
    - 列表          → p，前缀 ·
    | 表格 |        → table 块
    ---            → 丢弃（不是分隔线就是 frontmatter 围栏）
    行内 **加粗** / `代码` / [[双链]] → 去标记保留文字
"""
import json
import pathlib
import re
import sys


def deinline(s: str) -> str:
    """去掉 markdown 行内标记，保留文字"""
    s = re.sub(r'\*\*(.+?)\*\*', r'\1', s)
    s = re.sub(r'`(.+?)`', r'\1', s)
    s = re.sub(r'\[\[(.+?)\]\]', r'\1', s)
    s = re.sub(r'(?<!\*)\*(?!\*)', '', s)
    return s.strip()


def convert(src: pathlib.Path, spec_path: pathlib.Path,
            title: str = None, subtitle: str = None) -> dict:
    lines = src.read_text(encoding='utf-8').split('\n')
    blocks, md_title = [], None
    i, fm_done = 0, False

    while i < len(lines):
        s = lines[i].strip()

        # 跳过 frontmatter
        if not fm_done:
            if s == '---':
                if i == 0:
                    i += 1
                    while i < len(lines) and lines[i].strip() != '---':
                        i += 1
                    i += 1
                    fm_done = True
                    continue
            fm_done = True

        if not s:
            i += 1
            continue

        # 表格
        if s.startswith('|') and i + 1 < len(lines) and re.match(
                r'^\|[\s\-:|]+\|$', lines[i + 1].strip()):
            header = [deinline(c) for c in s.strip('|').split('|')]
            i += 2
            rows = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                rows.append([deinline(c)
                             for c in lines[i].strip().strip('|').split('|')])
                i += 1
            blocks.append({'type': 'table', 'header': header, 'rows': rows,
                           'cell_font': {'name': '仿宋', 'size': 10}})
            continue

        # 标题层级
        if s.startswith('# ') and md_title is None:
            md_title = deinline(s[2:])
            i += 1
            continue
        if s.startswith('## '):
            blocks.append({'type': 'h1', 'text': deinline(s[3:])})
            i += 1
            continue
        if s.startswith('### '):
            blocks.append({'type': 'h2', 'text': deinline(s[4:])})
            i += 1
            continue

        # 分隔线
        if re.match(r'^-{3,}$', s):
            i += 1
            continue

        # 引述 → 楷体（连续 > 行合并成一段）
        if s.startswith('>'):
            buf = []
            while i < len(lines) and lines[i].strip().startswith('>'):
                buf.append(lines[i].strip().lstrip('>').strip())
                i += 1
            txt = deinline(' '.join(x for x in buf if x))
            if txt:
                blocks.append({'type': 'p', 'text': txt, 'font': '楷体_GB2312',
                               'size': 14, 'indent': True, 'line': 26})
            continue

        # 列表项
        if re.match(r'^[-*]\s+', s):
            blocks.append({'type': 'p', 'indent': True,
                           'text': '· ' + deinline(re.sub(r'^[-*]\s+', '', s))})
            i += 1
            continue

        # 普通段落：合并连续非空行
        buf = [s]
        i += 1
        while i < len(lines) and lines[i].strip() and not re.match(
                r'^(#|\||>|-{3,}|[-*]\s)', lines[i].strip()):
            buf.append(lines[i].strip())
            i += 1
        txt = deinline(' '.join(buf))
        # 编号条目顶格，其余首行缩进
        blocks.append({'type': 'p', 'text': txt,
                       'indent': not re.match(r'^[0-9]+[.、]', txt)})

    spec = {
        'title': title or md_title or '会议纪要',
        'title_font': {'name': '黑体', 'size': 22},
        'normal_font': {'name': '仿宋_GB2312', 'size': 16},
        'page': {'margins_mm': {'top': 37, 'bottom': 35, 'left': 28, 'right': 26}},
        'footer_page_numbers': True,
        'blocks': blocks,
    }
    if subtitle:
        spec['subtitle'] = subtitle

    spec_path.parent.mkdir(parents=True, exist_ok=True)
    spec_path.write_text(json.dumps(spec, ensure_ascii=False, indent=1),
                         encoding='utf-8')
    return spec


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    src = pathlib.Path(sys.argv[1])
    out = pathlib.Path(sys.argv[2])
    title = sys.argv[3] if len(sys.argv) > 3 else None
    subtitle = sys.argv[4] if len(sys.argv) > 4 else None
    spec = convert(src, out, title, subtitle)
    kinds = {}
    for b in spec['blocks']:
        kinds[b['type']] = kinds.get(b['type'], 0) + 1
    print(json.dumps({'ok': True, 'spec': str(out), 'title': spec['title'],
                      'blocks': kinds,
                      'paras': kinds.get('p', 0),
                      'tables': kinds.get('table', 0)},
                     ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())

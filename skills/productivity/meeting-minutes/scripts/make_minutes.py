#!/usr/bin/env python3
"""转写 JSON → 豆包式会议纪要 Markdown。

用法:
    python3 make_minutes.py <transcript.json> --out minutes.md \
        [--title "会议主题"] [--date 2026/11/09] [--mode auto|doubao|gov]

铁律（照 SKILL.md）：
  · 不许编人名、数字、时限、结论，转写里没有的不写
  · 不许把提议当决策
  · 不许猜发言人身份
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

ENV = '/opt/data/.env'
LLM = 'https://api.deepseek.com/v1/chat/completions'
MODEL = 'deepseek-chat'


def getkey(name='DEEPSEEK_API_KEY'):
    fd = os.open(ENV, os.O_RDONLY)
    d = os.read(fd, 400000).decode('utf-8', 'ignore')
    os.close(fd)
    m = re.search(rf'^{name}\s*=\s*(.+)$', d, re.M)
    if not m:
        sys.exit(f'{ENV} 缺 {name}')
    return m.group(1).strip().strip('"\'')


def ts(sec):
    sec = int(sec or 0)
    return f'{sec//60:02d}:{sec%60:02d}'


def build_prompt(transcript, title, date, mode, src_name):
    # 带时间戳的转写正文
    lines = []
    for s in transcript['segments']:
        lines.append(f"[{ts(s['start'])}] {s['text']}")
    body = '\n\n'.join(lines)

    mode_rule = {
        'doubao': '用豆包式四段结构：总结 / 智能章节 / 关键决策 / 金句时刻。',
        'gov': '用政务式结构：一、二、三 分大节，节内用 1. 2. 3. 编号条目，必要处加「注意事项：a…… b……」。',
        'auto': ('先判断会议类型再选结构。判定标准（按顺序比对，命中即定）：\n'
                 '  · 出现两方或多方单位/人员就同一批事项交换意见、比对清单、探讨方案、谈合作、对接需求 → 豆包式四段'
                 '（总结 / 智能章节 / 关键决策 / 金句时刻）。对接会、交流会、讨论会、座谈会、需求对接都算这一类。\n'
                 '  · 出现任务分解、责任分工、时限要求、培训讲解、逐条部署 → 政务式'
                 '（一二三大节 + 编号条目 + 注意事项）。\n'
                 '  · 判断不了时一律用豆包式四段，不要用政务式。'),
    }[mode]

    return f"""你是一名政务信息化项目的高级咨询顾问，负责把会议录音转写整理成正式会议纪要。

【输出结构】
{mode_rule}

【格式硬要求，逐条核对】
- 正文第一行必须是一级标题 `# <会议主题>纪要`，frontmatter 之后空一行再写。
- `tags` 必须正好 10 个，专有名词优先（系统名/机构名/项目名/业务名），不许多不许少。
- `summary` 必须正好 5 条，每条一句话，结尾必须是「 ×」（空格加乘号）。
- 豆包式的「智能章节」：按时间分段，每段开头 `### 一、<小标题>（MM:SS—MM:SS）`，
  段内每个要点用 `**<要点句。>**` 开头再展开两三句，不要写成编号列表。
- 豆包式的「金句时刻」：每条三行——`「<原话直引，一个字不许改>」`、空行、
  `—— <为什么重要，一句话点题>`。没有值得记的原话就整节省略，不许硬凑，更不许自己编一句塞进引号。

【硬性规则，违反即作废】
1. 转写里没有的人名、数字、金额、比例、日期、时限，一个字都不许写。听不清写【听不清】。
2. 只是"可以考虑""回头看看""再看看"的说法，不算决策，放进待定，不许写进关键决策。
3. 转写只标了"说话人1/2"的，不许猜他是什么职务、什么单位。
4. 每条决策必须能在转写里找到原话依据，写不出依据的不要写。
5. 数字用转写里的原值，不换算、不四舍五入、不加"约"。
6. 不要写"会议认为""与会人员一致表示"这类没有依据的套话，除非转写里确实如此。

【正文写法】
- 每个条目的首句要提纲挈领，后面再补细节。
- 涉及数量、时间、负责方，必须具体，不许空泛。
- 连续三句同一句式要拆开改写，别写成 AI 腔。

【frontmatter 要求】
紧跟正文最前面输出 YAML frontmatter：
---
title: "{title}"
date: {date}
tags:   # 10 个关键词，专有名词优先（系统名/机构名/项目名/业务名）
  - ...
summary:   # 5 条，每条一句话概括，结尾必须是空格加一个 × 号
  - "... ×"
related: []   # 找不到相关笔记就留空数组
---

【会议信息】
标题：{title}
日期：{date}
来源录音：{src_name}

【转写全文（带时间戳）】
{body}
"""


def call_llm(prompt, key, max_tokens=16000):
    body = {'model': MODEL, 'messages': [{'role': 'user', 'content': prompt}],
            'max_tokens': max_tokens, 'temperature': 0.3}
    req = urllib.request.Request(
        LLM, data=json.dumps(body).encode(),
        headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'})
    for i in range(3):
        try:
            with urllib.request.urlopen(req, timeout=600) as r:
                res = json.load(r)
            ch = res['choices'][0]
            content = ch['message']['content']
            fr = ch.get('finish_reason')
            if not content or not content.strip():
                raise RuntimeError('模型返回空内容')
            if fr == 'length':
                print(f'  ⚠️ finish_reason=length，输出被截断', file=sys.stderr)
            return content, res.get('usage') or {}
        except Exception as e:
            if i == 2:
                raise
            print(f'  重试 {i+1}: {e}', file=sys.stderr)
            time.sleep(3 * (i + 1))
    raise RuntimeError('LLM 调用未返回结果')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('transcript')
    ap.add_argument('--out', default='/tmp/minutes.md')
    ap.add_argument('--title', default='')
    ap.add_argument('--date', default='')
    ap.add_argument('--mode', default='auto', choices=['auto', 'doubao', 'gov'])
    a = ap.parse_args()

    tr = json.load(open(a.transcript, encoding='utf-8'))
    title = a.title or (os.path.splitext(tr.get('audio', '会议'))[0] + '会议纪要')
    date = a.date or time.strftime('%Y/%m/%d')
    print(f'  转写 {len(tr["text"])} 字 / {len(tr["segments"])} 段', file=sys.stderr)

    key = getkey()
    prompt = build_prompt(tr, title, date, a.mode, tr.get('audio', ''))
    print(f'  提示词 {len(prompt)} 字 → {MODEL}', file=sys.stderr)

    t0 = time.time()
    md, usage = call_llm(prompt, key)
    with open(a.out, 'w', encoding='utf-8') as f:
        f.write(md)
    print(f'✅ 纪要 {len(md)} 字 → {a.out}  ({time.time()-t0:.0f}s)  usage={usage}',
          file=sys.stderr)


if __name__ == '__main__':
    main()

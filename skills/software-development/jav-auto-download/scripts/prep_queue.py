#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""多番号云端准备队列 —— 一次只处理一条，避免多条 prep 抢同一个代理节点。

为什么必须串行：所有轮换动作都在改写 reality_active.json 并 proxy.sh stop/start，
两个并发就是互相把对方刚切好的节点顶掉，或者一个在跑 prep_dl 时另一个把 sing-box 重启了。

用法：
    export PATH=/opt/data/.venv/bin:$PATH
    python3 prep_queue.py            # 处理 prep_queue.json 里所有 pending
    python3 prep_queue.py --add CODE "完整目标文件名"   # 只追加，不开跑

清单格式（/opt/data/.tmp_tests/prep_queue.json）：
    [{"code": "ABF-394", "target": "ABF-394-女优-描述.mp4", "task": "prep", "status": "pending"}]

  task=prep  → 跑 prep_dl.py（搜 javdb → 选版 → 离线 → 清广告 → 改名）
  task=dump  → 只用 jav_manager.get_magnets() 导出候选清单，交用户定（不下任何东西）

状态：pending → done / reported / needs_user / failed。**done/reported/needs_user 会跳过，重跑是幂等的。**

  needs_user = 选版规则把全部候选否掉（典型是全站最大才 1.87GB，够不着 2GB 门槛）。
  此时把候选体积/文件数写进 item['candidates'] 并把状态钉成 needs_user，**立刻处理下一条**——
  换节点重试对这个结论一字节影响都没有，只会把 javdb 配额烧光。候选要原样报给用户让他挑。

🚨 运行期间不要直接编辑 prep_queue.json 追加番号：本脚本启动时把清单读进内存、每条处理完
   回写**内存版本**，你的追加会被覆盖掉（新番号神不知鬼不觉丢了）。收到新番号时用
   `--add` 或手写 prep_pending.json，本脚本每次启动会先把 pending 合并进队列。

🚨 导出候选用 get_magnets()，绝不自己写正则扒 HTML：javdb 的 data-size 单位是 MB、
   data-files="0" 是空值要回退正文，自写正则极易全抓到 0 → 被 <2GB 规则全否 →
   误报「该番号只有小体积版」。判据：所有候集体积恰好都为 0 时，先怀疑解析器。
"""
import importlib.util
import json
import pathlib
import re
import subprocess
import sys
import time

TMP = pathlib.Path('/opt/data/.tmp_tests')
QF = TMP / 'prep_queue.json'
PF = TMP / 'prep_pending.json'
SKILL = pathlib.Path('/opt/data/proxy-skill')
ACTIVE = SKILL / 'reality_active.json'
SB = str(SKILL / 'sing-box')
PROXY = 'http://127.0.0.1:10808'
COOLDOWN = 1200          # javdb 每 IP 只有 1-3 次请求，全 403 后约 20 分钟解封
PROXY_SH = '/opt/data/proxy-skill/proxy.sh'

NODES = [
    'node_🇺🇸美国圣何塞03.json', 'node_🇺🇸美国圣何塞05.json',
    'node_🇺🇸美国圣何塞07.json', 'node_🇺🇸美国洛杉矶08.json',
    'node_🇸🇬AWS新加坡04.json', 'node_🇸🇬AWS新加坡05.json',
    'node_🇺🇸美国圣何塞02.json', 'node_🇺🇸美国圣何塞06.json',
    'node_🇺🇸美国圣何塞01.json', 'node_🇸🇬AWS新加坡03.json',
    'node_🇺🇸美国圣何塞04.json',
]


def sh(cmd, timeout=580):
    """跑 shell。节点名与路径全在脚本里硬编码，不接受外部输入，shell=True 是安全的。"""
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)


def load_jm():
    spec = importlib.util.spec_from_file_location('jm', '/opt/data/jav_manager.py')
    jm = importlib.util.module_from_spec(spec)
    sys.modules['jm'] = jm
    spec.loader.exec_module(jm)
    return jm


def switch_node(fname):
    """切节点并只用 google 验活。绝不拿 javdb 做连通性测试——测试本身就把配额吃掉了。"""
    p = SKILL / fname
    if not p.exists():
        return None
    try:
        tag = json.loads(p.read_text(encoding='utf-8'))['outbounds'][0].get('tag', fname)
    except Exception:
        return None
    ACTIVE.write_text(p.read_text(encoding='utf-8'), encoding='utf-8')
    if sh(f'{SB} check -c {ACTIVE}', 30).returncode != 0:
        return None
    sh(f'bash {PROXY_SH} stop', 30)
    time.sleep(1)
    sh(f'bash {PROXY_SH} start', 60)
    r = sh(f'curl -s -o /dev/null -w "%{{http_code}}" -m 10 -x {PROXY} '
           f'https://www.google.com/generate_204', 25)
    return tag if (r.stdout or '').strip() in ('204', '200') else None


def run_dump(jm, code, detail_path):
    """只导出候选，不下任何东西。返回 True 表示成功拿到清单。"""
    mags = jm.get_magnets(detail_path)
    if not mags:
        return False
    rows = sorted(({
        'name': m['name'],
        'size_bytes': m['size_bytes'],
        'gb': round(m['size_bytes'] / 1024 ** 3, 2),
        'file_count': m['file_count'],
        'has_subtitle': int(m['has_subtitle']),
    } for m in mags), key=lambda x: -x['size_bytes'])
    print(f'  [{code}] {len(rows)} 条磁链：', flush=True)
    for x in rows:
        print(f"     {x['gb']:6.2f}GB / {x['file_count']:2d}文件 / 字幕{x['has_subtitle']}"
              f"  {x['name'][:50]}", flush=True)
    if all(x['size_bytes'] == 0 for x in rows):
        print('  ⚠️ 全部体积为 0 —— 先怀疑解析器，不要据此判「只有小体积版」', flush=True)
    out = TMP / f'{code}_candidates.json'
    out.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'  已存 {out}', flush=True)
    return True


def run_prep(code, target):
    """跑 prep_dl.py，返回 (是否成功, 是否属于限流失败, 候选清单)。

    第三个返回值只在「选版规则把全部候选否掉」时非空：那种情况换 8 个节点、
    再等 3 轮 20 分钟，结论一模一样，纯属白烧 javdb 配额（每换一次节点就烧一次请求）。
    拿到候选就让调用方标 needs_user 并立刻跳到下一条。
    """
    r = sh(f'export PATH=/opt/data/.venv/bin:$PATH && python3 '
           f'{TMP}/prep_dl.py "{code}" "{target}"')
    # stderr 必须一起打印：只 print(stdout) 会把异常和 exit=2 的原因全吞掉，
    # 表现就是「跑完什么都不说」，只能靠猜（曾因此白换 6-8 个节点才反应过来不是限流）。
    out = (r.stdout or '') + (r.stderr or '')
    for line in out.splitlines():
        if any(k in line for k in ('磁链', '选定', '重命名', '空文件夹', '未搜到',
                                   '详情页', '已删', 'GB ')):
            print(f'  [prep] {line}', flush=True)
    if '已重命名' in out or '空文件夹已删' in out:
        return True, False
    # 详情页拿不到 = 限流，换节点有意义；拿到了却没「选定」= 选版规则全否，换节点白费
    throttled = ('未搜到该番号' in out) or ('详情页: None' in out)
    cand = []
    if not throttled:
        if '没有 >=2GB 的候选版本' in out:
            cand = [l.strip() for l in out.splitlines()
                    if re.search(r'\d+\.\d+GB\s+\d+个文件', l)]
            print('  ⚠️ 全部候选 <2GB（规则拒绝，不是节点问题），候选如下：', flush=True)
            for c in cand:
                print(f'        {c}', flush=True)
        else:
            print('  ← 非限流失败，换节点无意义', flush=True)
    return False, throttled, cand


def merge_pending():
    """把 prep_pending.json 里的新番号合并进队列。必须在读进内存之前跑。"""
    if not PF.exists():
        return []
    pend = json.loads(PF.read_text(encoding='utf-8') or '[]')
    if not pend:
        return []
    q = json.loads(QF.read_text(encoding='utf-8')) if QF.exists() else []
    have = {x['code'] for x in q}
    added = [it['code'] for it in pend if it['code'] not in have]
    q.extend(it for it in pend if it['code'] not in have)
    QF.write_text(json.dumps(q, ensure_ascii=False, indent=2), encoding='utf-8')
    PF.write_text('[]', encoding='utf-8')
    return added


def add_one(code, target, task='prep'):
    pend = json.loads(PF.read_text(encoding='utf-8') or '[]') if PF.exists() else []
    if not any(x['code'] == code for x in pend):
        pend.append({'code': code, 'target': target, 'task': task, 'status': 'pending'})
        PF.write_text(json.dumps(pend, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'已记入 {PF}（共 {len(pend)} 条）：' + '、'.join(x['code'] for x in pend))


def main():
    if len(sys.argv) >= 3 and sys.argv[1] == '--add':
        add_one(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None,
                'dump' if (len(sys.argv) > 4 and sys.argv[4] == 'dump') else 'prep')
        return 0

    added = merge_pending()
    if added:
        print(f'合并新番号: {"、".join(added)}', flush=True)

    queue = json.loads(QF.read_text(encoding='utf-8'))
    jm = load_jm()
    orig = ACTIVE.read_text(encoding='utf-8')
    failed = []

    try:
        for item in queue:
            code = item['code']
            if item.get('status') in ('done', 'reported', 'failed', 'needs_user'):
                continue
            task = item.get('task', 'prep')
            target = item.get('target')
            print(f'\n{"=" * 58}\n▶ {code}  ({task})  {time.strftime("%H:%M:%S")}\n{"=" * 58}',
                  flush=True)

            ok = False
            for rnd in range(1, 4):
                print(f'  第 {rnd}/3 轮', flush=True)
                for node in NODES:
                    tag = switch_node(node)
                    if not tag:
                        continue
                    if task == 'dump':
                        detail = item.get('detail')
                        if not detail:
                            print('  dump 任务缺 detail 字段（已知详情页路径），跳过', flush=True)
                            break
                        try:
                            ok = run_dump(jm, code, detail)
                        except Exception as e:
                            print(f'  [{tag}] 详情页失败（{e}，多半是限流）', flush=True)
                            continue
                        if not ok:
                            print(f'  [{tag}] 详情页失败（限流），换节点', flush=True)
                            continue
                    else:
                        ok, throttled, cand = run_prep(code, target)
                        if not ok and throttled:
                            continue          # 限流，换节点
                        if not ok:
                            if cand:
                                item['candidates'] = cand
                                item['status'] = 'needs_user'
                            break             # 非限流失败，换节点无意义
                    print(f'  [{tag}] ✅', flush=True)
                    break
                if ok:
                    break
                if rnd < 3:
                    print(f'  … 等 {COOLDOWN // 60} 分钟再试  {time.strftime("%H:%M:%S")}', flush=True)
                    time.sleep(COOLDOWN)

            if item.get('status') != 'needs_user':
                item['status'] = ('done' if (ok and task == 'prep')
                                  else 'reported' if ok else 'failed')
                if not ok:
                    failed.append(code)
            QF.write_text(json.dumps(queue, ensure_ascii=False, indent=2), encoding='utf-8')
    finally:
        ACTIVE.write_text(orig, encoding='utf-8')
        sh(f'bash {PROXY_SH} stop', 30)
        time.sleep(1)
        sh(f'bash {PROXY_SH} start', 60)

    print('\n=== 队列处理完毕 ===', flush=True)
    for it in queue:
        print(f"  {it['code']:10s} {it.get('status', 'pending')}", flush=True)
    if failed:
        print(f'\n❌ 失败: {"、".join(failed)}', flush=True)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())

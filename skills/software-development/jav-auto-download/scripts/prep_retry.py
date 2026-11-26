#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""javdb 配额耗尽时的轮换准备：每轮遍历全部节点，失败就等 20 分钟再来。

用法:
    prep_retry.py <番号> "<目标文件名.mp4>" [最大轮数]

两条硬规则（都踩过）:
  1. 切节点后**只用 google/generate_204 验连通**，绝不拿 javdb 测——
     配额只有 1-3 次，测试本身就是一次消耗，测通了额度也没了。
  2. **同一时刻只允许一个切节点的任务在跑**。两个并发会互相顶掉
     reality_active.json、或在 prep_dl 跑到一半时把 sing-box 重启。
     收到新番号时先确认没有别的轮换任务在跑，有就排队。

诊断要点：日志里有「详情页」和「磁链 N 条」但**没有「选定」** =
选版规则否掉了全部候选（全 <2GB / 全 -U / btih 非 40 位），
**与节点无关**，此时继续换节点纯属浪费配额 —— 脚本会直接停下并把候选交给用户。
"""
import json, pathlib, subprocess, sys, time, re

SKILL = pathlib.Path('/opt/data/proxy-skill')
ACTIVE = SKILL / 'reality_active.json'
SB = str(SKILL / 'sing-box')
PROXY = 'http://127.0.0.1:10808'

CODE = sys.argv[1]
NEWNAME = sys.argv[2]
ROUNDS = int(sys.argv[3]) if len(sys.argv) > 3 else 3

# 这两个值会拼进 shell 命令，先挡掉危险字符
if not re.fullmatch(r'[A-Za-z0-9-]{2,20}', CODE):
    sys.exit(f'非法番号: {CODE!r}')
if re.search(r'["`$\\;&|<>*\n\r]', NEWNAME) or not NEWNAME.lower().endswith(('.mp4', '.mkv')):
    sys.exit(f'文件名非法或后缀不对: {NEWNAME!r}')

# 只列 US/SG，日本节点被 javdb 按国家封锁
NODES = [
    'node_🇺🇸美国圣何塞03.json', 'node_🇺🇸美国圣何塞05.json',
    'node_🇺🇸美国圣何塞07.json', 'node_🇺🇸美国洛杉矶08.json',
    'node_🇸🇬AWS新加坡04.json', 'node_🇸🇬新加坡04.json',
    'node_🇺🇸美国圣何塞02.json', 'node_🇺🇸美国圣何塞06.json',
    'node_🇺🇸美国圣何塞01.json', 'node_🇸🇬AWS新加坡03.json',
    'node_🇺🇸美国圣何塞04.json', 'node_🇸🇬新加坡05.json',
]


def sh(cmd, timeout=600):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)


def switch(nm):
    p = SKILL / nm
    if not p.exists():
        return None
    try:
        cfg = json.loads(p.read_text(encoding='utf-8'))
        tag = cfg['outbounds'][0].get('tag', nm)
    except Exception:
        return None
    ACTIVE.write_text(p.read_text(encoding='utf-8'), encoding='utf-8')
    if sh(f'{SB} check -c {ACTIVE}', 30).returncode != 0:
        return None
    sh('bash /opt/data/proxy-skill/proxy.sh stop', 30); time.sleep(1)
    sh('bash /opt/data/proxy-skill/proxy.sh start', 60)
    c = sh(f'curl -s -o /dev/null -w "%{{http_code}}" -m 10 -x {PROXY} '
           f'https://www.google.com/generate_204', 25)
    return tag if (c.stdout or '').strip() in ('204', '200') else None


orig = ACTIVE.read_text(encoding='utf-8')

for rnd in range(1, ROUNDS + 1):
    print(f'====== 第 {rnd}/{ROUNDS} 轮  {time.strftime("%H:%M:%S")} ======', flush=True)
    for nm in NODES:
        tag = switch(nm)
        if not tag:
            print(f'  [{nm}] 代理不通/配置无效，跳过', flush=True)
            continue

        r = sh(f'export PATH=/opt/data/.venv/bin:$PATH && python3 '
               f'/opt/data/.tmp_tests/prep_dl.py "{CODE}" "{NEWNAME}"')
        # stderr 必须一起打，否则失败原因全被吞掉
        out = (r.stdout or '') + (r.stderr or '')
        for line in out.splitlines():
            if any(k in line for k in ('选定', '重命名', '空文件夹', '未搜到', '详情页',
                                       '已删', 'KEEP', 'DEL', 'GB ')):
                print(f'  [{tag}] {line}', flush=True)

        if '已重命名' in out or '空文件夹已删' in out:
            print(f'\n✅ 成功（{tag}）  番号 {CODE}', flush=True)
            sys.exit(0)

        # 拿到详情页和磁链列表但没有「选定」→ 选版全否，与节点无关，立刻停
        if '详情页' in out and '选定' not in out and r.returncode == 2:
            ACTIVE.write_text(orig, encoding='utf-8')
            sh('bash /opt/data/proxy-skill/proxy.sh stop', 30); time.sleep(1)
            sh('bash /opt/data/proxy-skill/proxy.sh start', 60)
            print(f'\n⚠️ {CODE}：候选全部不满足选版规则（见上方体积清单）', flush=True)
            print('   这不是节点问题——把候选列给用户定，不要继续换节点。', flush=True)
            sys.exit(2)

        print(f'  [{tag}] ← 本次失败（{r.returncode}），换节点', flush=True)

    if rnd < ROUNDS:
        print(f'  … 全部节点 403，等 20 分钟（{time.strftime("%H:%M:%S")} 起）', flush=True)
        time.sleep(1200)

ACTIVE.write_text(orig, encoding='utf-8')
sh('bash /opt/data/proxy-skill/proxy.sh stop', 30); time.sleep(1)
sh('bash /opt/data/proxy-skill/proxy.sh start', 60)
print(f'\n❌ {ROUNDS} 轮全部失败，已回滚节点。番号 {CODE} 需人工处理。', flush=True)
sys.exit(1)

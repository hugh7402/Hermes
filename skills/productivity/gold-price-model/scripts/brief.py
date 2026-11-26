# -*- coding: utf-8 -*-
"""黄金每日简报（新版，四段）

  1. 行情 + 账户（招行口径，沿用老版单边点差 2.5 元）
  2. 昨日归因（国际金价 / 国内溢价 / 汇率 各占多少）
  3. 底部条件监测（5 条满足几个）
  4. 仓位缺口 + 日度倾向 + 预测台账命中率

════════════ 设计约束 ════════════
• 招行价：卖出价 = Au99.99 − 2.5（他的净值），银行买入牌价 = +2.5。
  双边总点差 5 元/克，这个口径不能改，否则净值和盈亏全错。
• **不输出周度/月度方向预测**（回测已证无效，见 SKILL.md）。
  日度倾向只是“弱信号”，必须带区间、必须标明命中率。
• 简报不拉网。数据全从 panel.csv 读（由 backfill.py 先跑）。
  这样即使代理挂了，简报也能出，只会在末尾提示数据可能滞后。

用法：
  python3 brief.py
"""
import csv
import datetime as dt
import json
import math
import pathlib
import sys

import numpy as np

import attribution as AT
import backtest as BT
import regime as RG

BASE = pathlib.Path(__file__).resolve().parent.parent
DATA = BASE / 'data'
PANEL = DATA / 'panel.csv'
FORECASTS = DATA / 'forecasts.csv'
CONFIG = pathlib.Path('/opt/data/gold/config.json')

SPREAD_SIDE = 2.5
SPREAD = 5.0
HORIZON = 5          # 台账回打周期（交易日）


# ────────────────────── 台账 ──────────────────────

def ledger_append(date, au_close, pred, sigma):
    """记下今天的日度倾向，等 5 个交易日后回打"""
    fields = ['date', 'au_close', 'pred', 'sigma', 'lo', 'hi', 'actual', 'hit']
    rows = []
    if FORECASTS.exists():
        with open(FORECASTS, encoding='utf-8') as f:
            rows = list(csv.DictReader(f))
    if any(r['date'] == date for r in rows):
        return rows
    rows.append({
        'date': date,
        'au_close': f'{au_close:.2f}',
        'pred': f'{pred:.6f}',
        'sigma': f'{sigma:.6f}',
        'lo': f'{pred - 1.645*sigma:.6f}',
        'hi': f'{pred + 1.645*sigma:.6f}',
        'actual': '',
        'hit': '',
    })
    _write(rows, fields)
    return rows


def ledger_score(rows, panel):
    """把已经到期的预测回打：算 T+5 累计收益，记方向是否命中和区间是否覆盖"""
    idx = {r['date']: i for i, r in enumerate(panel)}
    au = [float(r['au_close']) for r in panel]
    changed = False
    for r in rows:
        if r.get('hit'):
            continue
        i = idx.get(r['date'])
        if i is None or i + HORIZON >= len(au):
            continue
        act = math.log(au[i + HORIZON] / au[i])
        cum_pred = float(r['pred']) * HORIZON      # 粗略：日度倾向×天数
        r['actual'] = f'{act:.6f}'
        r['hit'] = '1' if (act > 0) == (cum_pred > 0) else '0'
        changed = True
    if changed:
        _write(rows, ['date', 'au_close', 'pred', 'sigma', 'lo', 'hi', 'actual', 'hit'])
    return rows


def _write(rows, fields):
    DATA.mkdir(parents=True, exist_ok=True)
    with open(FORECASTS, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, '') for k in fields})


# ────────────────────── 主流程 ──────────────────────

def main():
    if not PANEL.exists():
        print('⚠️ 黄金简报\n\npanel.csv 不存在，先跑 backfill.py')
        return 1
    cfg = json.loads(CONFIG.read_text())
    grams, cost_px = cfg['grams'], cfg['cost_price']
    total = cfg['total_assets']
    lo_t, hi_t = cfg['gold_target_low'], cfg['gold_target_high']

    panel = BT.load()
    last = panel[-1]
    px = float(last['au_close'])
    sell = round(px - SPREAD_SIDE, 2)
    buy = round(px + SPREAD_SIDE, 2)

    # 数据新鲜度
    try:
        age = (dt.date.today() - dt.date.fromisoformat(last['date'])).days
    except Exception:
        age = 99

    # 模型：只用滞后数据拟合，预测下一天的日度倾向
    hist = BT.build(panel)
    coef = BT.ols([d['y'] for d in hist], [[d[f] for d in hist] for f in BT.FACTORS])
    feats_last = [hist[-1][f] for f in BT.FACTORS]
    pred = BT.pred(coef, feats_last)
    resid = np.array([d['y'] - BT.pred(coef, [d[f] for f in BT.FACTORS]) for d in hist])
    sigma = float(resid.std())

    # 台账
    rows = ledger_append(last['date'], px, pred, sigma)
    rows = ledger_score(rows, panel)
    scored = [r for r in rows if r.get('hit')]
    hit_rate = sum(int(r['hit']) for r in scored) / len(scored) if scored else None

    # 归因（同期列）
    adata = AT.build(panel, lag=0)
    y = adata[-1]
    bB = AT.ols([d['r_au'] for d in adata], [[d['r_gld'], d['r_fx']] for d in adata])
    c_gld = bB['beta'][0] * y['r_gld']
    c_fx = bB['beta'][1] * y['r_fx']
    c_res = y['r_au'] - c_gld - c_fx

    # 条件（复用 regime 逻辑）
    au = [float(r['au_close']) for r in panel]
    tips = [float(r['tips10y']) for r in panel]
    gc = [float(r['gc_fut']) for r in panel]
    fx = [float(r['usdcny']) for r in panel]
    prem = [au[i] / (gc[i] / 31.1035 * fx[i]) - 1 for i in range(len(au))]
    ma20 = sum(au[-20:]) / 20
    ma60 = sum(au[-60:]) / 60
    r14 = RG.rsi(au)
    pct_q, _ = RG.cftc_percentile(panel, float(last['cftc_net_long']))

    # 🚨 回测已证：只有 C1（实际利率回落）有预核力，C2/C4/C5 无效甚至反向。
    # 简报不再报「几条满足」，只报那一条真信号 + 背景数字。
    c1_ok = max(tips[-20:]) - tips[-1] >= 0.15
    c1_drop = (max(tips[-20:]) - tips[-1]) * 100

    # 账户与仓位
    cost = cost_px * grams
    mv = sell * grams
    profit = mv - cost
    cur_pct = mv / total * 100
    gap_lo = total * lo_t / 100 - mv

    # ── 输出 ──
    L = []
    A = L.append
    A(f'📊 黄金简报 · {last["date"]}')
    A('')
    A(f'【行情】Au99.99 {px:.2f}　招行净值 {sell:.2f}（银行卖价 {buy:.2f}）')
    A(f'  国际 ${float(last["gld"])*10:.0f}/oz 口径　美元 {float(last["dxy"]):.2f}　'
      f'汇率 {float(last["usdcny"]):.3f}')
    A(f'  实际利率 {tips[-1]:.2f}%　溢价 {prem[-1]*100:+.2f}%　MA20 {ma20:.2f}（{(px/ma20-1)*100:+.1f}%）')
    A('')
    A(f'【昨日归因】Au 涨跌 {y["r_au"]*100:+.2f}%')
    A(f'  国际金价 {c_gld*100:+.2f}%　汇率 {c_fx*100:+.2f}%　国内溢价 {c_res*100:+.2f}%')
    A('')
    A(f'【状态参考】以下五项均经事件式检验证伪，非买卖信号')
    A(f'  实际利率 {tips[-1]:.2f}%（20日回落 {c1_drop:.0f}bp）　RSI {r14:.0f}　'
      f'CFTC {pct_q:.0f}分位')
    A(f'  溢价 {prem[-1]*100:+.2f}%　MA20 距 {(px/ma20-1)*100:+.1f}%')
    A('  ⚠️ C1「实际利率回落」独立事件检验 20日超额 −1.90%、后半样本 −6.69%，')
    A('     C2/C3 无效、C4/C5 反向。**不给买点、不给底。**')
    A('')
    A(f'【你的账户】{grams:g} 克，成本 {cost_px:.2f}')
    A(f'  市值 {mv:,.0f} 元　浮盈亏 {profit:+,.0f} 元（{profit/cost*100:+.2f}%）')
    A(f'  占总资产 {cur_pct:.2f}%（目标 {lo_t}–{hi_t}%）')
    A(f'  距 {lo_t}% 还差 {gap_lo:,.0f} 元 ≈ {gap_lo/sell:.0f} 克')
    A('')
    A(f'【日度倾向】模型 {pred*100:+.2f}%　次日 90% 区间 '
      f'[{pred*100-1.645*sigma*100:+.1f}%, {pred*100+1.645*sigma*100:+.1f}%]')
    if hit_rate is not None:
        A(f'  台账 {len(scored)} 条已回打，方向命中率 {hit_rate*100:.1f}%（回测基准 58%）')
    else:
        A('  台账尚无到期记录，命中率待累计')
    A('  🚨 日度弱信号，不做周度/月度方向断言')
    if age > 3:
        A('')
        A(f'⚠️ 数据滞后 {age} 天（backfill 未成功），以上非最新')

    print('\n'.join(L))
    return 0


if __name__ == '__main__':
    sys.exit(main())

# -*- coding: utf-8 -*-
"""底部条件监测（regime watch）

════════════ 为什么用「条件监测」而不是「时点预测」════════════
回测已证：3 个月方向/时点预测不可做（水平模型 R²=0.433，60 日独立样本仅 7 个，
样本期只含一轮行情）。但「底部区域长什么样」是**可观测的**，不需要预测。

本脚本每天回答一个问题：底部特征凑齐了几个？

五个条件（每个都是历史上有依据的拐点特征）：
  C1 实际利率见顶  TIPS 从高位转头下行（20 日高点回落 ≥ 15bp）
  C2 溢价出清    国内溢价回到 0 以下（恐慌抛售已释放）
  C3 多头出清    CFTC 非商业净多头处于历史低位（≤ 30 分位）
  C4 超卖        RSI-14 ≤ 35
  C5 趋势转多     收盘站回 20 日均线（趋势拐点的最后确认）

🚨 这是「状态描述」不是「买入信号」。条件凑齐只说明“风险收益比改善”，
   不代表不会再跌。定投分批永远优于等一个时点。

用法：
  python3 regime.py
"""
import csv
import math
import pathlib

import numpy as np

DATA = pathlib.Path(__file__).resolve().parent.parent / 'data'


HIST_CFTC = []   # 用于算 CFTC 历史分位


def load():
    with open(DATA / 'panel.csv', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def rsi(prices, n=14):
    rets = [math.log(prices[i] / prices[i - 1]) for i in range(1, len(prices))]
    g = sum(max(x, 0) for x in rets[-n:]) / n
    l = sum(max(-x, 0) for x in rets[-n:]) / n
    return 100.0 if l == 0 else 100 - 100 / (1 + g / l)


def cftc_percentile(rows, cur):
    """CFTC 净多头的历史分位（周频去重）"""
    seen, vals = set(), []
    for r in rows:
        v = r['cftc_net_long']
        if not v or v in seen:
            continue
        seen.add(v)
        vals.append(float(v))
    if not vals:
        return None, 0
    return sum(1 for v in vals if v < cur) / len(vals) * 100, len(vals)


def main():
    rows = load()
    au = [float(r['au_close']) for r in rows]
    last = rows[-1]
    px = au[-1]

    tips = [float(r['tips10y']) for r in rows]
    gc = [float(r['gc_fut']) for r in rows]
    fx = [float(r['usdcny']) for r in rows]
    prem = [au[i] / (gc[i] / 31.1035 * fx[i]) - 1 for i in range(len(au))]

    print(f'══ 底部条件监测 · {last["date"]} ══')
    print(f'  上金所 Au99.99  {px:.2f} 元/克\n')

    checks = []

    # 🚨 事件式检验结论（validate_c1.py）：五个条件全部证伪，C1 也不例外。
    #    C1 用「重叠日」算是 +2.36% 超额，用「独立事件」算是 −1.90%，信号有害。
    #    2026 年那 5 次事件全亏，前后半完全反转。下面全部只作背景描述。

    # C1 实际利率见顶回落 —— ❌ 事件式检验：20日超额 −1.90%，前半+2.92%/后半−6.69%
    t20 = tips[-20:]
    peak = max(t20)
    drop = peak - tips[-1]
    ok1 = drop >= 0.15
    checks.append(('C1 实际利率回落', ok1, False, '−1.90%（事件式无效）',
                   f'TIPS {tips[-1]:.2f}%，20日高点 {peak:.2f}%，回落 {drop*100:.0f}bp'
                   f'　⚠️ 按重叠日算是假信号，事件式检验为负'))

    # C2 溢价出清 —— ❌ 无效：20日 +0.39%、60日 −2.86%
    ok2 = prem[-1] <= 0
    checks.append(('C2 溢价出清', ok2, False, '+0.39%/-2.86%',
                   f'溢价 {prem[-1]*100:+.2f}%（仅背景，无预核力）'))

    # C3 多头出清 —— ❌ 20日无效（−0.09%），仅60日略正
    pct, n_obs = cftc_percentile(rows, float(last['cftc_net_long']))
    ok3 = pct is not None and pct <= 30
    checks.append(('C3 多头出清', ok3, False, '−0.09%',
                   f'CFTC {float(last["cftc_net_long"])/1e4:.1f} 万手，历史 {pct:.0f} 分位（仅背景）'))

    # C4 技术超卖 —— ❌ **反向**：60日超额 −5.64%
    r = rsi(au)
    ok4 = r <= 35
    checks.append(('C4 技术超卖', ok4, False, '−5.64%（反向）',
                   f'RSI-14 {r:.1f}　⚠️ 超卖后历史上继续跌，不是买点'))

    # C5 站回 MA20 —— ❌ **反向**：20日超额 −1.03%
    ma20 = sum(au[-20:]) / 20
    ok5 = px >= ma20
    checks.append(('C5 站回 MA20', ok5, False, '−1.03%（反向）',
                   f'收盘 {px:.2f} vs MA20 {ma20:.2f}（{(px/ma20-1)*100:+.2f}%）⚠️ 右侧确认反而跑输'))

    for name, ok, valid, excess, detail in checks:
        mark = '✅' if ok else '❌'
        print(f'  {mark} {name:<16}【仅背景】 {detail}')

    met_all = sum(1 for _, ok, _, _, _ in checks if ok)
    print(f'\n  当前满足 {met_all}/5 项——**但这个计数没有任何预测意义**。')
    print(f'\n  🚨 五个条件全部经事件式检验证伪：')
    print(f'     C1 重叠日算 +2.36% / 独立事件算 −1.90%（前半 +2.92%、后半 −6.69%）')
    print(f'     C2 无效　C3 无效　C4 反向 −5.64%　C5 反向 −1.03%')
    print(f'     → **没有任何“底部信号”被验证有效。不要用本页做买卖判断。**')

    # 附加状态参考
    ma60 = sum(au[-60:]) / 60
    print(f'\n  参考：MA60 {ma60:.2f}（收盘距其 {(px/ma60-1)*100:+.1f}%），'
          f'距历史峰值 {(px/max(au)-1)*100:+.1f}%')

    # 结论：没有任何条件经得起事件式检验，只能给状态描述
    print(f'\n  → **不给买点、不给底、不给方向。** 五个条件均已被事件式检验证伪。')
    print(f'    可用的只有：分批建仓纪律 + 日度区间估计（另见 brief.py）。')
    print(f'\n  🚨 状态描述，不是择时信号。条件会反复，历史上底部区域可持数月。')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

# -*- coding: utf-8 -*-
"""验证五个底部条件到底有没有用

════════════ 为什么要这个脚本 ════════════
最初定的 C1–C5 阀值是拍脑袋的，全样本 459 天里「≥4 条成立」只出现 4 天
（合并后 1 个独立先例）——**样本上无法检验，等于凭感觉**。

本脚本做三件事：
  1. 每个条件单独检验：为真时未来 20/60 日收益 vs 全样本基准的差
  2. 计数阀值扫描：≥1/2/3/4 条各自的预核力
  3. 阀值网格：粗扫每个指标的不同阀值，看有没有更强的

════════════ 读结果的铁则 ════════════
• 基准不是 50%，是**全样本的无条件上涨率**（样本期是牛市，无条件涨率高）。
• 重叠窗口：20 日预期重叠 20 倍，有效样本 ≈ n/20，z 值必须用折后的样本算。
• 网格搜索（第 3 部分）是规格搜索，**最好的结果必须打折看**，不能直接采用。

用法：
  python3 validate_regime.py
"""
import math
import numpy as np

import backtest as BT

FWD = (20, 60)


def load_state():
    panel = BT.load()
    au = [float(r['au_close']) for r in panel]
    tips = [float(r['tips10y']) for r in panel]
    gc = [float(r['gc_fut']) for r in panel]
    fx = [float(r['usdcny']) for r in panel]
    cftc = [float(r['cftc_net_long']) for r in panel]
    prem = [au[i] / (gc[i] / 31.1035 * fx[i]) - 1 for i in range(len(au))]
    return panel, au, tips, prem, cftc


def rsi_series(au, m=14):
    out = [50.0] * len(au)
    for i in range(m + 1, len(au)):
        rets = [math.log(au[k] / au[k - 1]) for k in range(i - m, i)]
        g = sum(max(x, 0) for x in rets) / m
        l = sum(max(-x, 0) for x in rets) / m
        out[i] = 100.0 if l == 0 else 100 - 100 / (1 + g / l)
    return out


def cftc_pct_series(cftc):
    """扩展窗口分位（不偷未来）"""
    out = [50.0] * len(cftc)
    seen, prev = [], None
    for i, v in enumerate(cftc):
        if v != prev:
            seen.append(v)
            prev = v
        out[i] = (sum(1 for x in seen if x < v) / len(seen) * 100) if len(seen) >= 10 else 50.0
    return out


def indicators(panel, au, tips, prem, cftc):
    """每个条件背后的原始指标（都是连续值，方便扫阀值）"""
    ma20 = [None] * len(au)
    for i in range(19, len(au)):
        ma20[i] = sum(au[i - 19:i + 1]) / 20
    tips_drop = [0.0] * len(tips)      # 从 20 日高点的回落
    for i in range(20, len(tips)):
        tips_drop[i] = max(tips[i - 20:i + 1]) - tips[i]
    return {
        'C1 TIPS回落bp': [x * 100 for x in tips_drop],
        'C2 溢价%': [x * 100 for x in prem],
        'C3 CFTC分位': cftc_pct_series(cftc),
        'C4 RSI14': rsi_series(au),
        'C5 价格/MA20%': [(au[i] / ma20[i] - 1) * 100 if ma20[i] else 0.0 for i in range(len(au))],
    }


def fwd_rets(au, i, h):
    j = min(i + h, len(au) - 1)
    return (au[j] / au[i] - 1) * 100


def stat_block(name, flags, au, valid):
    """比较条件为真/假两组的未来收益"""
    res = {}
    for h in FWD:
        y_true = [fwd_rets(au, i, h) for i, f in zip(valid, flags) if f]
        y_false = [fwd_rets(au, i, h) for i, f in zip(valid, flags) if not f]
        if len(y_true) < 5 or len(y_false) < 5:
            res[h] = None
            continue
        mt, mf = np.mean(y_true), np.mean(y_false)
        # 有效样本折减（重叠窗口）
        n_eff = max(2, len(y_true) // h)
        sd = np.std(y_true, ddof=1) if len(y_true) > 1 else 1.0
        z = (mt - 50 * 0 + 0) / (sd / math.sqrt(n_eff)) if sd > 0 else 0.0
        res[h] = dict(n=len(y_true), mean=mt, base=mf, up=(np.array(y_true) > 0).mean() * 100,
                      base_up=(np.array(y_false) > 0).mean() * 100, n_eff=n_eff, sd=sd,
                      excess=mt - mf)
    return res


def main():
    panel, au, tips, prem, cftc = load_state()
    ind = indicators(panel, au, tips, prem, cftc)
    valid = list(range(60, len(au) - max(FWD)))
    print(f'══ 底部条件有效性验证 ══')
    print(f'  样本 {len(au)} 天（{panel[0]["date"]} → {panel[-1]["date"]}），'
          f'可用于验证 {len(valid)} 天\n')

    # 基准
    base20 = np.mean([fwd_rets(au, i, 20) for i in valid])
    base60 = np.mean([fwd_rets(au, i, 60) for i in valid])
    up20 = np.mean([fwd_rets(au, i, 20) > 0 for i in valid]) * 100
    up60 = np.mean([fwd_rets(au, i, 60) > 0 for i in valid]) * 100
    print(f'  无条件基准：20日 平均 {base20:+.2f}% / 上涨率 {up20:.0f}%　'
          f'60日 平均 {base60:+.2f}% / 上涨率 {up60:.0f}%')
    print(f'  ⚠️ 升幅基准不是 0%：样本期是牛市，无条件就是涨的\n')

    # ── 第1部分：原阀值逐条检验 ──
    THR = {
        'C1 TIPS回落bp': lambda v: v >= 15,
        'C2 溢价%': lambda v: v <= 0,
        'C3 CFTC分位': lambda v: v <= 30,
        'C4 RSI14': lambda v: v <= 35,
        'C5 价格/MA20%': lambda v: v >= 0,
    }
    print('══ 第1部分：原阀值下的条件单独表现 ══')
    print(f'  {"条件":<16}{"命天数":>7}{"20日超额":>10}{"60日超额":>10}{"20日上涨率":>11}{"有效样本":>9}  判定')
    flags_all = {}
    for name, vals in ind.items():
        f = [THR[name](vals[i]) for i in range(len(au))]
        flags_all[name] = f
        r = stat_block(name, f, au, valid)
        a, b = r[20], r[60]
        hit = sum(f)
        if a is None:
            print(f'  {name:<16}{hit:>7}   样本太少，无法判定')
            continue
        # 判定：20日超额 > 1% 且方向正确
        good = a["excess"] > 1.0
        print(f'  {name:<16}{hit:>7}{a["excess"]:>+9.2f}%{b["excess"]:>+9.2f}%'
              f'{a["up"]:>10.0f}%{a["n_eff"]:>9}  {"✅有正超额" if good else "❌无/负超额"}')

    # ── 第2部分：计数阀值 ──
    print(f'\n══ 第2部分：几条同时成立才有效 ══')
    print(f'  {"阈值":<8}{"命天数":>7}{"20日超额":>10}{"60日超额":>10}{"独立先例":>9}  判定')
    for k in (1, 2, 3, 4, 5):
        cnt = [sum(1 for n in ind if THR[n](ind[n][i])) for i in range(len(au))]
        f = [c >= k for c in cnt]
        r = stat_block(f, f, au, valid)
        a = r[20]
        hits = sum(1 for i in valid if f[i])
        if a is None:
            print(f'  ≥{k} 条{"":<4}{hits:>7}   样本太少，无法判定')
            continue
        indep = max(1, hits // 20)
        print(f'  ≥{k} 条{"":<4}{hits:>7}{a["excess"]:>+9.2f}%{r[60]["excess"] if r[60] else 0:>+9.2f}%'
              f'{indep:>9}  {"✅" if a["excess"]>1 else "❌"}')

    # ── 第3部分：阀值网格（带多重检验警告）──
    print(f'\n══ 第3部分：阀值粗扫（⚠️ 规格搜索，结果必须打折）══')
    GRID = {
        'C1 TIPS回落bp': [0, 10, 15, 25, 40],
        'C2 溢价%': [-2, -1, 0, 1],
        'C3 CFTC分位': [10, 20, 30, 50],
        'C4 RSI14': [25, 30, 35, 45, 55],
        'C5 价格/MA20%': [-10, -5, 0, 3],
    }
    best = []
    for name, vals in ind.items():
        for t in GRID[name]:
            if name in ('C2 溢价%', 'C3 CFTC分位', 'C4 RSI14'):
                f = [vals[i] <= t for i in range(len(au))]
                lab = f'<= {t}'
            else:
                f = [vals[i] >= t for i in range(len(au))]
                lab = f'>= {t}'
            r = stat_block(name, f, au, valid)
            if r[20]:
                best.append((r[20]['excess'], name, lab, sum(f), r[20]['n_eff']))
    best.sort(reverse=True)
    for ex, name, lab, hits, neff in best[:8]:
        print(f'  {name:<16}{lab:<8}命中 {hits:>4} 天  20日超额 {ex:+7.2f}%  有效样本 {neff}')
    print(f'\n  ⚠️ 一共试了 {len(best)} 个阀值组合，最好的那个必须当噪声打折')
    if best and best[0][0] > 3:
        print(f'     最高超额 {best[0][0]:+.2f}% 需要样本外再验证才能用，不能直接采纳')

    return 0


if __name__ == '__main__':
    raise SystemExit(main())

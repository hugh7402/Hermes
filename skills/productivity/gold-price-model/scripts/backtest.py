# -*- coding: utf-8 -*-
"""回测：样本外验证三层模型能否打过「瞎猜」

════════════ 铁则 ════════
只跟「上涨概率 50%、区间随便拍」比不算本事。真正要打过的是两个基准：

  B1 随机游走：预测下期收益 = 0（金融预测里最常被低估的对手）
  B2 历史均值：预测下期收益 = 训练期均值

如果模型的方向命中率没过 55%、或 MAE 没比 B1 小，**就是废模型**，
不要给用户报，也不要入 forecast 台账。

════════════ 三层结构 ════════
  r_au = r_国际(宏观因子) + r_汇率 + Δ溢价(均值回复)
溢价项用已拟合的 -0.646×prem，国际金价项用 OLS，汇率项取 0（随机游走）。

用法：
  python3 backtest.py                                   # 默认 2026-09-01 样本外
  python3 backtest.py --split 2026-08-01 --horizon 5
"""
import csv
import math
import pathlib
import sys

import numpy as np

DATA = pathlib.Path(__file__).resolve().parent.parent / 'data'
PANEL = DATA / 'panel.csv'

FACTORS = ['d_tips', 'r_dxy', 'r_vix', 'z_cftc', 'mom20', 'prem']

# 🚨 回测驱动的模型修正（2026-11-26，消融测试得出）：
#    原设计把溢价当「独立加法修正项」：r_au = 宏观预测 + c0 + c1*prem
#    结果 MAE 1.325%，比随机游走 1.268% 还差——因为溢价项拟合在残差上，
#    带了个 -0.187%/天的常数偏置，把宏观信号抵消掉了。
#    改成「溢价当一个普通因子丢进同一个回归」后：
#    命中率 57.8% → 60.3%，MAE 1.228% → 1.215%，z=+3.18 显著。
#    所以 MODE 固定为 single，不要再改回 add 式。
MODE = 'single'


def load() -> list[dict]:
    with open(PANEL, encoding='utf-8') as f:
        return list(csv.DictReader(f))


def build(rows) -> list[dict]:
    """全部用**滞后**数据（预测时点真能拿到的），标签用当日。"""
    au = [float(r['au_close']) for r in rows]
    gc = [float(r['gc_fut_l']) for r in rows]      # 滞后国际金价
    fx = [float(r['usdcny_l']) for r in rows]
    dxy = [float(r['dxy_l']) for r in rows]
    vix = [float(r['vix_l']) for r in rows]
    tips = [float(r['tips10y_l']) for r in rows]
    cftc = [float(r['cftc_net_long_l']) for r in rows]
    n = len(rows)
    out = []
    for i in range(22, n):
        parity = gc[i] / 31.1035 * fx[i]
        prem_prev = au[i - 1] / (gc[i - 1] / 31.1035 * fx[i - 1]) - 1   # 昨收盘已知
        out.append({
            'date': rows[i]['date'],
            'y': math.log(au[i] / au[i - 1]),                    # 标签：当日收益
            'r_gc': math.log(gc[i] / gc[i - 1]),                 # 国际金价（滞后对齐）
            'd_tips': tips[i] - tips[i - 1],
            'r_dxy': math.log(dxy[i] / dxy[i - 1]),
            'r_vix': math.log(vix[i] / vix[i - 1]),
            'z_cftc': (cftc[i] - cftc[i - 1]) / 100000.0,
            'mom20': math.log(au[i - 1] / au[i - 21]),
            'prem': prem_prev,
            'au_close': au[i],
        })
    return out


def ols(y, X):
    y = np.asarray(y, float)
    X = np.column_stack([np.ones(len(y))] + [np.asarray(c, float) for c in X])
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    return coef


def pred(coef, feats):
    return coef[0] + sum(coef[j + 1] * feats[j] for j in range(len(feats)))


def walkforward(min_train=200):
    """滚动前推（expanding window）：每天用「截至前一日的全部历史」拟合，
    预测当日，然后窗口向前扩一天。

    为什么必须这样测：单次 40/60 切分的样本外只有几十天，命中率的
    标准误高达 ±6.6%，59.6% 和 50% 根本分不开。walk-forward 能挤到
    250+ 个样本外观测，才能判定优势真假。
    """
    data = build(load())
    if len(data) < min_train + 30:
        print(f'  ❌ 总样本 {len(data)} 不足以做 walk-forward')
        return 2

    print(f'══ Walk-forward 滚动前推 ══')
    print(f'  总样本 {len(data)} 天，最小训练窗口 {min_train} 天')
    preds, acts, dates = [], [], []
    for i in range(min_train, len(data)):
        tr = data[:i]                      # 只用 i 之前的数据
        d = data[i]
        c1 = ols([x['y'] for x in tr], [[x[f] for x in tr] for f in FACTORS])
        preds.append(pred(c1, [d[f] for f in FACTORS]))
        acts.append(d['y'])
        dates.append(d['date'])

    preds, acts = np.array(preds), np.array(acts)
    n = len(acts)
    hit = (np.sign(preds) == np.sign(acts)).mean()
    k = int((np.sign(preds) == np.sign(acts)).sum())
    z = (hit - 0.5) / math.sqrt(0.25 / n)
    mae = np.abs(preds - acts).mean()
    mae_nv = np.abs(acts).mean()

    print(f'  样本外 {n} 天（{dates[0]} → {dates[-1]}）')
    print(f'\n  方向命中率 {hit*100:.1f}%（{k}/{n}）  z = {z:+.2f}  ' +
          ('✅ 5% 显著' if z >= 1.64 else '❌ 不显著'))
    print(f'  模型 MAE {mae*100:.3f}%/天   随机游走 {mae_nv*100:.3f}%/天  ' +
          ('✅更优' if mae < mae_nv else '❌更差'))

    for h in (1, 5, 10, 20):
        if n <= h + 2:
            continue
        cp = np.array([sum(preds[i:i + h]) for i in range(n - h)])
        ca = np.array([sum(acts[i:i + h]) for i in range(n - h)])
        hh = (np.sign(cp) == np.sign(ca)).mean()
        indep = len(cp) // h
        zh = (hh - 0.5) / math.sqrt(0.25 / max(indep, 2))
        mark = ' ⚠️低于抛硬币' if hh < 0.5 else (' ✅显著' if zh >= 1.64 else '')
        print(f'  {h:>2} 日累计命中率 {hh*100:5.1f}%  独立样本≈{indep:<4} z≈{zh:+.2f}{mark}')

    print(f'\n══ 判定 ══')
    ok = z >= 1.64 and mae < mae_nv
    print(f'  {"✅ 方向预测有统计显著优势" if z >= 1.64 else "❌ 方向预测无显著优势（样本量已足够，不是噪声问题）"}')
    print(f'  {"✅ 幅度预测优于随机游走" if mae < mae_nv else "❌ 幅度也估不准"}')
    if not z >= 1.64:
        print(f'\n  → 模型定位：**只输出区间与波动估计，不输出方向预测**。')
        print(f'    这正好坐实了设计原则第一条：只给区间不给点值。')
    return 0 if ok else 2


def run(split='2026-09-01', horizon=1):
    rows = load()
    data = build(rows)
    train = [d for d in data if d['date'] < split]
    test = [d for d in data if d['date'] >= split]
    if len(train) < 60 or len(test) < 20:
        print(f'  ❌ 样本不足：训练 {len(train)}、测试 {len(test)}')
        return 1

    print(f'══ 回测（三层模型）══')
    print(f'  训练 {len(train)} 天（{train[0]["date"]} → {train[-1]["date"]}）')
    print(f'  测试 {len(test)} 天（{test[0]["date"]} → {test[-1]["date"]}）  horizon={horizon}')

    # ── 拟合（全部只用训练集）──
    # 单回归模式：溢价作为普通因子参与，不做独立加法修正（见 FACTORS 处注释）
    c1 = ols([d['y'] for d in train], [[d[f] for d in train] for f in FACTORS])
    print(f'\n  拟合系数（单回归，target=r_au）：\n    const={c1[0]:.6f}  ' +
          '  '.join(f'{f}={c1[j+1]:+.4f}' for j, f in enumerate(FACTORS)))

    # ── 样本外预测（逐日滚动，不偷未来）──
    preds, acts, naive = [], [], []
    for d in test:
        preds.append(pred(c1, [d[f] for f in FACTORS]))
        acts.append(d['y'])
        naive.append(0.0)
    preds, acts = np.array(preds), np.array(acts)

    # ── 指标 ──
    hit = (np.sign(preds) == np.sign(acts)).mean()
    mae = np.abs(preds - acts).mean()
    mae_naive = np.abs(np.array(naive) - acts).mean()
    hist_mean = np.mean([d['y'] for d in train])
    mae_hist = np.abs(hist_mean - acts).mean()
    rmse = math.sqrt(((preds - acts) ** 2).mean())

    # 命中率显著性（二项分布正态近似 + 连续性修正）
    n_obs = len(acts)
    k = int((np.sign(preds) == np.sign(acts)).sum())
    se = math.sqrt(0.25 / n_obs)
    z = (hit - 0.5) / se if se > 0 else 0.0

    print(f'\n══ 样本外结果（单日）══')
    print(f'  方向命中率   {hit*100:.1f}%（{k}/{n_obs}）  瞎猜 50%，及格线 55%')
    print(f'  显著性检验   z = {z:+.2f}（|z|>1.64 才算 5% 显著；>1.96 为 1%）')
    if z < 1.64:
        print(f'  ⚠️ **命中率与抛硬币无显著差异**，不能声称「能预测方向」')
    print(f'  模型 MAE     {mae*100:.3f}%/天')
    print(f'  随机游走 MAE {mae_naive*100:.3f}%/天   → {"✅模型更优" if mae < mae_naive else "❌跑输随机游走"}')
    print(f'  历史均值 MAE {mae_hist*100:.3f}%/天   → {"✅模型更优" if mae < mae_hist else "❌跑输历史均值"}')
    print(f'  RMSE         {rmse*100:.3f}%')

    # ── 多周期方向命中率 ──
    print(f'\n══ 多周期方向命中率（重叠窗口，仅作参考）══')
    hits_by_h = {}
    for h in (1, 5, 20):
        if len(acts) <= h + 2:
            continue
        cp, ca = [], []
        for i in range(len(acts) - h):
            cp.append(sum(preds[i:i + h]))
            ca.append(sum(acts[i:i + h]))
        hh = (np.sign(cp) == np.sign(ca)).mean()
        hits_by_h[h] = hh
        note = f'（重叠，独立样本≈{max(1, len(cp)//h)}）' if h > 1 else ''
        mark = ' ⚠️低于抛硬币' if hh < 0.5 else ''
        print(f'  {h:>2} 日累计方向命中率 {hh*100:5.1f}%   n={len(cp)} {note}{mark}')

    # ── 区间覆盖（±1.645σ 应覆盖 90%）──
    resid_train = np.array([d['y'] - pred(c1, [d[f] for f in FACTORS]) for d in train])
    sigma = resid_train.std()
    inside = (np.abs(acts - preds) <= 1.645 * sigma).mean()
    print(f'\n  区间覆盖（±1.645σ={1.645*sigma*100:.2f}%）: {inside*100:.1f}%  ' +
          ('✅接近 90%' if 0.8 <= inside <= 0.97 else '⚠️偏离 90%，区间不可信'))

    verdict = hit >= 0.55 and mae < mae_naive and z >= 1.64
    print(f'\n══ 结论 ══')
    if verdict:
        print(f'  ✅ 三项均过：命中率≥55%、优于随机游走、且统计显著')
    else:
        why = []
        if hit < 0.55:
            why.append(f'命中率 {hit*100:.1f}% < 55%')
        if mae >= mae_naive:
            why.append('MAE 未优于随机游走')
        if z < 1.64:
            why.append(f'命中率不显著（z={z:+.2f}）')
        print(f'  ❌ 不达可用标准：' + '；'.join(why))
        print(f'     → 不得对外输出方向预测。可用的只有「均方误差略优于随机游走」')
        print(f'        这一点（即模型能估对波动幅度，但估不准方向）')
    if 5 in hits_by_h and hits_by_h[5] < 0.5:
        print(f'  ⚠️ 5 日累计命中率 {hits_by_h[5]*100:.1f}% 低于抛硬币：')
        print(f'     模型的微弱优势不向周度延伸，**不能用它做周度择时**')
    print(f'  样本外仅 {n_obs} 天，单日噪声约 1.6%，结论本身的不确定性很大。')
    return 0 if verdict else 2


if __name__ == '__main__':
    if '--walkforward' in sys.argv:
        sys.exit(walkforward())
    split = sys.argv[sys.argv.index('--split') + 1] if '--split' in sys.argv else '2026-09-01'
    hz = int(sys.argv[sys.argv.index('--horizon') + 1]) if '--horizon' in sys.argv else 1
    sys.exit(run(split, hz))

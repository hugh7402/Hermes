# -*- coding: utf-8 -*-
"""归因模块：解释金价为什么涨跌（两层结构）

════════════ 为什么必须分两层 ════════════
如果把 GLD/GC=F 当成因子去回归 Au99.99，R² 能到 0.95，但那是
**自己解释自己**，对理解宏观毫无贡献。所以拆成：

  A 层（宏观 → 国际金价）target = Δln(GLD)
     因子 = Δ实际利率 / Δ美元 / ΔVIX / CFTC 持仓变动 / 动量
     这一层回答“黄金为什么动”，对应 WGC GRAM 的因子分类

  B 层（国际金价 + 汇率 → 人民币金价）target = Δln(Au99.99)
     因子 = Δln(GLD) / Δln(USDCNY)
     残差就是「国内溢价变动」——它也是信息，不是误差

════════════ 用法 ════════════
  python3 attribution.py                    # 全样本拟合 + 昨日归因
  python3 attribution.py --train-end 2026-08-31   # 只用该日之前拟合
"""
import csv
import datetime as dt
import math
import pathlib
import sys

import numpy as np

DATA = pathlib.Path(__file__).resolve().parent.parent / 'data'
PANEL = DATA / 'panel.csv'

FACTORS_A = ['d_tips', 'r_dxy', 'r_vix', 'z_cftc', 'mom20']
LABEL = {
    'd_tips': '实际利率变动', 'r_dxy': '美元指数', 'r_vix': 'VIX(风险)',
    'z_cftc': 'CFTC 持仓变动', 'mom20': '20日动量',
    'r_gld': '国际金价', 'r_fx': '人民币汇率',
}


# ──────────────────── 数据准备 ────────────────────

def load_panel() -> list[dict]:
    with open(PANEL, encoding='utf-8') as f:
        return list(csv.DictReader(f))


def build(rows, lag: int = 0) -> list[dict]:
    """算收益率与因子。

    lag=0 → 用**同期**列（解释用）
    lag=1 → 用 **`_l`** 滞后列（预测用，不偷未来）

    第一个 21 日丢弃（20 日动量需要历史）。
    """
    def col(name):
        key = name + '_l' if lag else name
        return [float(r[key]) for r in rows]

    au = [float(r['au_close']) for r in rows]
    gld, fx, dxy, vix, tips, cftc = (col('gld'), col('usdcny'), col('dxy'),
                                     col('vix'), col('tips10y'), col('cftc_net_long'))
    n = len(rows)
    out = []
    for i in range(21, n):
        d = {
            'date': rows[i]['date'],
            'r_au': math.log(au[i] / au[i - 1]),
            'r_gld': math.log(gld[i] / gld[i - 1]),
            'r_fx': math.log(fx[i] / fx[i - 1]),
            'd_tips': tips[i] - tips[i - 1],
            'r_dxy': math.log(dxy[i] / dxy[i - 1]),
            'r_vix': math.log(vix[i] / vix[i - 1]),
            'z_cftc': (cftc[i] - cftc[i - 1]) / 100000.0,   # 万手
            'mom20': math.log(au[i - 1] / au[i - 21]),
            'au_close': au[i],
        }
        out.append(d)
    return out


# ────────────────────── OLS ──────────────────────

def ols(y, X):
    """多元回归。X 不带常数列，内部补。返 dict(beta, se, t, r2, n, k)"""
    y = np.asarray(y, dtype=float)
    X = np.asarray(X, dtype=float)
    n, k = X.shape
    X1 = np.column_stack([np.ones(n), X])
    # 最小二乘
    coef, *_ = np.linalg.lstsq(X1, y, rcond=None)
    resid = y - X1 @ coef
    ss_res = float(resid @ resid)
    ss_tot = float(((y - y.mean()) ** 2).sum())
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0
    dof = max(n - k - 1, 1)
    sigma2 = ss_res / dof
    try:
        cov = sigma2 * np.linalg.inv(X1.T @ X1)
        se = np.sqrt(np.diag(cov))
    except np.linalg.LinAlgError:
        se = np.full(k + 1, np.nan)
    beta = coef[1:]
    t = beta / se[1:] if se[1] is not None else np.full(k, np.nan)
    adj = 1 - (1 - r2) * (n - 1) / dof
    return {'beta': beta, 'se': se[1:], 't': t, 'r2': r2, 'adj_r2': adj,
            'n': n, 'k': k, 'const': coef[0], 'sigma': math.sqrt(sigma2)}


def vif(X):
    """方差膨胀因子。>5 说明多重共线性重，系数不稳。"""
    X = np.asarray(X, dtype=float)
    out = {}
    for j in range(X.shape[1]):
        others = np.delete(X, j, axis=1)
        if others.shape[1] == 0:
            out[j] = 1.0
            continue
        r = ols(X[:, j], others)
        out[j] = 1 / (1 - r['r2']) if r['r2'] < 1 else float('inf')
    return out


def fmt_pct(x):
    return f'{x*100:+.3f}%'


def report(data, train_end=None):
    rows = [d for d in data if (train_end is None or d['date'] <= train_end)]
    if len(rows) < 40:
        print(f'  ❌ 样本只有 {len(rows)} 条，不够回归')
        return None

    # ── A 层：宏观 → 国际金价 ──
    ya = [d['r_gld'] for d in rows]
    Xa = [[d[f] for f in FACTORS_A] for d in rows]
    ra = ols(ya, Xa)
    print(f"\n══ A 层：宏观 → 国际金价（Δln GLD）══")
    print(f"  样本 {ra['n']} 天（{rows[0]['date']} → {rows[-1]['date']}）")
    print(f"  R² = {ra['r2']:.4f}   调整 R² = {ra['adj_r2']:.4f}   残差标准差 {ra['sigma']*100:.3f}%/天")
    print(f"  {'因子':<16}{'系数':>12}{'t 值':>9}   {'标准化贡献(全期)':>16}")
    v = vif(Xa)
    for j, f in enumerate(FACTORS_A):
        # 标准化贡献 = beta * sd(factor) / sd(target)
        sd_f = float(np.std([d[f] for d in rows], ddof=1))
        sd_y = float(np.std(ya, ddof=1))
        contrib = ra['beta'][j] * sd_f / sd_y if sd_y else 0
        flag = ' ⚠️VIF高' if v[j] > 5 else ''
        print(f"  {LABEL[f]:<16}{ra['beta'][j]:>12.4f}{ra['t'][j]:>9.2f}   {contrib:>15.2%}{flag}")

    # ── B 层：国际金价 + 汇率 → 人民币金价 ──
    yb = [d['r_au'] for d in rows]
    Xb = [[d['r_gld'], d['r_fx']] for d in rows]
    rb = ols(yb, Xb)
    print(f"\n══ B 层：国际金价 + 汇率 → 人民币金价（Δln Au99.99）══")
    print(f"  R² = {rb['r2']:.4f}   调整 R² = {rb['adj_r2']:.4f}   残差标准差 {rb['sigma']*100:.3f}%/天")
    for j, f in enumerate(['r_gld', 'r_fx']):
        print(f"  {LABEL[f]:<16}β = {rb['beta'][j]:>8.4f}   t = {rb['t'][j]:>6.2f}")
    return {'A': ra, 'B': rb, 'rows': rows, 'vif': v}


def attribute_yesterday(res, data):
    """把最新一天的 Au99.99 涨跌拆成三条。"""
    d = data[-1]
    bA, bB = res['A'], res['B']
    print(f"\n══ 昨日归因：{d['date']} ══")
    print(f"  上金所 Au99.99 涨跌 {fmt_pct(d['r_au'])}")
    c_gld = bB['beta'][0] * d['r_gld']
    c_fx = bB['beta'][1] * d['r_fx']
    resid = d['r_au'] - c_gld - c_fx
    print(f"    国际金价贡献 {fmt_pct(c_gld)}   （国际金价本身 {fmt_pct(d['r_gld'])}）")
    print(f"    汇率贡献     {fmt_pct(c_fx)}   （人民币 {fmt_pct(d['r_fx'])}）")
    print(f"    国内溢价残差 {fmt_pct(resid)}")
    print(f"\n  国际金价为何动（A 层拆解）：")
    tot = 0.0
    for j, f in enumerate(FACTORS_A):
        c = bA['beta'][j] * d[f]
        tot += c
        print(f"    {LABEL[f]:<14} {d[f]:>10.5f} × {bA['beta'][j]:>8.4f} = {fmt_pct(c)}")
    print(f"    {'残差':<14} {'':>10}   {'':>8}   {fmt_pct(d['r_gld'] - tot)}")
    print(f"    {'合计':<14} {'':>10}   {'':>8}   {fmt_pct(d['r_gld'])}")


def main() -> int:
    train_end = None
    if '--train-end' in sys.argv:
        train_end = sys.argv[sys.argv.index('--train-end') + 1]
    if not PANEL.exists():
        print('  ❌ 先跑 backfill.py 生成面板')
        return 1
    # 归因用同期列；要预测必须用 build(lag=1)
    data = build(load_panel(), lag=0)
    print(f'══ 归因模块（同期对齐，{len(data)} 个交易日）══')
    res = report(data, train_end)
    if res:
        attribute_yesterday(res, data)
    return 0


if __name__ == '__main__':
    sys.exit(main())

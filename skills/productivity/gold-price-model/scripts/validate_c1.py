# -*- coding: utf-8 -*-
"""C1（实际利率见顶回落）单信号 walk-forward 验证

════════════ 为什么不能直接信前面那个 +2.36% ════════════
前面那份检验有两个毛病：
  1. 把「信号为真的每一天」当独立样本，但 124 个命中日里大量是连续重叠的，
     实际是同一波行情数了一百遍。
  2. 没区分「状态」和「事件」。买点只发生在**信号从关到开的那一刻**，
     之后一直亮着的日子里没有增量信息。

所以本脚本做两件事：
  A. 状态检验（描述性）：开/关两组的未来收益差
  B. **事件检验（可执行）**：只在 off→on 转换当天记一次，看之后 20/60 日

═══════════ 前视偏差 ══════════
TIPS 是美财政部当晚发布，北京 D+1 才看得到 → 判定 D 日信号时只能用
D-1 及之前的 TIPS。脚本内已错位。

用法：
  python3 validate_c1.py
"""
import math
import numpy as np

import backtest as BT

NEED = ('d_tips',)      # 仅作参考，真正的信号用水平值算


def main():
    panel = BT.load()
    au = [float(r['au_close']) for r in panel]
    tips_l = [float(r['tips10y_l']) for r in panel]   # 滞后，防前视
    dates = [r['date'] for r in panel]
    n = len(au)

    # 信号：D 日判定时看 D-1 及之前的 TIPS，从 20 日高点回落 ≥15bp
    sig = [False] * n
    for i in range(21, n):
        w = tips_l[i - 20:i + 1]
        sig[i] = (max(w) - tips_l[i]) >= 0.15

    def fwd(i, h, kind='ret'):
        j = min(i + h, n - 1)
        if kind == 'ret':
            return (au[j] / au[i] - 1) * 100
        seg = au[i:j + 1]
        return (min(seg) / au[i] - 1) * 100          # 区间内最大回撤

    valid = list(range(21, n - 60))
    base20 = np.mean([fwd(i, 20) for i in valid])
    base60 = np.mean([fwd(i, 60) for i in valid])
    up20 = np.mean([fwd(i, 20) > 0 for i in valid]) * 100
    print(f'══ C1 单信号验证 ══')
    print(f'  样本 {n} 天（{dates[0]} → {dates[-1]}），可验证 {len(valid)} 天')
    print(f'  基准：20日 {base20:+.2f}%（上涨率 {up20:.0f}%）　60日 {base60:+.2f}%\n')

    # ── A. 状态检验 ──
    on = [i for i in valid if sig[i]]
    off = [i for i in valid if not sig[i]]
    print(f'══ A. 状态检验（描述性）══')
    print(f'  信号开 {len(on)} 天 / 关 {len(off)} 天')
    for h in (20, 60):
        a = np.mean([fwd(i, h) for i in on])
        b = np.mean([fwd(i, h) for i in off])
        print(f'    {h:>2}日：开 {a:+7.2f}%　关 {b:+7.2f}%　差 {a-b:+7.2f}%')

    # ── B. 事件检验（可执行）──
    onsets = [i for i in valid if sig[i] and not sig[i - 1]]
    print(f'\n══ B. 事件检验：信号从关→开 共 {len(onsets)} 次 ══')
    print(f'  {"日期":<13}{"金价":>9}{"+20日":>9}{"+60日":>9}{"20日内最大回撤":>15}{"60日内最大回撤":>15}')
    for i in onsets:
        print(f'  {dates[i]:<13}{au[i]:>9.2f}{fwd(i,20):>8.1f}%{fwd(i,60):>8.1f}%'
              f'{fwd(i,20,"mdd"):>14.1f}%{fwd(i,60,"mdd"):>14.1f}%')

    if onsets:
        r20 = [fwd(i, 20) for i in onsets]
        r60 = [fwd(i, 60) for i in onsets]
        m20 = [fwd(i, 20, 'mdd') for i in onsets]
        m60 = [fwd(i, 60, 'mdd') for i in onsets]
        k = len(r20)
        print(f'\n  事件汇总（n={k}，独立样本就是 {k} 个，不重叠）：')
        print(f'    20日 平均 {np.mean(r20):+.2f}%（基准 {base20:+.2f}%，超额 {np.mean(r20)-base20:+.2f}%）'
              f'　上涨 {sum(1 for x in r20 if x>0)}/{k}')
        print(f'    60日 平均 {np.mean(r60):+.2f}%（基准 {base60:+.2f}%，超额 {np.mean(r60)-base60:+.2f}%）'
              f'　上涨 {sum(1 for x in r60 if x>0)}/{k}')
        print(f'    20日内最大回撤 平均 {np.mean(m20):+.2f}%，最差 {min(m20):+.2f}%')
        print(f'    60日内最大回撤 平均 {np.mean(m60):+.2f}%，最差 {min(m60):+.2f}%')

        # 显著性（事件样本独立，可直接用二项/单样本 t）
        if k >= 3:
            se = np.std(r20, ddof=1) / math.sqrt(k)
            t = (np.mean(r20)) / se if se > 0 else 0
            print(f'\n    20日均值 t = {t:+.2f}（|t|>2.78 为 n={k} 时 5% 临界）')
            print(f'    → {"✅ 统计上可区分于 0" if abs(t) > 2.78 else "❌ 无法区别于 0，样本太少"}')

    # ── C. 稳定性：分两半 ──
    mid = n // 2
    print(f'\n══ C. 稳定性：前后两半分别看事件表现 ══')
    for label, seg in (('前半', [i for i in onsets if i < mid]),
                       ('后半', [i for i in onsets if i >= mid])):
        if not seg:
            print(f'  {label}：无事件')
            continue
        r = [fwd(i, 20) for i in seg]
        print(f'  {label}（{len(seg)} 次）：20日平均 {np.mean(r):+.2f}%　上涨 {sum(1 for x in r if x>0)}/{len(r)}')

    # ── D. 结论 ──
    print(f'\n══ 结论 ══')
    if len(onsets) < 5:
        print(f'  ❌ 只有 {len(onsets)} 个独立事件，**样本不足以下结论**。')
        print(f'     前面那个「+2.36% 超额」是 124 个重叠日造出来的，不能当依据。')
        print(f'     → 建议：C1 只当「背景改善」看待，不当买入信号；')
        print(f'       如果要用，必须先把样本拉到 3–5 年以上（需更早的 TIPS 历史）。')
    else:
        r20 = [fwd(i, 20) for i in onsets]
        ex = np.mean(r20) - base20
        print(f'  {len(onsets)} 个事件，20日超额 {ex:+.2f}%。' if ex > 0 else
              f'  {len(onsets)} 个事件，20日超额 {ex:+.2f}%（负，信号无效）。')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

# -*- coding: utf-8 -*-
"""回填历史面板 → data/panel.csv

════════ 前视偏差（look-ahead bias）是本脚本最要紧的事 ════════
解释 A 股黄金 D 日的涨跌，只能用 **D-1 及更早已知** 的信息：
  • 美债实际收益率：财政部当晚（ET）发布 → 北京 D+1 才看得到
  • 美股/黄金期货/VIX/美元指数：美东 D 日收盘 = 北京 D+1 凌晨
  • CFTC COT：报告日（周二）持仓，周五 15:30 ET 才公布 → 北京周六
如果不错位，回测出来的 R² 会虚高一大截，上实盘立刻打脸。

因此：美系序列一律 asof(D - LAG)，LAG 默认 1；CFTC 单独用 LAG_CFTC=5。

用法：
  python3 backfill.py               # 构建 panel.csv
  python3 backfill.py --years 2025,2026
"""
import csv
import datetime as dt
import pathlib
import sys
from urllib.parse import quote

import net

DATA = pathlib.Path(__file__).resolve().parent.parent / 'data'
PANEL = DATA / 'panel.csv'

LAG = 1          # 美系日频数据错位（交易日）
LAG_CFTC = 5     # CFTC 报告中位延迟


def _d(s):
    """多种日期格式 → date。

    CFTC Socrata 返的是 ISO 时间戳（`2026-11-17T00:00:00.000`），
    先截前 10 位再用；不截会直接 ValueError 把整列变空（踩过）。
    """
    s = str(s).strip()[:10]
    for fmt in ('%Y-%m-%d', '%m/%d/%Y', '%Y/%m/%d'):
        try:
            return dt.datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    raise ValueError(f'认不出的日期：{s}')


def asof(series: dict, day: dt.date, lag: int = 0):
    """取 day-lag 当天或之前最近的可用值。lag 用交易日近似（忽略节假日，取日历日）。

    panel 是日频且避开周末即可——循环里已经只在交易日调用。
    """
    if not series:
        return None
    cands = [d for d in series if d <= day]
    if not cands:
        return None
    return series[max(cands)]


def shift(day: dt.date, n: int) -> dt.date:
    """往回推 n 个「有效日」：先按日历日退，再跳过周末。"""
    d = day
    moved = 0
    while moved < n:
        d -= dt.timedelta(days=1)
        if d.weekday() < 5:
            moved += 1
    return d


# ────────────────────── 各序列拉取 ──────────────────────

def get_tips(years):
    """财政部官方实际收益率曲线（直连，免 key）"""
    out = {}
    for y in years:
        u = ('https://home.treasury.gov/resource-center/data-chart-center/interest-rates/'
             f'daily-treasury-rates.csv/{y}/all?type=daily_treasury_real_yield_curve'
             f'&field_tdr_date_value={y}&_format=csv')
        try:
            txt = net.fetch(u, via='direct')
            for r in csv.DictReader(txt.splitlines()):
                v = net.num(r.get('10 YR'))
                if v is not None:
                    out[_d(r['Date'])] = v
            print(f'  ✅ TIPS {y}  {len(out)} 个日期累计')
        except Exception as e:
            print(f'  ❌ TIPS {y}  {type(e).__name__}: {str(e)[:50]}')
    return out


def get_yahoo(sym, rng='2y'):
    """Yahoo 日线收盘（代理）"""
    u = (f'https://query1.finance.yahoo.com/v8/finance/chart/{quote(sym, safe="")}'
         f'?interval=1d&range={rng}')
    d = net.fetch_json(u, via='proxy')
    r = d['chart']['result'][0]
    ts = r.get('timestamp') or []
    cl = r['indicators']['quote'][0].get('close') or []
    out = {}
    for t, c in zip(ts, cl):
        if c is None:
            continue
        day = dt.datetime.fromtimestamp(t, dt.UTC).date()
        out[day] = float(c)
    return out


def get_au9999():
    """上金所 Au99.99 日线（东财，直连）——回测的目标变量"""
    u = ('https://push2his.eastmoney.com/api/qt/stock/kline/get?'
         'secid=118.AU9999&fields1=f1,f2,f3&fields2=f51,f53&klt=101&fqt=0'
         '&end=20500101&lmt=800')
    d = net.fetch_json(u, via='direct')
    rows = []
    for k in d['data']['klines']:
        p = k.split(',')
        rows.append((_d(p[0]), float(p[1])))
    return rows


def get_cftc():
    """CFTC 黄金（COMEX 主合约）非商业净多头，周频（代理）"""
    u = ('https://publicreporting.cftc.gov/resource/6dca-aqww.json?'
         '$where=market_and_exchange_names%20like%20%27%25GOLD%25%27'
         '&$order=report_date_as_yyyy_mm_dd%20DESC&$limit=500')
    rows = net.fetch_json(u, via='proxy')
    out = {}
    for r in rows:
        name = str(r.get('market_and_exchange_names', '')).upper()
        if 'COMMODITY EXCHANGE' not in name or 'MICRO' in name or 'COINBASE' in name:
            continue
        lo = net.num(r.get('noncomm_positions_long_all'))
        sh = net.num(r.get('noncomm_positions_short_all'))
        if lo is None or sh is None:
            continue
        out[_d(r['report_date_as_yyyy_mm_dd'])] = int(lo - sh)
    return out


# ────────────────────── 主流程 ──────────────────────

def main() -> int:
    years = [2025, 2026]
    if '--years' in sys.argv:
        years = [int(x) for x in sys.argv[sys.argv.index('--years') + 1].split(',')]

    print('══ 回填历史面板 ══')
    if not net.ensure_proxy():
        print('  ⚠️ 代理不可用，Yahoo/CFTC 会缺，面板不完整')

    tips = get_tips(years)
    yh = {}
    for sym, key in [('DX-Y.NYB', 'dxy'), ('^VIX', 'vix'), ('GLD', 'gld'),
                     ('GC=F', 'gc_fut'), ('ZQ=F', 'zq'), ('CNY=X', 'usdcny')]:
        try:
            yh[key] = get_yahoo(sym)
            ks = sorted(yh[key])
            print(f'  ✅ {key:<8} {len(ks)} 条  {ks[0]} → {ks[-1]}')
        except Exception as e:
            yh[key] = {}
            print(f'  ❌ {key:<8} {type(e).__name__}: {str(e)[:50]}')

    au = get_au9999()
    print(f'  ✅ Au99.99  {len(au)} 条  {au[0][0]} → {au[-1][0]}')
    try:
        cftc = get_cftc()
        ks = sorted(cftc)
        print(f'  ✅ CFTC     {len(ks)} 周  {ks[0]} → {ks[-1]}')
    except Exception as e:
        cftc = {}
        print(f'  ❌ CFTC     {type(e).__name__}: {str(e)[:50]}')

    rows = []
    for i, (day, close) in enumerate(au):
        d_us = shift(day, LAG)                    # 美系数据可用截止日（预测用）
        d_cftc = shift(day, LAG_CFTC)
        zq = asof(yh.get('zq', {}), d_us)
        r = {
            'date': str(day),
            'au_close': close,
            # ── 同期列：事后「解释」用（上金所 D 日收盘 vs 国际 D 日 K 线，
            #    后者覆盖了 D 日亚洲时段，所以对齐是对的）
            'tips10y': asof(tips, day),
            'dxy': asof(yh.get('dxy', {}), day),
            'vix': asof(yh.get('vix', {}), day),
            'gld': asof(yh.get('gld', {}), day),
            'gc_fut': asof(yh.get('gc_fut', {}), day),
            'usdcny': asof(yh.get('usdcny', {}), day),
            'cftc_net_long': asof(cftc, day),
            # ── 滞后列：事前「预测」用（D 日收盘时只能拿到 D-1 及以前的）
            'tips10y_l': asof(tips, d_us),
            'dxy_l': asof(yh.get('dxy', {}), d_us),
            'vix_l': asof(yh.get('vix', {}), d_us),
            'gld_l': asof(yh.get('gld', {}), d_us),
            'gc_fut_l': asof(yh.get('gc_fut', {}), d_us),
            'usdcny_l': asof(yh.get('usdcny', {}), d_us),
            'zq_rate_l': round(100 - zq, 3) if zq else None,
            'cftc_net_long_l': asof(cftc, d_cftc),
        }
        rows.append(r)

    DATA.mkdir(parents=True, exist_ok=True)
    # 裁剪到「所有因子都有值」的共同区间，避免半途缺因子污染回归
    rows = [r for r in rows if all(r[k] is not None for k in r if k != 'date')]
    if not rows:
        print('\n  ❌ 没有一行因子齐全，先查数据源')
        return 1
    fields = list(rows[0].keys())
    with open(PANEL, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    complete = sum(1 for r in rows if all(r[k] is not None for k in fields if k != 'date'))
    print(f'\n  已写入 {PANEL}')
    print(f'  {len(rows)} 行 × {len(fields)} 列，因子齐全的行：{complete}（{complete/len(rows)*100:.0f}%）')
    print(f'  区间 {rows[0]["date"]} → {rows[-1]["date"]}')
    if complete < len(rows) * 0.8:
        print('  ⚠️ 完整率低于 80%，回测前先补齐数据')
    return 0


if __name__ == '__main__':
    sys.exit(main())

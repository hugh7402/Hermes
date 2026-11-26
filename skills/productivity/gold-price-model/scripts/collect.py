# -*- coding: utf-8 -*-
"""采集黄金模型当日全部因子 → data/factors.csv

设计原刚：**单个因子失败不许搞死整轮**。每个采集器独立 try/except，
最后打一张成功/失败表，缺哪个因子一目了然（不静默降级）。

用法：
  python3 collect.py            # 采集并追写 data/factors.csv
  python3 collect.py --check    # 只验源，不写盘
"""
import csv
import datetime as dt
import math
import pathlib
import statistics as st
import sys

import net

DATA = pathlib.Path(__file__).resolve().parent.parent / 'data'
FACTORS = DATA / 'factors.csv'


# ────────────────────────── 各因子采集器 ──────────────────────────

def c_au_history():
    """上金所 Au99.99 日线（东财，直连）→ 收盘序列 + 均线/RSI/波动率"""
    u = ('https://push2his.eastmoney.com/api/qt/stock/kline/get?'
         'secid=118.AU9999&fields1=f1,f2,f3&fields2=f51,f53&klt=101&fqt=0'
         '&end=20500101&lmt=400')
    d = net.fetch_json(u, via='direct')
    ks = d['data']['klines']
    px = [float(k.split(',')[1]) for k in ks]
    dates = [k.split(',')[0] for k in ks]
    if len(px) < 65:
        raise ValueError(f'日线只有 {len(px)} 条，不足以算 60 日均线')
    rets = [math.log(px[i + 1] / px[i]) for i in range(len(px) - 1)]
    sd = st.pstdev(rets[-250:]) if len(rets) >= 250 else st.pstdev(rets)
    # RSI-14
    gains = [max(rets[i], 0) for i in range(-14, 0)]
    losses = [max(-rets[i], 0) for i in range(-14, 0)]
    ag, al = sum(gains) / 14, sum(losses) / 14
    rsi = 100.0 if al == 0 else 100 - 100 / (1 + ag / al)
    return {
        'au_close': round(px[-1], 2),
        'au_date': dates[-1],
        'au_ma20': round(sum(px[-20:]) / 20, 2),
        'au_ma60': round(sum(px[-60:]) / 60, 2),
        'au_rsi14': round(rsi, 1),
        'au_vol_daily_pct': round(sd * 100, 2),
        'au_vol_weekly_pct': round(sd * math.sqrt(5) * 100, 2),
        'au_vol_annual_pct': round(sd * math.sqrt(252) * 100, 1),
        '_px': px,
    }


def c_spot_fx():
    """伦敦金 + 美元指数 + USDCNY（新浪，直连）"""
    d = net.sina('hf_XAU,DINIW,fx_susdcny')
    xau = net.num(d.get('hf_XAU', [None])[0])
    dxy_fields = d.get('DINIW', [])
    dxy = None
    for f in dxy_fields:            # 新浪 DINIW 第1个是时间，取第一个能转的数值
        v = net.num(f)
        if v and v > 50:
            dxy = v
            break
    fx_fields = d.get('fx_susdcny', [])
    fx = None
    for f in fx_fields[1:3]:
        v = net.num(f)
        if v and 5 < v < 9:
            fx = v
            break
    if xau is None:
        raise ValueError('伦敦金取不到')
    return {'xau_usd': xau, 'dxy': dxy, 'usdcny': fx}


def c_tips():
    """10Y TIPS 实际利率（美财政部官方 CSV，直连，免 key）"""
    u = ('https://home.treasury.gov/resource-center/data-chart-center/interest-rates/'
         'daily-treasury-rates.csv/2026/all?type=daily_treasury_real_yield_curve'
         '&field_tdr_date_value=2026&_format=csv')
    txt = net.fetch(u, via='direct')
    rows = list(csv.DictReader(txt.splitlines()))
    if not rows:
        raise ValueError('财政部 CSV 空')
    r = rows[0]                     # 最新在前
    return {'tips10y': net.num(r.get('10 YR')), 'tips_date': r.get('Date')}


def c_debt():
    """美国国债总额（财政部 FiscalData，直连）"""
    u = ('https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v2/accounting/'
         'od/debt_to_penny?sort=-record_date&page[size]=1')
    d = net.fetch_json(u, via='direct')
    row = d['data'][0]
    return {'us_debt_tn': round(float(row['tot_pub_debt_out_amt']) / 1e12, 3),
            'us_debt_date': row['record_date']}


def _yahoo(sym, rng='5d'):
    u = (f'https://query1.finance.yahoo.com/v8/finance/chart/{urllib_quote(sym)}'
         f'?interval=1d&range={rng}')
    d = net.fetch_json(u, via='proxy')
    res = d['chart']['result'][0]
    return res['meta']['regularMarketPrice'], res['timestamp'][-1]


def urllib_quote(s):
    from urllib.parse import quote
    return quote(s, safe='')


def c_vix():
    v, _ = _yahoo('^VIX')
    return {'vix': round(float(v), 2)}


def c_etf_futures():
    """GLD（ETF）+ GC=F（期金）+ ZQ=F（联邦基金利率期货）"""
    gld, _ = _yahoo('GLD')
    gc, _ = _yahoo('GC=F')
    zq, _ = _yahoo('ZQ=F')
    return {'gld_usd': round(float(gld), 2),
            'gc_fut_usd': round(float(gc), 2),
            'zq_fed_funds': round(100 - float(zq), 3)}   # ZQ 报价=100-利率


def c_cftc():
    """CFTC COT：黄金非商业净多头（周频，代理）"""
    base = ('https://publicreporting.cftc.gov/resource/6dca-aqww.json?'
            '$order=report_date_as_yyyy_mm_dd%20DESC&$limit=200')
    rows = net.fetch_json(base, via='proxy')
    gold = [r for r in rows if 'GOLD' in str(r.get('market_and_exchange_names', '')).upper()]
    if not gold:
        raise ValueError('CFTC 返回里找不到 GOLD 合约')
    # 只认主合约（COMEX），排除微型/迷你
    main = [r for r in gold if 'COMMODITY EXCHANGE' in str(r.get('market_and_exchange_names', '')).upper()
            and 'MICRO' not in str(r.get('market_and_exchange_names', '')).upper()]
    r = (main or gold)[0]
    longs = net.num(r.get('noncomm_positions_long_all'))
    shorts = net.num(r.get('noncomm_positions_short_all'))
    if longs is None or shorts is None:
        raise ValueError(f'CFTC 字段缺失: {list(r.keys())[:6]}')
    return {'cftc_net_long': int(longs - shorts), 'cftc_date': r.get('report_date_as_yyyy_mm_dd', '')[:10]}


# ────────────────────────── 主流程 ──────────────────────────

COLLECTORS = [
    ('au_history', c_au_history),
    ('spot_fx', c_spot_fx),
    ('tips', c_tips),
    ('debt', c_debt),
    ('vix', c_vix),
    ('etf_futures', c_etf_futures),
    ('cftc', c_cftc),
]


def main() -> int:
    check_only = '--check' in sys.argv
    need_proxy = True
    print(f'══ 黄金因子采集 {dt.date.today()} ══')
    if net.ensure_proxy():
        print('  [net] 代理可用')
    else:
        print('  [net] ⚠️ 代理不可用，境外因子（VIX/GLD/GC/ZQ/CFTC）将缺失')

    out, ok, fail = {}, [], []
    for name, fn in COLLECTORS:
        try:
            r = fn()
            out.update({k: v for k, v in r.items() if not k.startswith('_')})
            ok.append(name)
            brief = ', '.join(f'{k}={v}' for k, v in r.items() if not k.startswith('_'))
            print(f'  ✅ {name:<12} {brief[:110]}')
        except Exception as e:
            fail.append((name, type(e).__name__, str(e)[:70]))
            print(f'  ❌ {name:<12} {type(e).__name__}: {str(e)[:60]}')

    # 交叉校验：伦敦金 → 人民币克价 vs 上金所
    xau, fx, au = out.get('xau_usd'), out.get('usdcny'), out.get('au_close')
    if all(v is not None for v in (xau, fx, au)):
        imp = xau / 31.1035 * fx
        gap = (au - imp) / imp * 100
        out['import_parity'] = round(imp, 2)
        out['premium_pct'] = round(gap, 2)
        print(f'\n  交叉校验：${xau} × {fx} ÷ 31.1035 = {imp:.2f} 元/克，'
              f'上金所 {au}，内外价差 {gap:+.2f}%')
        if abs(gap) > 3:
            print('  ⚠️ 内外价差超 3%，某个源可能失真，先核数据再用')

    print(f'\n  成功 {len(ok)}/{len(COLLECTORS)}：{ok}')
    if fail:
        print(f'  失败：{[(n, e) for n, e, _ in fail]}')

    if check_only:
        print('  --check 模式，不写盘')
        return 0 if not fail else 1

    DATA.mkdir(parents=True, exist_ok=True)
    out['date'] = str(dt.date.today())
    fields = ['date'] + sorted(k for k in out if k != 'date')
    exists = FACTORS.exists()
    old = []
    if exists:
        with open(FACTORS, encoding='utf-8') as f:
            old = [r for r in csv.DictReader(f) if r.get('date') != out['date']]
    with open(FACTORS, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in old:
            w.writerow({k: r.get(k, '') for k in fields})
        w.writerow({k: out.get(k, '') for k in fields})
    print(f'  已写入 {FACTORS}（共 {len(old) + 1} 天）')
    return 0 if not fail else 1


if __name__ == '__main__':
    sys.exit(main())

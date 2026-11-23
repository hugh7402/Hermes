#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""黄金每日简报 — 招商银行黄金账户口径

口径铁律（来自 investment-portfolio-review skill）：
  1. 招行黄金账户按实时卖出价兑付，持仓金额 = 克数 × 卖出价
  2. 双边总点差 5 元/克（买卖各 2.5），中间价挂钩上金所 Au99.99
  3. 算收益/仓位/结论一律用卖出价，绝不用买入价
  4. 取不到价就说取不到，不编
"""
import json, csv, os, sys, urllib.request, datetime, pathlib, time

os.environ['TZ'] = 'Asia/Shanghai'   # cron 环境无 TZ，不设会走 UTC
try:
    time.tzset()
except Exception:
    pass

BASE = pathlib.Path('/opt/data/gold')
CFG = BASE / 'config.json'
HIST = BASE / 'history.csv'
UA = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64)'}
SINA = {**UA, 'Referer': 'https://finance.sina.com.cn'}

SPREAD = 5.0          # 双边总点差
SPREAD_SIDE = 2.5     # 单边


def fetch(url, timeout=15, hdr=None):
    req = urllib.request.Request(url, headers=hdr or UA)
    return urllib.request.urlopen(req, timeout=timeout).read().decode('utf-8', 'ignore')


def get_au9999():
    """上金所 Au99.99 实时 — 东方财富主，新浪备"""
    # 主：东方财富
    try:
        u = ('https://push2.eastmoney.com/api/qt/stock/get'
             '?secid=118.AU9999&fields=f43,f44,f45,f46,f60,f170,f58')
        d = json.loads(fetch(u)).get('data') or {}
        if d.get('f43'):
            return {
                'last': d['f43'] / 100, 'high': d['f44'] / 100,
                'low': d['f45'] / 100, 'open': d['f46'] / 100,
                'prev': d['f60'] / 100, 'pct': d['f170'] / 100,
                'name': d.get('f58') or '黄金9999', 'src': '东方财富',
            }
    except Exception:
        pass
    # 备：新浪
    try:
        t = fetch('https://hq.sinajs.cn/list=gds_AU9999', hdr=SINA)
        s = t.split('"')[1].split(',')
        return {'last': float(s[0]), 'high': float(s[4]), 'low': float(s[5]),
                'open': float(s[8]), 'prev': float(s[7]),
                'pct': None, 'name': 'Au99.99', 'src': '新浪'}
    except Exception:
        return None


def get_xau():
    """国际现货黄金 USD/oz — 新浪"""
    try:
        t = fetch('https://hq.sinajs.cn/list=hf_XAU', hdr=SINA)
        s = t.split('"')[1].split(',')
        return {'last': float(s[0]), 'prev': float(s[1]), 'high': float(s[4]),
                'low': float(s[5]), 'time': s[6], 'src': '新浪'}
    except Exception:
        return None


def load_state():
    with open(CFG, encoding='utf-8') as f:
        return json.load(f)


def append_hist(row):
    # 同日只留一条：先读出现有行，剔除今天的，再整体重写
    rows = []
    if HIST.exists():
        with open(HIST, encoding='utf-8') as f:
            rd = list(csv.reader(f))
        if rd:
            rows = [rd[0]] + [r for r in rd[1:] if r and r[0] != row[0]]
    new = not rows
    with open(HIST, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        if new:
            w.writerow(['日期', 'Au99.99', '招行卖出价', '持仓市值', '浮盈', '收益率%', '日内分位%'])
        for r in rows[1:] if rows else []:
            w.writerow(r)
        w.writerow(row)


def main():
    cfg = load_state()
    grams = cfg['grams']
    cost_px = cfg['cost_price']
    total_assets = cfg['total_assets']
    tgt_lo, tgt_hi = cfg['gold_target_low'], cfg['gold_target_high']

    au = get_au9999()
    xau = get_xau()
    today = datetime.date.today().isoformat()
    now = datetime.datetime.now().strftime('%H:%M')

    if not au:
        print(f'⚠️ 黄金简报 {today}\n\n上金所 Au99.99 行情连续两个源都取不到，'
              f'今天的简报无法生成。\n请检查网络后手动重试：'
              f'\n/opt/data/.venv/bin/python3 /opt/data/gold/gold_brief.py')
        return 1

    # ── 招行口径换算 ──────────────────────────────
    mid = au['last']
    sell = round(mid - SPREAD_SIDE, 2)     # 你的净值
    buy = round(mid + SPREAD_SIDE, 2)      # 银行的卖价，不是你的

    cost = cost_px * grams
    mv = sell * grams
    profit = mv - cost
    roi = profit / cost * 100

    # 日内分位
    rng = au['high'] - au['low']
    pct_pos = (sell - au['low']) / rng * 100 if rng > 0 else None

    # 仓位
    cur_pct = mv / total_assets * 100
    gap_lo = total_assets * tgt_lo / 100 - mv
    gap_hi = total_assets * tgt_hi / 100 - mv

    # ── 结论 ────────────────────────────────────
    if pct_pos is None:
        verdict = '日内区间数据不足，无法判断位置。'
    elif pct_pos >= 70:
        verdict = f'卖出价处于日内 {pct_pos:.0f}% 分位，属当天高位，不是加仓位置。'
    elif pct_pos <= 30:
        verdict = f'卖出价处于日内 {pct_pos:.0f}% 分位，属当天低位，可按分批节奏接一点。'
    else:
        verdict = f'卖出价处于日内 {pct_pos:.0f}% 分位，位置居中，观察为主。'

    if au.get('pct') is not None and au['pct'] >= 2 and pct_pos and pct_pos >= 70:
        verdict += '今日已涨 2% 以上且在高位，按既定节奏不追。'

    # ── 输出 ────────────────────────────────────
    L = []
    L.append(f'📊 黄金每日简报 · {today}')
    L.append('')
    L.append('【行情】上金所 Au99.99')
    pct_txt = f"（{au['pct']:+.2f}%）" if au.get('pct') is not None else ''
    L.append(f'  最新 {au["last"]:.2f}{pct_txt}　昨结 {au["prev"]:.2f}')
    L.append(f'  日内 {au["low"]:.2f} ~ {au["high"]:.2f}　今开 {au["open"]:.2f}')
    if xau:
        L.append(f'  国际现货 ${xau["last"]:.2f}/oz（{xau["time"]}）')
    L.append('')
    L.append('【你的账户】招行黄金账户口径')
    L.append(f'  持仓 {grams:g} 克　成本均价 {cost_px} 元/克')
    L.append(f'  你的卖出价 ≈ {sell:.2f}　（银行买入牌价 {buy:.2f}，不是你的净值）')
    L.append(f'  持仓市值 ≈ {mv:,.2f} 元')
    L.append(f'  浮动盈亏 ≈ {profit:+,.2f} 元（{roi:+.2f}%）')
    L.append(f'  点差摩擦 {grams:g} 克 × 5 = {grams*SPREAD:.0f} 元（占本金 {grams*SPREAD/cost*100:.2f}%，沉没成本）')
    L.append('')
    L.append('【位置与仓位】')
    if pct_pos is not None:
        L.append(f'  日内分位 {pct_pos:.0f}%（0%=最低，100%=最高）')
    L.append(f'  当前占总资产 {cur_pct:.2f}%（目标 {tgt_lo}%–{tgt_hi}%）')
    L.append(f'  距 {tgt_lo}% 还差 {gap_lo:,.0f} 元 ≈ {gap_lo/sell:.0f} 克')
    L.append(f'  距 {tgt_hi}% 还差 {gap_hi:,.0f} 元 ≈ {gap_hi/sell:.0f} 克')
    L.append('')
    L.append('【结论】')
    L.append('  ' + verdict)
    L.append('')
    L.append(f'· 数据源 {au["src"]}／{xau["src"] if xau else "国际盘缺失"}，取价时间 {now}')
    L.append('· 招行价按中间价=Au99.99、双边点差 5 元/克推算，与实际可能有几分钱差异，以 App 为准')

    msg = '\n'.join(L)
    print(msg)

    try:
        append_hist([today, au['last'], sell, round(mv, 2), round(profit, 2),
                     round(roi, 2), round(pct_pos, 1) if pct_pos is not None else ''])
    except Exception as e:
        print(f'\n[警告] 历史记录写入失败: {e}', file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main())

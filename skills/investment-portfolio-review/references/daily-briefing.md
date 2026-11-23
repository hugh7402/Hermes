# 每日行情简报自动化（cron）

把一个每日持仓/行情简报做成零 token 的定时推送。以招行黄金账户为例，换品种时只改取价与换算两段。

## 文件布局

| 路径 | 作用 |
|---|---|
| `/opt/data/scripts/gold_brief.py` | 主脚本。**必须在 `/opt/data/scripts/` 下**——cron 的 `script` 参数只接受该目录下的相对文件名，写绝对路径会被拒 |
| `/opt/data/gold/config.json` | 持仓配置：`grams` / `cost_price` / `total_assets` / `gold_target_low` / `gold_target_high` |
| `/opt/data/gold/history.csv` | 每日快照，同日只留一条 |

脚本内用绝对路径指向 config/history，所以脚本本身可以随意搬动。只用标准库，任何 python3 都能跑。

## 数据源（国内可直连，不需要代理）

```python
# 主：东方财富，干净 JSON，价格已放大 100 倍
# https://push2.eastmoney.com/api/qt/stock/get?secid=118.AU9999&fields=f43,f44,f45,f46,f60,f170,f58
#   f43 最新  f44 最高  f45 最低  f46 今开  f60 昨结  f170 涨跌幅×100  f58 名称

# 备：新浪，字符串数组，必须带 Referer
# https://hq.sinajs.cn/list=gds_AU9999   → 上金所 Au99.99
#   s[0] 最新  s[4] 最高  s[5] 最低  s[7] 昨结  s[8] 今开  s[6] 时间
# https://hq.sinajs.cn/list=hf_XAU       → 国际现货 USD/oz
#   s[0] 最新  s[1] 昨结  s[4] 最高  s[5] 最低  s[6] 时间
```

主源失败自动降级到备源；两个都取不到就输出「取不到，不编」，不要用旧价冒充当次价。

## 招行口径换算

中间价直接取 Au99.99 现价（与 App 实测贴合，不需要加基差）：

```python
sell = au_last - 2.5    # 你的净值，一切结论用它
buy  = au_last + 2.5    # 银行牌价，只展示，不用来算收益
mv   = sell * grams
profit = mv - cost_price * grams
```

## cron 四个必踩的坑

1. **最小环境没有 `TZ`**。`env -i` 下 `datetime.now()` 走 UTC，取价时间会显示成七小时前。脚本开头必须：
   ```python
   os.environ['TZ'] = 'Asia/Shanghai'
   try: time.tzset()
   except Exception: pass
   ```
2. **`hq.sinajs.cn` 不带 Referer 返回空**。`{'User-Agent': ..., 'Referer': 'https://finance.sina.com.cn'}` 两个头都要，否则国际盘那一行会静默缺失。
3. **`script` 参数只认文件名**。传绝对路径会被拒（提示 must be relative to `/opt/data/scripts/`），挪到该目录后传裸文件名。
4. **同日重跑会写重复行**。写历史前先读全表、剔除今天那行、再整体重写；否则手动补跑一次就多一条。

## 建 cron 的最省 token 形态

分析类简报不需要模型推理，用 `no_agent=true` + `script`，stdout 原样投递：

```
cronjob_manage(action='create',
               name='黄金每日简报',
               schedule='45 13 * * *',
               timezone='Asia/Shanghai',
               script='gold_brief.py',
               no_agent=True,
               deliver='origin',
               wrap_response='off',
               enabled_toolsets=[])
```

`wrap_response='off'` 去掉「Cronjob Response:」头尾，简报干净。改时间用 `action='update'` 只动 `schedule`，不要重建任务。

## 投产前自检

```bash
# 1. 模拟 cron 最小环境
env -i PATH=/usr/bin:/bin HOME=/opt/data /opt/data/scripts/gold_brief.py
# 2. 非 venv 解释器
/usr/bin/python3 /opt/data/scripts/gold_brief.py
# 3. 走 shebang 直接执行
/opt/data/scripts/gold_brief.py
```

三条都过才算能上。建完立刻 `cronjob_manage(action='run', job_id=...)` 打一次端到端——脚本能跑、定时器能触发、微信能收到，比只测脚本可信。

## 简报输出结构

```
📊 黄金每日简报 · {日期}

【行情】上金所 Au99.99
  最新 X（±Y%）　昨结 Z
  日内 最低 ~ 最高　今开 W
  国际现货 $N/oz（时间）

【你的账户】招行黄金账户口径
  持仓 N 克　成本均价 C 元/克
  你的卖出价 ≈ S　（银行买入牌价 B，不是你的净值）
  持仓市值 ≈ M 元
  浮动盈亏 ≈ ±P 元（±R%）
  点差摩擦 N 克 × 5 = X 元（占本金 Y%，沉没成本）

【位置与仓位】
  日内分位 Q%（0%=最低，100%=最高）
  当前占总资产 T%（目标 A%–B%）
  距 A% 还差 … 元 ≈ … 克

【结论】
  一句可执行结论

· 数据源 …／…，取价时间 HH:MM
· 招行价按中间价=Au99.99、双边点差 5 元/克推算，以 App 为准
```

结论必须可执行：「当天高位，不是加仓位置」／「当天低位，可按节奏接一点」／「位置居中，观察为主」，不要停在「注意风险」。日内分位 ≥70% 判高位、≤30% 判低位；当日已涨 2% 以上且在高位时补一句「按既定节奏不追」。

输出里所有星号记得去掉——微信不解析 `**加粗**`，会原样显示。

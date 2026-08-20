---
name: cn-hotel-booking-links
description: "推荐酒店/民宿时生成国内可打开的中文预订链接。"
version: 1.0.0
author: Emma + Hermes Agent
license: MIT
tags: [hotel, homestay, 民宿, 酒店, 预订, ctrip, 携程, travel, 推荐]
trigger: 用户要求推荐酒店/民宿/农家院，或要求发预订链接/打开链接时使用。尤其北京周边周末游（白河湾/金海湖/百里山水画廊）、亲子游场景。用户明确纠正过：境外站链接打不开且是英文，必须给携程中文链接。
related_skills: [multi-search-engine, weixin-gateway-troubleshooting]
---

# 国内酒店/民宿预订链接生成

给国内用户推荐酒店/民宿时，**只给国内可直接打开的中文链接**。用户实测纠正（2026-08-18）：境外站链接打不开、界面英文。

## 核心规则

1. **首选携程手机版**：`https://m.ctrip.com/html5/hotel/hoteldetail/{id}.html`
   PC 版等价：`https://hotels.ctrip.com/hotels/{id}.html`
2. **绝不给**：trip.com 国际站（www/hk/tw/jp 子域）、eztravel.com.tw、wingontravel.com、antianbaoche.com、booking.com 等——国内打不开或英文界面
3. **关键技巧：国际站 trip.com 的酒店详情页 ID 与携程国内站是同一套 ID**。搜到 `trip.com/hotels/beijing-hotel-detail-{ID}/...` 时，直接把 ID 套进 `m.ctrip.com/html5/hotel/hoteldetail/{ID}.html` 即可，无需重新搜
4. 无独立预订页的（如 HIGH旅行民宿）→ 指明 **美团/携程 App 内搜店名**
5. 每个链接**必须验证**再交付（见下），不要只靠搜索摘要里的 URL

## 验证命令（抓 <title> 确认店名）

```bash
for id in 80935572 90215209; do
  title=$(curl -s --max-time 15 -L -A 'Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 Chrome/120 Mobile Safari/537.36' \
    "https://m.ctrip.com/html5/hotel/hoteldetail/${id}.html" \
    | python3 -c "import sys,re,html; t=re.search(r'<title>(.*?)</title>', sys.stdin.read(), re.S); print(html.unescape(t.group(1).strip())[:40] if t else 'NO TITLE')")
  echo "$id -> $title"
done
```

`<title>` 含店名（如 `携程酒店-赛努精品民宿(白河湾店)预订-...`）= 有效且是那家店。title 对不上 = ID 用错，别交付。

## 获取 ID 的方式

- web_search 搜 `"店名" 携程`，结果常直接带 `m.ctrip.com/html5/hotel/hoteldetail/{id}.html`
- 搜到国际站 trip.com 详情页 → 提取 URL 里的 `hotel-detail-{id}` 数字段
- 都找不到 → 给"App 内搜店名"指引，别硬编

## 北京周边民宿推荐要素（用户常用场景）

- 一家三口周末游：**小河/溪水 + 烧烤 + 带院子/亲子间** 是核心诉求
- 资源位：怀柔·白河湾（玩水+烧烤首选）、平谷·金海湖（湖景+烧烤免费）、延庆·百里山水画廊（独院安静）
- 推荐时标注每家关键卖点（亲子间、烧烤是否免费、河边位置），末尾提醒"订前电话确认河边位和烧烤位"——玩水季房源紧，别只信平台房态
- 用户选定清单后可能要求"发到微信"——走一次性 cron + deliver='all'（见 weixin-gateway-troubleshooting）

## 陷阱

1. 搜索摘要里常混入境外站链接（wingontravel/eztravel/hk.trip.com）——先用国内站链接模板重构造，别直接复制
2. `hotels.ctrip.com` PC 版手机也能开，但手机端体验 m.ctrip.com 更好；两个都给也行但优先 m.
3. 民宿类店名多变（如"燚宿·曦然"vs"燚宿曦然"、大小写），验证 title 时允许无空格差异
4. 美团/大众点评上很多民宿没有携程页——直接说"App 搜店名"，不要强行编链接

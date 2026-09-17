---
name: cn-shopping-links
description: "Use when 用户要商品/酒的京东购买链接。给国内可直接打开的链接。"
version: 1.0.0
author: Hermes Agent
license: MIT
tags: [购物, 京东, jd, 商品链接, 推荐, 电商, shopping]
trigger: 用户要求推荐商品后“给京东链接”/“发我链接”/“给出对应链接”，或要求推荐服装、酒、日用品、数码等可购商品
trigger-notes: 只给国内能直接打开的中文链接（商品页 + search.jd.com 搜索兜底）；境外站不给
related_skills: [cn-hotel-booking-links]
---

# 国内商品链接生成（京东为主）

用户要“推荐 + 链接”时，**只给国内能直接打开的中文链接**——境外站（amazon、iherb 等）不给。本 skill 管商品，住宿走 `cn-hotel-booking-links`（同一套“只给国内中文链接”的逻辑）。

## 交付骨架

1. **先给推荐**：按价位/档位分（性价比 / 中端 / 高端），每家说清“为什么选它”+ 关键参数（面料克重、酒精度、容量、年份）
2. **每个推荐配一个京东链接**
3. **末尾给一条搜索兜底**：`https://search.jd.com/Search?keyword=<urlencoded 关键词>&enc=utf-8`
4. 若推荐的是某品牌全系（如安德玛 UA Tech、CHOYA 梅酒），额外给**店铺页**：`https://mall.jd.com/index-<id>.html`

## 链接来源优先级

| 级别 | 形式 | 说明 |
|---|---|---|
| ⭐ 商品页 | `https://item.jd.com/product/<id>.html`、`https://item.m.jd.com/product/<id>.html` | `web_search "<品牌> <型号> 京东 item.jd.com"`；搜索摘要里带 ¥ 价格的可信度高 |
| 店铺页 | `https://mall.jd.com/index-<id>.html` | “某品牌全系”场景最好用 |
| 搜索直达 | `https://search.jd.com/Search?keyword=...&enc=utf-8` | **永远可用，底层兜底**；关键词用中文全名+品类，别用英文 SKU |

聚合页（`jd.com/hprm/...`、`jd.com/jiage/...`、`jd.com/sptopic/...`）能点开但**不是单品页**，可给但不标为“商品页”。

## 陷阱

1. **京东页面不能用 curl 校验**（返回 JS 骨架/反爬）——**不要把“抓不到 title”当成链接无效**；直接给搜索直达兜底，并提示“打不开就京东 App 搜名称”
2. **不要编 SKU ID**：拿不到具体商品 ID 就给搜索直达，别把数字拼一个凑数
3. **搜品类会混入同名商品**（搜“普罗旺斯桃红”混进番茄苗、美甲胶；搜“梅酒”混进品牌周边）——交付前过滤，只留真商品
4. 搜索结果里的**标题带型号/容量**才写进推荐，否则用户搜不准
5. 进口酒/酒类写**参考价**并区分“京东自营”与“第三方店”（同款价差大），标注产地与度数

## 已交付品类参考（可直接复用）

- **速干长袖 T 恤**：迪卡侬 KIPRUN（性价比）、安德玛 UA Tech 1328495/1328496（机能）、龙牙秘纤（通勤）
- **葡萄酒**：蝶之兰天使密语（普罗旺斯桃红）、尚缇 Minuty、云雾之湾长相思（新西兰）、蚝湾 Oyster Bay（平价替代）
- **梅酒/清酒**：CHOYA 俏雅本格梅酒（带梅子 14.5 度）、獭祭 45（推荐）/39/23、白鹤大吟酿（平价）
- 推荐时**给梯度**（同品类里放一个平价替代 + 一个旗舰），用户更容易拍板

## 与酒店 skill 的分工

- 住宿/民宿/酒店 → `cn-hotel-booking-links`
- 商品/酒/服装/日用品 → 本 skill

## 交付后

链接直接写在回复里即可（微信渲染 markdown 可点），无需额外投递；需要成文件/卡片时才走 cron 投递。

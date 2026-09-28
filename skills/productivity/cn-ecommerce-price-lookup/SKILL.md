---
name: cn-ecommerce-price-lookup
description: Use when 用户要查商品价格/京东价/淘宝价/比价表。京东掩码绕过+多源比价。
tags: [京东, 淘宝, 天猫, 比价, 价格, 查价, 电商, jd, taobao, 多少钱, 价格表]
trigger: 用户要求查某个商品在京东/淘宝的价格、做比价表、按价格排序；或需要批量查询商品报价
requires-skills: [douyin-content-extract]
---

# 国内电商比价（京东 + 淘宝）

## 核心事实：京东对未登录访客隐藏价格 🚨

京东商品页给匿名访客的 HTML 里价格是**掩码**的：
```
¥ 4??
登录查看价格
```
搜索摘要里也是掩码（`¥4??`、`¥1??`）。**这是硬拦截，不是抓取姿势问题。**

### 掩码解码（能给出区间）
`¥4??` = 400–499（3 位）／`¥3?` = 30–39（2 位）。数字位数看问号个数，首位数保留。

---

## 三条可用通路

### ✅ 通路 1：京东新版商品页不掩码
形如 `https://item.jd.com/product/<hash>.html`（**不是** `item.jd.com/<sku>.html`）
——这类页面匿名可见价格，且搜索摘要里带完整价。
```bash
# 用精确商品标题去搜，容易命中这类页面
web_search("<完整商品标题> 价格")
# 摘要形如：商品详情 ... ¥ 129.00 北京市 朝阳区
```

### ✅ 通路 2：什么值得买（首选，带店铺名+实付价）
京东价格被掩码，但 **smzdm 的爆料页和百科页带完整京东价**：
```
¥423.3  京东  现售498元，参考爆料购买可优惠74.7元
爆料人: xxx  25-03-18发布
京东此款目前活动售价498元，参与满1元打8.5折，下单1件，实付低至423.3元
购买步骤 1 店铺 京东 悦野户外卖场店 页面价: ¥498
```
- `m.smzdm.com/p/<id>/` = 爆料帖（带**店铺名 + 页面价 + 实付价 + 日期**）
- `wiki.m.smzdm.com/p/<id>/` 或 `wiki.smzdm.com/p/<id>/` = 商品百科，带**价格趋势**（常卖价/历史最低/30天低价/双十一价）
- ⚠️ smzdm 直连被 JS challenge 挡（HTTP 202 + `probe.js`），**只能从搜索引擎摘要读**，别硬抓
- 搜索姿势：`"<完整商品标题> 报价 价格 评测 怎么样"` → 命中 wiki 页概率最高

### ✅ 通路 3：淘宝/天猫（登不登录都便宜，价格明文）
淘宝商品页在搜索引擎摘要里**直接暴露价格**（`￥295`、`￥348.00`）：
```
mobile-phone.taobao.com/detail/<hash>.html   → ￥298 + 颜色分类/长度
pcdetail.taobao.com/<hash>.html              → ￥215 + 市场价/价格区间
mobile-phone.taobao.com/chanpin/<hash>.html  → 品牌聚合页，一次给多个店铺报价
1688: m.1688.com/offer/<id>.html             → 批发价（通常最高，但有参考值）
```
搜索姿势：`"<完整商品标题> 淘宝"` 或 `"<品牌> <型号> 淘宝 价格"`

---

## 死路（别浪费时间）

| 方式 | 结果 |
|---|---|
| `search.jd.com/Search?keyword=` | 302 → `cfe.m.jd.com/privatedomain/risk_handler/`（风控页 2704B） |
| `item.m.jd.com/product/<sku>.html` | HTTP 200 但 title=「京东验证」，价格掩码 |
| `p.3.cn/prices/mgets`（经典价格 API） | ❌ **本机 DNS 被 sinkhole**：`getent hosts p.3.cn` 返回 `172.x/10.x` 内网 IP → 连接超时。走代理 HTTP 000 |
| `api.m.jd.com/client.action` | 403 `cross-origin request from '' is not allowed` / `no access` |
| `item.jd.com/ware/detail.json` | 404 |
| `s.manmanbuy.com`（慢慢买） | 页面能拿到但**价格是 JS 加载**，HTML 里 0 个 `¥` |
| 购物党 gwdang.com | 返回 3227B JS challenge |
| `web_extract()` 抓京东 | Keyless 通道 Gateway timeout |
| 浏览器（browser_exec） | `daemon default didn't come up`（本机内存不足，起不来） |

⚠️ 京东 SEO 聚合页（`www.jd.com/jiage/*.html`、`/hprm/`、`/hotitem/`、`/brand/`）**能直连**（200，500KB+），标题和 SKU 都能拿到，但价格同样是 JS 加载的空壳 `<div class="price p-price" data-skuId="...">`——**只有标题有用**。

---

## 输出规范

1. **必须分通道标注**，不能把区间和实价混在一列：
   - ✅ 京东确定价（商品页直读 / smzdm 爆料）
   - ⚠️ 京东区间（掩码推出）
   - 淘宝/天猫实价
2. **解释为什么有区间**——主动说明京东登录墙，并给用户可操作的解法（自己截图 / 自己登录）
3. **排序时先声明依据**。跨平台取最低可成交价排序最实用；只在京东有价的款不要混进去排
4. 用户明确要「查不到就上淘宝补」——**别在登录墙前停手**，先跨源补齐再汇报
5. 一并给出「京东 vs 淘宝价差最大」的几款（这是用户最关心的行动信息）

## 批量脚本要点
- `web_search` 走 execute_code 批处理，**每批 10-19 次调用**（上限 50），结果落盘 JSON 支持续跑
- 提取价格用双正则：`[¥￥]\s*([0-9]+\.?[0-9]*)` 抓即时价；`实付低至?\s*([0-9.]+)元|到手价\s*([0-9.]+)元|现售\s*([0-9.]+)元` 抓促销实付
- 同一商品有多个 SKU/颜色/长度时，价格不同，必须带上规格

# SeedHub 站点结构详解 —— 内嵌中字影视资源的头号来源

2026-09-27《变形金刚》全系列实战整理。SeedHub 是目前**内嵌中字版本最全**的 BT 索引站，
本 skill 前面的磁力熊 / 悠悠MP4 / 电影天堂 / BTDigg 全部拿不到中字版时，SeedHub 一次解决。

## 基础信息

| 项 | 值 |
|---|---|
| 可用域名 | **`https://www.seedhub.cc`**（直连 200，**无需代理**）|
| 已死域名 | `seedhub.icu`（直连/代理均 HTTP 000，站点已迁）|
| 搜索接口 | **`/s/<urlencode 关键词>`** ← 唯一可用 |
| 失效接口 | `/search?keyword=` / `/searchs` → **403**（Cloudflare）；`/index/search` → 404 |
| 影片页 | `/movies/<id>/` |
| 取磁链 | `/link_start/?seed_id=<id>&movie_title=x`（**必须带 Referer 指影片页**）|

## 🚨 磁链是 base64 编码的

`link_start` 页面里**搜不到 `magnet:` 字符串**。磁链以裸 base64 形式嵌在页面里：

```
bWFnbmV0Oj94dD11cm46YnRpaDo3YTgyNmIwYTk3NzU1M2RiZDkwMWM2NDFhMDk1ZjM5ODU4NDlkMWVk
```

解码 = `magnet:?xt=urn:btih:7a826b0a977553dbd901c641a095f3985849d1ed`

**解析法**：
```python
for b in re.findall(r'\b[A-Za-z0-9+/]{40,200}={0,2}\b', page):
    try:
        dec = base64.b64decode(b + "=" * (-len(b) % 4)).decode('utf-8', 'ignore')
        if dec.startswith('magnet:'): return dec
    except Exception: pass
```

> 页面里还会出现 `thunder-link.js`（迅雷）和 `#qrcode` 等元素，都不是磁链来源；不要被引到迅雷链接上。

## 影片页版本表结构

```html
<li>
  <a target="_blank" title="变形金刚5：最后的骑士[国英多音轨+简繁英特效字幕].Transformers.Thest.Knight.2017.UHD.BluRay-MiniHD[36.86G]"
     href="/link_start/?seed_id=493330&movie_title=变形金刚5：最后的骑士的磁力">变形金刚5：最后的骑士[国英多音轨+简繁英特效字幕].Transf...</a>
     / <code class="size">36.86G</code>
     <code class="seed-feature">蓝光</code><code class="seed-feature">4K</code>
     <span style="float:right;...">2025年</span>
     <span class="create-time" style="display:none;">2025-11-02 23:57</span>
</li>
```

一条正则拿全：
```python
r'title="([^"]{10,400})"[^>]*href="/link_start/\?seed_id=(\d+)[^"]*"[^>]*>.*?</a>\s*/\s*<code class="size">([^<]*)</code>(.*?)</li>'
```

- `title` 属性 = **带中文标注的完整版本名**（`[国英多音轨+简繁英特效字幕]` 这类），筛选靠它，不要靠 `<a>` 的可见文本（被截断成 `…`）
- `<code class="size">` = 体积
- `<code class="seed-feature">` = 特征标签（蓝光/4K/杜比/无损/iNT组…）

## 决定性判据：`seed_id=` vs `redirect_to=pan_id_`

| href 形态 | 含义 |
|---|---|
| `/link_start/?seed_id=NNN&movie_title=…` | **有 BT 种子** → base64 解出磁链 ✅ |
| `/link_start/?redirect_to=pan_id_NNN&movie_title=…` | **只有网盘链接**（夸克/阿里/百度）→ **拿不到磁链** ❌ |

**动手前先数 `seed_id=` 出现的次数**。

实测《变形金刚：起源》(2024)：影片页 `link_start` 出现 96 次，**`seed_id=` 是 0**，全是 `pan_id_`
→ 该片在 SeedHub 只有网盘渠道。（同片在磁力熊只有无中字原声版，SeedHub pan-only，
其他中字版全在阿里/夸克/百度网盘或需登录的 bdshare 论坛 → **BT 无内嵌中字源**，要如实告知用户
并给"网盘 / 无中字版+AI 造字幕内嵌 / 暂缺"三个选项，不要假装找到了。）

## 命中率与压制组

变形金刚系列 **7/8 部**一次拿到 `[国英多音轨+简繁中字]` 的 4K UHD 磁链：

| 片名 | movie_id | 版本数 | 中字版数 |
|---|---|---|---|
| 变形金刚 (2007) | 272 | 79 | 14 |
| 变形金刚2 (2009) | 788 | 62 | 10 |
| 变形金刚3 (2011) | 607 | 56 | 7 |
| 变形金刚4 (2014) | 759 | 98 | 10 |
| 变形金刚5 (2017) | 2710 | 101 | 25 |
| 大黄蜂 (2018) | 115450 | 126 | 33 |
| 超能勇士崛起 (2023) | 110779 | 133 | 35 |
| 变形金刚：起源 (2024) | 117113 | **0（全 pan_id）** | — |

**HDH 系压制组**（SSDSSE / DreamHD / MiniHD / NukeHD / BATWEB）是 4K 中字版主力，
种子文件夹名带「【高清影视之家发布 www.SSDSSE.com】」类前缀 → 离线后移出视频、删广告、删空文件夹（同 jav 流程）。

## 版本挑选：规格优先，体积其次

本 skill 的"用户偏好高清大版本"在 SeedHub 上**不能简单等于"挑体积最大的"**：

- ✅ `[HDR+杜比视界双版本][国英多音轨+简繁英特效字幕].2017.UHD.BluRay.2160p.x265.DV.HDR.TrueHD.Atmos.Repack-SSDSSE[36.87G]`
- ❌ `...IMAX满屏版...UHD.BluRay.Remux...-NukeHD[76.92G]` — 体积最大但属 REMUX 档

实测差点按"最大体积"选中 61.92G 的 REMUX，正确选择是**同规格 25.42G 的 DreamHD 版**。
**规则：先按规格过滤（2160p + 国英多音轨 + 简繁中字 + DV/HDR），再在同规格内挑体积大的。**

## 已解析磁链存档（变形金刚系列，2026-09-27）

```
变形金刚(2007)      35.33G  b4836805a49fc640fbb3b97228dd3dfb1b0e4671
变形金刚2(2009)     35.71G  4c0e7c421808bce06d14f741407914c29973fcf9
变形金刚3(2011)     39.00G  5b718b19d599abcb18ed86dc61b8b0f5f11f2829
变形金刚4(2014)     37.39G  90d6855340db606286c100560e381e83f72cfbd0
变形金刚5(2017)     36.87G  382dfece0fb078e039a0d3f6d53a81638b8bcf89
大黄蜂(2018)        26.77G  ff7db5a9c0b6b220bc9a4ea930eeb6e206a51a47
超能勇士崛起(2023)  25.42G  2cce1940d5da67857196ccefc794f467cf38a255
```

## 配套：同批次的性能与坑

- 7 个磁链同时 `offline_download`（间隔 2s）→ **60 秒全部离线完成**
- `rclone copy` 7 文件并行 + `--buffer-size 32M` → **85-91 MiB/s**，236GB ETA 40 分钟
- rclone **预分配**：`du -sh` 立刻显示满体积、`df` 立刻扣减，别把预分配当"已下完"（判据：`.partial` 归零 + 进程退出）
- 4K HDR 片抽帧 OCR 查字幕**必须先 tonemap**（见 SKILL.md 踩坑记录），否则发灰画面 OCR 识别不到中字

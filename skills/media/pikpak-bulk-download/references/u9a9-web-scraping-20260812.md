# U9A9 网页视频采集调研（2026-08-12 Spike 验证）

用户要建"U9下载"skill：给网页 → 按时间/大小过滤 → 去重 → 离线到 PikPak 指定文件夹。本文件是前置调研结论，**Spike 已验证，无需 crawl4ai**。

## 核心结论

- **不需要 crawl4ai / 浏览器**：u9a9.com 是纯静态 HTML，`curl + 正则` 完整可解析（走代理 us03）
- **列表页已含全部所需数据**：磁链、大小、时间、标题（含清晰度/时长/格式），**无需进入详情页**
- **单页全量、无分页**：搜索 Retsu_dao 返回 53 条（2025-09-11 ~ 2026-08-06），分页导航只有 `<li class="active"><a href="#">1</a></li>`（第 1 页 = 全部）

## 抓取命令

```bash
curl -s --proxy http://127.0.0.1:10808 --max-time 30 \
  -H "User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0" \
  "https://u9a9.com/?type=2&search=Retsu_dao" -o /tmp/u9_page.html
```

## 每行条目结构（<tr class="default">）

```
<a href="/view/2/{btih}" title="【新片速遞】... [1.1G/54:26/MP4]">标题</a>
<a href="//t2-2.6img.pics/2/{btih}.torrent">.torrent 下载</a>
<a href="magnet:?xt=urn:btih:{btih}&tr=...">磁链</a>
<td class="text-center">1.22 GB</td>              ← 大小
<td class="text-center">2026-08-06 05:27:21</td>  ← 发布时间
```

## 解析正则（Python）

```python
rows = re.findall(r'<tr class="default">(.*?)</tr>', html, re.DOTALL)
for row in rows:
    vm = re.search(r'href="(/view/2/[a-f0-9]+)"[^>]*title="([^"]*)"', row)
    btih, title = vm.group(1).rsplit('/',1)[-1], vm.group(2)
    mm = re.search(r'href="(magnet:[^"]+)"', row)          # 磁链
    sm = re.search(r'<td class="text-center">([\d.]+) (GB|MB)</td>', row)  # 大小
    tm = re.search(r'(\d{4}-\d{2}-\d{2}) \d{2}:\d{2}:\d{2}', row)          # 时间
    magnet = mm.group(1).replace('&amp;','&') if mm else ''
```

## 过滤规则（按用户 2026-08-12 指令）

- 时间：`datetime.date.fromisoformat(date) >= cutoff`（如 2025-11-01）
- 大小：`size_gb >= 1.0`
- 去重：⚠️ **待用户确认规则**。实测同标题系列多次出现（如"女演员真实私密生活系列第11集" 3 次、3.24G/3.34G/3.19G），btih 不同但内容可能相同。候选：标题关键词去重只留最大，或按 btih 去重。用户规则未定，先列出清单让用户确认。
- 目标：PikPak `/网络视频/烈@Retsu_dao` 文件夹（需先 path_to_id 或创建）

## 实测结果（Retsu_dao）

- 53 条 → ≥2025-11-01 且 ≥1GB：**43 个 / 86.7GB**
- 过滤掉：8 个（2025-09/10 月）+ 2 个（<1GB）

## 执行注意

- 用户给的网址可能带 `?type=2&search=XXX` 参数，直接原样用
- 离线用 pikpakapi `offline_download(magnet, parent_id=目标文件夹id)`，完成后同样走清广告→移出→改名→删空文件夹流程（与 jav 番号同款）
- 域名可能变动（u9a9.com 类站点），跑前先 curl 验证 200

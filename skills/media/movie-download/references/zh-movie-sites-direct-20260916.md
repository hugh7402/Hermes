# 国内影视站直连实战（2026-09-16 碟中谍8 / 磁力熊 / 悠悠MP4）

## 一句话结论

**国内影视站（磁力熊、悠悠MP4、6V、飘花、电影天堂）一律先直连**（`curl --noproxy '*'`）——走代理常被拦成空响应/骨架页；**BTDigg 这类国外站才需要代理**，且它对代理 IP 频繁返回 0 字节响应，换节点（us06→us05）也无效，别在换节点上反复烧时间。

## 站点探测矩阵（同日同一 UA 实测）

| 站点 | 直连结果 | 磁链可得性 |
|---|---|---|
| 磁力熊 cilixiong.org | HTTP 200 / 19KB | ✅ 站内搜索命中，详情页 `/movie/<id>.html` 含 4 条 magnet |
| 悠悠MP4 uump4.cc | HTTP 200 / 39KB（搜索页 85KB） | ✅✅ 版本最全，帖子页给 `.torrent` 直链 |
| 6V电影 66s6.cc | HTTP 200 / 52KB | 帝国CMS，搜索 `POST /e/search/so.php`（需 Content-Length，缺失报 411） |
| SeedHub seedhub.cc | HTTP 200 / 41KB | 首页无 form，需再探 |
| 飘花 piaohua.com | HTTP 200 / 28KB | 搜索 `/plus/search.php?keyword=&kwtype=0` |
| 电影天堂 dytt8899.com | HTTP 200 / 32KB | GBK 编码，见主 skill |
| BT蚂蚁 btmayi.cc | HTTP 200 / 205KB | ❌ 导航站，`?s=` 只跳转其他搜索引擎 |
| 1lou.me / btbuluo.net / grab4k.cn | HTTP 000 | 直连不通，改用 `web_extract` |
| hdchd.cc / space-empires.com | HTTP 200 但仅 3.5-5.5KB | ❌ 登录壳页，**无 magnet**（DreamHD/REMUX 首发地但拿不到） |
| btdig.com（需代理） | 代理 CONNECT 建隧道成功但**无数据**（len=0） | ⚠️ 换节点无效；限流窗口内用单关键词 + 间隔 13s |

## 磁力熊站内搜索（可直接复制）

```bash
KW="碟中谍8"
timeout 40 curl -sL --noproxy '*' -X POST "https://cilixiong.org/e/search/index.php" \
  -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120" \
  -H "Referer: https://cilixiong.org/" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data-urlencode "classid=1,2" --data-urlencode "show=title" \
  --data-urlencode "tempid=1" --data-urlencode "keyboard=$KW" \
  -o /tmp/cx_s.html -w "HTTP:%{http_code} size:%{size_download}\n"
```

- **UTF-8 提交**（不要把关键词转 GBK，返回 1106B 空页）
- 结果页小（3.5KB）是**正常的**（内联样式少），用“找到 N 条符合搜索条件”判断有无结果
- 结果链接直接用 `re.finditer(r'<a\s[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>')` 抓 `<a>` 内文本，能看到 `/movie/4475.html` 这类详情页
- ⚠️ 磁力熊详情页往往**只有国际版磁链**（YTS / RMTeam），页面底部自带提示“为保证质量优先选择原声版本，下载字幕请前往 Subhd字幕、Zimuku字幕库” → 看到这句就等于“本站无中字版”，直接转悠悠MP4

## 悠悠MP4 → .torrent → 磁链

```bash
KW=$(python3 -c "import urllib.parse;print(urllib.parse.quote('碟中谍8'))")
curl -sL --noproxy '*' -A "$UA" "https://www.uump4.cc/search.htm?keyword=$KW" -o /tmp/u.html
# 解析出 thread-XXXXXX.htm 列表 → 按标题里的字幕/语言/体积标注筛版本
curl -sL --noproxy '*' -A "$UA" "https://www.uump4.cc/thread-424022.htm" | grep -oE 'https?://[^"'\''<>[:space:]]+\.torrent'
curl -sL --noproxy '*' -A "$UA" -e "https://www.uump4.cc/thread-424022.htm" \
  "https://bt.uump4.cc/btdown/2025/08/27/20250827081144t2u12cicnmd.torrent" -o /tmp/t.torrent
python3 scripts/torrent_to_magnet.py /tmp/t.torrent
```

干 torrent 链接用 `-e <帖子URL>` 带 Referer，否则可能拿不到。

## 版本挑选实例：《碟中谍8：最终清算》(2025, 170min)

| 版本 | 磁链 hash 前缀 | 体积 | 说明 |
|---|---|---|---|
| 4K 主选 | `a1f4bdc5…` | 30.18 GB | 2160p iTunes WEB-DL HDR10+ H.265，国英多音轨+简繁英双语特效字幕 |
| 1080p 备选 | `ace3158d…` | 13.48 GB | 1080p H.264，同字幕组合，兼容性最好 |
| 1080p 纯简繁英 | `cc028b1c…` | 12.81 GB | 无国语配音 |

三个都是 DreamHD，**字幕内封在 mkv**（种子内无 .srt/.ass 外挂文件，符合用户内嵌中字规则）。

## PikPak 侧细节

- `path_to_id('/Inbox-JAV')` —— **大小写必须一致**，小写返回空列表 → IndexError
- 磁链 `dn=` 含中文/【】时用 `urllib.parse.quote` 编码；tracker 补 `udp://tracker.openbittorrent.com:80`、`udp://tracker.opentrackr.org:1337/announce` 提高离线成功率
- 离线添加成功后 `offline_list()` 常为空（完成即移除）；**用云端文件夹 `file_list` 累计大小判断进度**

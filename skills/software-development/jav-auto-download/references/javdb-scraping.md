# javdb.com 爬取参考

## 前置条件

- 需要 xray SOCKS5 代理 (127.0.0.1:10808)
- Cookies 管理与年龄验证

## Cookie 管理

```python
def http_get(url, cookie_file='/tmp/jdb_cookies.txt'):
    cmd = ['curl', '-sL', '--socks5', '127.0.0.1:10808',
           '--connect-timeout', '10', '--max-time', '20',
           '-b', cookie_file, '-c', cookie_file,
           '-H', 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36']
    cmd.append(url)
    subprocess.run(cmd, capture_output=True, text=True, timeout=25)
```

**关键点**：
- 必须同时使用 `-b` (读取) 和 `-c` (写入) 以维持会话
- 先访问 `/over18?respond=1` 设置 `over18=1` cookie
- 所有后续请求使用同一 cookie 文件
- **代理不稳定时自动重试**：`http_get()` 内置 3 次重试，如果 stdout < 100 bytes 视为失败并重试

## 搜索影片

```
GET https://javdb.com/search?q={番号}&f=all
```

⚠️ **必须加 `&f=all` 参数！** 不加的话 javdb 默认只返回"热门推荐"卡片，不返回搜索结果。加了 `f=all` 后才显示全部匹配结果。

响应结构：HTML 包含 `<div class="movie-list h cols-4 vcols-8">` 中的卡片
每张卡片 `<a href="/v/{id}" class="box">` 包含：
- `<span class="tag-can-play cnsub">中字可播放</span>` — 封面徽章
- `<div class="video-title"><strong>{番号}</strong> 标题</div>` — 番号+标题
- `<span class="tag is-warning">含中字磁鏈</span>` — 标签

**匹配策略**：在卡片HTML中查找 `<strong>番号</strong>` 匹配。

## 获取磁链

```
GET https://javdb.com/v/{id}
```

磁链在 HTML 中直接可见（非JS加载），格式：
```html
<a href="magnet:?xt=urn:btih:HASH&amp;dn=[javdb.com]NAME.torrent"
   title="右键点击并选择「复制链接地址」">
  <span class="name">DSOD-005-C.torrent</span>
  <br />
  <span class="meta">5.70GB</span>
  <br />
  <div class="tags">
    <span class="tag is-primary is-small is-light">高清</span>
  </div>
</a>
```

**提取规则**：
1. `href="(magnet:[^"]+)"` — 磁链 URL
2. `<span class="name">([^<]+)</span>` — 文件名
3. `<span class="meta">(\d+\.?\d*)\s*(GB|MB)</span>` — 大小

每个磁链在页面中出现两次（一次在按钮区，一次在复制区），通过 `btih:` hash 去重。

### 实测的当前结构：按 `div.item` 切块，体积读 `data-size`（单位 MB）

磁链列表容器是 `<div id="magnets-content" class="magnet-links">`，**每条磁链是一个 `div.item.odd/.even`**，
体积/文件数/日期都在 `data-*` 属性上，比用正则从展示文案里抠可靠得多：

```html
<div id="magnets-content" class="magnet-links">
  …<div class="sda-content">（广告区，别当磁链）…
  <div class="item odd" data-rank="0" data-size="5315" data-files="0" data-date="20260820">
    <div class="magnet-name">
      <a href="magnet:?xt=urn:btih:5cf7ecc9…&amp;dn=[javdb.com]MIDA-709-C.torrent">
        <span class="name">MIDA-709-C.torrent</span>
        <div class="tags">
          <span class="tag is-primary is-small is-light">高清</span>
          <span class="tag is-warning is-small is-light">字幕</span>
        </div>
        <span class="meta">5.19GB</span>
      </a>
    </div>
    <div class="date"><span class="time">2026-08-20</span></div>
    <button class="button is-info is-small copy-to-clipboard"
            data-clipboard-text="magnet:?xt=urn:btih:5cf7ecc9…">複製</button>
  </div>
</div>
```

解析规则（按这个来，别按类名猜）：

1. **切块**：`seg = html[html.find('magnets-content'):]` → `re.split(r'<div class="item (?:odd|even)"', seg)[1:]`
2. **体积**：`data-size` 的**单位是 MB**（5315 = 5.19GB），不要拿它当字节；展示值在 `<span class="meta">` 里
3. **标签**：`<div class="tags">` 内的 `span.tag` 文本（`高清` / `標清` / `字幕`）
4. **文件名 + btih**：`<span class="name">` 与 `data-clipboard-text` / `href` 里的 `btih:`

⚠️ **别按 `magnet-link` 这个类名切**：类名在 `div#magnets-content` 上，不在每条磁链上；
按 `<a class="magnet-link"` 切块会得到 0 条，然后误判成“这个番号没有磁链”。
同理，`<span class="meta">` 里的体积文本**可能被外层结构拆散**，用 `data-size` 兜底。

## 字幕检测

检测以下关键词判断磁链是否含字幕：
- `-C` 后缀（标准中字标记）
- `字幕` / `中字` — 标签文本
- `破解`（无码破解版通常有内嵌中字）
- `SUB` / `-U`（无码破解变体）

## 无码破解版（-UC/-U）处理

`-UC` 后缀表示无码破解+中文字幕，优先级高于纯 `-U`（无码无字幕版）。即使 `-U` 版文件更大（如 23.93GB vs 7.4GB），也优先选 `-UC`。因为用户明确偏好带中文内嵌字幕的版本，且 `-U` 版文件过大下载效率低。

**但注意**：如果用户遇到的是 SNOS/DASS 系列这类标准番号，`-U` 版本画质可能优于标准版。标准版优先，无码版次之。用户偏好以具体磁链名称为准。

## 注意

- javdb 使用 openresty + Cloudflare 反爬，依赖代理稳定性
- `/v/{id}` 页面可能比搜索页面多返回一些内容（如 related videos、actor info）
- 某些旧番号可能磁链已失效（0 个磁链）

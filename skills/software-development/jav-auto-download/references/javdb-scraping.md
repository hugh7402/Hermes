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

**匹配策略**：在卡片 HTML 中查找 `<strong>番号</strong>` 匹配。

⚠️ **番号不在 `<a>` 的 `title` 属性里**。卡片是：

```html
<a href="/v/OXyD4O" class="box" title="BBQ串刺し輪●NTR つばさ舞 パンティと写真付き">
  <div class="video-title"><strong>FNS-267</strong> BBQ串刺し輪●NTR つばさ舞 …</div>
</a>
```

`title` 只有日文片名。按 `title` 匹配会**一个番号都认不出**，然后误判成「javdb 搜不到」。

正确解析（向前配对，不用 `in`）：

```python
def find_vid(code, body):
    import re
    code_nh = code.replace('-', '').upper()
    hits = []
    for m in re.finditer(r'href="(/v/[^"?]+)"', body):
        seg = body[m.start():m.start() + 900]          # 往后看 900 字符
        sm = re.search(r'<strong>([^<]+)</strong>', seg)
        if sm and re.sub(r'[\s_]+', '', sm.group(1)).upper().replace('-', '') == code_nh:
            hits.append((m.group(1), sm.group(1)))
    return hits
```

必须用 `==` 精确相等：搜索页会带出同系列相邻番号（搜 FNS-267 会同时返回 FNS-268 / FNS-276），
用 `in` 会把它们当成目标。

## 详情页必须带 over18 cookie，否则一律 404

**搜索页不需要 cookie，详情页需要。** 不带时 `/v/{id}` 返回约 2.6KB 的 `頁面未找到 (404)`，
很容易误判成「视频 id 错了」或「节点被挡」，实际跟节点、片源都无关。

```bash
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 …"
# 只取一次，jar 跨节点通用
curl -s -c /tmp/jdb_jar.txt -b /tmp/jdb_jar.txt --proxy http://127.0.0.1:10808 \
  -A "$UA" 'https://javdb.com/over18?respond=1'
# jar 里应出现：javdb.com  FALSE  /  FALSE  <exp>  over18  1

# 之后每个请求：-b /tmp/jdb_jar.txt -e https://javdb.com/
```

**不要每换节点重取一遍**——在限流下每多一个请求都是成本（见下节）。

## 详情 URL 拼接：href 已含 `/v/`

```python
detail_url = ('https://javdb.com' + vid) if vid.startswith('/v/') else f'https://javdb.com/v/{vid}'
```

写成 `f'https://javdb.com/v/{vid}'` 而 vid 是 `/v/xAedqO` 时得到的是 `https://javdb.com/v//v/xAedqO` → 404。

## 演员字段：只认 `演員` 和 `/actors/`，不认标题尾巴

详情页的 `<h2 class="title is-4">` 末尾**经常被上传者拼上一个人名**，那不是演员字段。
拿它当演员会得出与用户相反的错误结论（实测：标题尾部写着 A，`演員` 字段其实是用户说的 B）。

两个权威来源：

```python
import re, html as H

def clean(s):
    return H.unescape(re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', s))).strip()

# ① /actors/ 链接：最稳，不受页面文案改版影响
actors = [m.group(2).strip() for m in
          re.finditer(r'href="/actors/([^"]+)"[^>]*>([^<]+)</a>', body)]
# 会混入导航项 censored / uncensored / western，过滤掉
actors = [a for a in actors if a not in ('有碼', '無碼', '歐美')]

# ② 演員 那一段（逗号分隔；逗号后的多个通常是男优）
m = re.search(r'<span class="header">\s*演\s*員[:：]?\s*</span>(.*?)</div>', body, re.S)
if m:
    print('演員:', clean(m.group(1)))
print('actors:', actors)
```

**判读顺序**：先用 ① 的 `/actors/` 列表（第一个即主演），再用 ② 的整段做交叉验证。
逗号后的名字多出来时，**默认它们是男优**，只在用户明确问了才展开。

**与用户给的名字对不上时**，先数该名字在页面出现几次（`body.count(用户给的名字)`）：
0 次基本可判不符；但**不要据此就说用户错**——先去标题/`dn=` 里看是不是上传者拼的别名，
必要时用这个名字反查她的作品列表（`search?q=<名字>`）再下结论。

## 节点轮换与配置生成（javdb 限流下的批量扫描）

### 限流的真实强度

每个机房 IP 只给 **1–3 个请求**，之后 `403` + `0 字节`，**约 20 分钟自动解封**（同 IP 会恢复，所以 403 不是永久封）。

实测数据点：

- 9 个番号用 4 路并发（约 27 个请求）→ 第一个 IP 几秒内废；
- 串行 + 6 秒间隔（18 个请求）→ 仍然在第 3 个番号左右被封；
- **每个番号换一个节点**（每 IP 承 2 个请求）→ 9/9 全部成功。

### 轮换节奏

0. **同一时刻只准有一个进程改 `reality_active.json` / 重启 sing-box。**
   两个脚本（比如「后台跑节点测速轮换」与「我手动切回某个节点」）并发时，后改的配置会被前一个进程随后的
   `stop_sb()/start_sb()` 盖掉，结果是**代理整体不可用、所有站点 `HTTP=000`**——
   现场看起来像「目标站全挂了」「订阅失效了」，实际是自己跟自己抢配置。
   建后台轮换任务前先检查是否已有同类进程；发现 000 先 `ps` 看有没有两个改配置的进程，再怀疑网络。
   **反过来：rclone WebDAV 拉取是直连不走代理的，扫描 javdb（改代理）与拉文件（不碰代理）可以并行。**
1. 每番号固定 2 个请求（1 次搜索 + 1 次详情），中间间隔 7 秒（同一 IP 内不要更密）。
2. 每个番号开始前**换下一个节点**，搜索/详情任一失败就把该番号整体交给下一个节点重试；单番号最多换 5 个节点。
3. 结果随时落盘 JSON（`code / vid / mags / pick{btih,gb,name,why} / target`），失败不用从头重跑。
4. 选版完成后，PikPak 离线阶段**只用 JSON 里的 btih**，不再访问 javdb。

### ⚠️ 不要依赖 `proxy_auto_switch.sh --node` 做地区轮换

它只把 `us01`–`us07` 映射到美国圣何塞，其他地区传不进去；且订阅解析在节点多时会失败
（日志 `解析完成: 1 行` 然后 `所有节点均不可用`），而同一时刻手动拉订阅是 200 / 33KB / 64 个节点。
**自己从订阅 URI 生成 sing-box 配置**，见下面两个坑。

### sing-box 配置生成的两个坑

**① `vless + reality + tcp` 不能有 `transport` 块。**
写 `{'type': 'vless', …, 'transport': {'type': 'tcp'}}` 会让 sing-box 直接 `FATAL` 退出：
`decode config: outbounds[0].transport: unknown transport type: tcp`。
正确做法：`type == 'tcp'` 时**整个 transport 字段省略**，只有 ws / grpc / http 才写。
症状辨识：节点“启动即退出 rc=1”，看上去像节点失效，实际是配置非法。

**② hysteria2 的端口可能是端口跳跃格式。** URI 里写 `…:35000/?…` 或 `20000-30000`，
直接 `int(port)` 会抛 `ValueError: invalid literal for int() with base 10: '35000/'`：

```python
raw_port = (port or '443').split('/')[0].strip()      # 去掉尾随 /
ports = None
if '-' in raw_port:                                    # 端口跳跃范围
    a, _, b = raw_port.partition('-')
    ports = [f'{a}:{b}']
    raw_port = a
ob = {…, 'server_port': int(raw_port)}
if ports:
    ob['server_ports'] = ports                         # sing-box 字段名是 server_ports
```

hysteria2 的 `tls.insecure` 直接设 `True`：订阅里这类节点的 SNI/证书常是自签，不放开会握手失败
（`remote error: tls: handshake failure`）。

### 节点优先级（javdb 场景）

1. **排除日本**——javdb 按国家封锁，返回版权限制页（约 1.4KB）。
2. **hysteria2 节点优先**——vless 的圣何塞/新加坡节点被反复使用后普遍处于 403，
   hy2 是未被消耗的独立 IP 池，一次性可以顶完 9 个番号。
3. 其次美国洛杉矶 / AWS新加坡，最后才是圣何塞与新加坡 vless。

把验证通过的配置存成 `reality_good.json`，下次会话直接复用，省一次探测请求。

## 注意

- javdb 使用 openresty + Cloudflare 反爬，依赖代理稳定性
- **三种失败要分清**：`403`/0 字节 = IP 限流（换节点或等 20 分钟）；`522`/16 字节 = 节点路由问题（换节点）；
  页面 40–50KB 但番号零匹配 = **解析器写错了，不是封禁**
- `/v/{id}` 页面可能比搜索页面多返回一些内容（如 related videos、actor info）
- 某些旧番号可能磁链已失效（0 个磁链）

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
2. **体积**：`data-size` 的**单位是 MB**（5315 = 5.19GB，10766 = 10.51GB），不要拿它当字节、也不要除 1024²；展示值在 `<span class="meta">` 里可作交叉校验
3. **标签**：`<div class="tags">` 内的 `span.tag` 文本（`高清` / `標清` / `字幕`）
4. **文件名 + btih**：`<span class="name">` 与 `data-clipboard-text` / `href` 里的 `btih:`

⚠️ **`data-*` 属性的 0 值是「缺失」不是「真值」，取到 0 必须回退到正文**：

`data-files="0"` 很常见，而同一行的展示文案写着 `3個文件`；`data-size` 偶尔也缺。
判据写 `if ds and int(ds[-1]) > 0` / `if df and int(df[-1]) > 0`，两个都为 0 时才回退到
`(\d+\.?\d*)\s*GB` 与 `(\d+)\s*個文件`。**按属性值直接采用会把 10GB 的片子当成 10MB，然后被 <2GB 门槛误杀。**

```python
ds = re.findall(r'data-size="(\d+)"', head)
df = re.findall(r'data-files="(\d+)"', head)
gb   = round(int(ds[-1]) / 1024, 2) if ds and int(ds[-1]) > 0 else 0.0
files = int(df[-1])                 if df and int(df[-1]) > 0 else 0
if not gb:    gb    = float(m.group(1)) if (m := re.search(r'(\d+\.?\d*)\s*GB',  seg)) else 0.0
if not files: files = int(m.group(1))   if (m := re.search(r'(\d+)\s*個文件',   seg)) else 0
```

（`head` 取 `body[max(0, m.start()-900):m.start()]`——`data-*` 在 `<a>` **之前**；`seg` 取 `<a>` 之后 1200 字符拿展示文案。）

⚠️ **btih 长度必须是 40 位**。`re.search(r'btih:([0-9a-fA-F]{32,40})', url)` 是安全的抓法（不写死 40，
否则遇到截断条目会**整条被正则丢掉**，表现为「这个番号磁链数为 0」而实际页面上有一条）；
但**抓到长度不为 40 的那条不能用**——它是 javdb 存储的残缺链接，PikPak 永远下不来，详见 SKILL.md「死种/无种磁链处理」。

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
- 详情页面积极大（含 related 卡片），**只按 `href="(/v/[^\"?]+)"` 抓链接再向前配 `<strong>`**，
  不要对整页做 `番号 in body` 判断——搜索页/详情页都会带出相邻番号的卡片。

# subtitlecat.com 字幕搜索参考

## 搜索

```
GET https://www.subtitlecat.com/index.php?search={番号}
```

不需要 Cookie 或代理（可选 socks5），搜索结果每行是一个字幕包。
⚠️ **搜索结果页的链接是相对路径**（无前导 `/`）：

```html
<a href="subs/1460/HMN-850.html">HMN-850 (translated from Japanese)</a>
<!-- 不是 /subs/1460/HMN-850.html，而是 subs/1460/HMN-850.html -->
```

代码中必须同时匹配两种格式：

```python
items = re.findall(r'<a[^>]*href="(/subs/\d+/[^"]+)"[^>]*>([^<]+)</a>', html)
if not items:
    items = re.findall(r'<a[^>]*href="(subs/\d+/[^"]+)"[^>]*>([^<]+)</a>', html)
```

拿到链接后**统一补前导斜杠**：

```python
if not link.startswith('/'):
    link = '/' + link
```

**筛选规则**：
1. 仅保留番号匹配的结果（`code.upper() in name.upper()`）
2. 按 `downloads` 降序排列
3. 选下载量最高的

## 获取各语言字幕

### 方式一：从详情页直接获取翻译版下载链接（推荐）

subtitlecat 详情页的 HTML 中直接包含了所有可用翻译版本的 .srt 下载链接，不需要通过翻译表单提交。这些链接是**静态可下载的**：

```html
<a href="/subs/1518/489155.com@CAWD-992.ja.whisperjav-zh-CN.srt">Chinese (Simplified) Download</a>
<a href="/subs/1518/489155.com@CAWD-992.ja.whisperjav-zh-TW.srt">Chinese (Traditional) Download</a>
<a href="/subs/1518/489155.com@CAWD-992.ja.whisperjav-en.srt">English Download</a>
```

**工作原理**：subtitlecat 服务器在用户请求翻译时生成并存储翻译后的 SRT 文件。这些文件永久存在于 `/subs/{folder_id}/` 目录下，命名规则为 `{原文件名}-{语言代码}.srt`。

**获取流程**：

```python
# 1. 从搜索结果进入详情页
# 2. 在详情页 HTML 中搜索所有 .srt 下载链接
links = re.findall(r'href\s*=\s*"(/subs/\d+/[^"]*\.srt)"', html)
# 3. 按语言优先级选择：
#    - 文件名含 zh-CN → 简体中文
#    - 文件名含 zh-TW → 繁体中文
#    - 文件名含 -en. → 英语
# 4. 直接下载
curl -sL 'https://www.subtitlecat.com/subs/1518/489155.com@CAWD-992.ja.whisperjav-zh-CN.srt'
```

### 方式二：通过 translate_from_server_folder 获取翻译（备用）

```
GET https://www.subtitlecat.com/subs/{id}/{name}.html
```

⚠️ **SRT 下载链接的 `href` 属性两侧可能有空格**：

```html
<a onclick="log_download(14609295); show_voting('zh-CN');"
   href = "/subs/1460/HMN-850-zh-CN.srt"    <!-- 注意 href 后有空格 -->
   >Chinese (Simplified) Download</a>
```

正则必须用 `href\s*=\s*"..."`（允许等号两侧空白）：

```python
for m in re.finditer(r'href\s*=\s*"(/subs/\d+/[^"]*\.srt)"', html):
    ...
```

**语言识别**（按优先级）：
1. 文件名含 `zh-CN` → 简体中文
2. 文件名含 `zh-TW` / `zh-Hant` → 繁体中文
3. 文件名含 `-zh.` → 视为简体中文
4. 页面上下文含 "Chinese (Simplified)" → 简体中文
5. 页面上下文含 "Chinese (Traditional)" → 繁体中文
6. 文件名含 `eng-zh-CN` → 英文原版翻译的简体中文（来自另一用户的英文字幕二次翻译，质量通常优于直接自动翻译版）

## 多搜索结果页面（重要）

同一番号可能对应**多个 subtitlecat 页面**。例如 WANZ-320：
- `subs/120/WANZ-320.html` — 原始自动翻译版，包含多种语言但可能中文质量较低
- `subs/245/WANZ-320%20eng.html` — 英文用户上传的英文原版页，由此派生 `eng-zh-CN`/`eng-zh-TW` 等多语言翻译

当第一个搜索结果页找不到理想的中文版时，检查搜索结果的第二页（`...eng.html`）：
- `eng-zh-CN` 是对白更完整的英文→中文翻译版
- `eng-zh-TW` 是英文→繁体中文版

## 下载字幕

```bash
# 先确保目标目录存在
mkdir -p /opt/data/PikPak/Inbox-JAV

# 下载 SRT
curl -sL -o /path/to/output.srt --socks5 127.0.0.1:10808 \
  --connect-timeout 10 --max-time 20 \
  "https://www.subtitlecat.com/subs/1460/HMN-850-zh-CN.srt"
```

⚠️ **必须先 `os.makedirs(dst_dir, exist_ok=True)` 再写入，否则 curl 输出到不存在的目录会静默失败。**

## 字幕文件命名

字幕文件名改为与视频文件一致（仅后缀改为 `.srt`）：
- 视频：`HMN-850.mp4` → 字幕：`HMN-850.mp4.srt`
- 磁链：`DSOD-005-C.torrent` → 去掉 `.torrent` → `DSOD-005-C.srt`

## 已知问题

- subtitlecat 搜索结果可能不包含最新番号
- 部分字幕包包含多语言但文件名无明确语言标记，需要检查页面上下文
- subtitlecat 可能有 Cloudflare 防护，代理不稳定时可能返回空页面
- 字幕包可能是多语言合集（`...uc` = unspecified collection?），中文只是其中之一
- SRT 文件下载直接通过静态链接，无需 referer 或 cookie

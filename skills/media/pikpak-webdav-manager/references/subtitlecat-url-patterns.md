# Subtitlecat URL Patterns & Workflow

## 搜索网址结构

```
https://www.subtitlecat.com/index.php?search={番号}
```

搜索结果页面中提取字幕详情页链接：

```
href="subs/{数字}/{名称}.html"
```

## 详情页 → 翻译版本下载

在详情页中，直接翻译好的 SRT 文件可通过以下模式找到：

```
href="/subs/{数字}/{名称}-zh-CN.srt"   # 中文简体
href="/subs/{数字}/{名称}-zh-TW.srt"   # 中文繁体
```

对应投票按钮也在同一行附近：
```
href="javascript:vote('zh-CN',{vote_id},+1)"
```

## 直接下载示例（一行命令）

```bash
# 番号搜索 → 直接下载中文简体
curl -sL 'https://www.subtitlecat.com/index.php?search=RBD-664' \
  -H 'User-Agent: Mozilla/5.0' \
  | grep -oP 'href="subs/\d+/[^"]+\.html"' \
  | head -1 \
  | sed 's/href="//;s/"//'

# 已知具体页面 → 提取 zh-CN 直链
curl -sL 'https://www.subtitlecat.com/subs/1496/IPZZ-835.html' \
  -H 'User-Agent: Mozilla/5.0' \
  | grep -oP 'href="(/subs/\d+/[^"]+-zh-CN\.srt)"' \
  | head -1 \
  | sed 's/href="//;s/"//'

# 下载中文简体字幕
curl -sL 'https://www.subtitlecat.com/subs/214/rbd-664-zh-CN.srt' \
  -H 'User-Agent: Mozilla/5.0' -o /tmp/sub.srt
```

## 文件命名规则

| 模式 | 示例 | 说明 |
|:----|:----|:------|
| `{name}-orig.srt` | `CAWD-992-FHD-orig.srt` | 原始上传文件 |
| `{name}-ja.srt` | `CAWD-992.whisperjav-ja.srt` | 日文 WhisperJAV 转录 |
| `{name}-zh-CN.srt` | `CAWD-992.whisperjav-zh-CN.srt` | 中文简体翻译 |
| `{name}-zh-TW.srt` | `CAWD-992.whisperjav-zh-TW.srt` | 中文繁体翻译 |
| `{name}-en.srt` | `CAWD-992.whisperjav-en.srt` | 英文翻译 |

## 质量推荐

1. **WhisperJAV 日→中翻译（~38KB）** — 质量最高，完整对话翻译
2. 其他中文翻译（7~32KB）— 视上传者质量而定
3. 原始日文 → 自行用 LLM 翻译

## 注意

- subtitlecat.com 不需要代理，直连即可
- 原始文件可能含广告植入（如 "shtfab" 水印），优先选翻译版本
- 有些原始 .srt 文件是 GBK 编码而非 UTF-8，用 `iconv -f GBK -t UTF-8` 转码
- 同一个番号可能有多个字幕条目（来自不同上传者），一个损坏就试另一个

## 编码损坏排查

部分 subtitlecat 字幕文件会出现严重编码损坏（UTF-8 替换字符 U+FFFD 嵌入文件）。
特征：
- 显示为 `锟斤拷` 或 `�` 乱码
- 文件包含 `\xef\xbf\xbd`（U+FFFD 的 UTF-8 编码）与有效中文混合

**排查步骤**：
1. 先试另一个条目（同一个番号可能有多个上传者）
2. 试查看原始版本（`-orig.srt` 或 `-ja.srt`）是否干净
3. 所有版本都坏的话，选字幕行数最多的版本保存——大部分行仍可辨识
4. 完成版字幕可后续用 LLM 从英/日原文重新翻译

## 通用排查流程

当 subtitlecat 搜索返回多条目时：

1. 先看条目名称是否包含 `whisperjav`（优先选，质量最好）
2. 其次看下载数（`downloads` 列），选最高的
3. 打开详情页找中文翻译（`zh-CN.srt` / `zh-TW.srt`）
4. 下载后检查前几行确认编码正确
5. 编码损坏则换另一个条目重试

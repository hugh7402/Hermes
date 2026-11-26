---
name: deepseek-web-search
description: Use when 需要联网搜索或抓取网页正文。DeepSeek Search/Fetch 接口。
version: 1.0.0
author: hermes
tags: [web, search, fetch, deepseek, 联网, 搜索, 抓取, 网页]
trigger: 联网搜索|网页搜索|搜索一下|查一下|抓取网页|fetch 网页|web search
requires-skills: []
metadata:
  hermes:
    tags: [web, search, deepseek]
    related_skills: []
---

# DeepSeek 网页搜索与抓取

## When to Use

- 需要查实时信息（价格、新闻、产品规格、政策原文）
- 需要把某个网页正文抓成 Markdown 再分析
- 内置 `web_search` 只给 snippet、不够用，需要**正文摘要**时

## 与内置 web_search 的区别

内置搜索只返回标题 + snippet（100~200 字符）。DeepSeek 的 Search 额外返回
`summary`（600~800 字符，已经提取过要点）与 `authority`（权威性 0~4）、
`rerank_score`（0~3，≥1.5 算优质）。**写材料要引证时优先用它**：
拿 `summary` 就能直接判断这一条值不值得点进去，省一轮 fetch。

## 两种用法，先选对

| 方式 | 谁调接口 | 计费 | 适合 |
|---|---|---|---|
| **联网工具**（服务端）<br>`ds_agent_web.py` | 模型自己决定搜不搜 | **搜索/抓取不计费**，只算 token | 对话式提问、“帮我查一下”、“总结这个链接” |
| **Search / Fetch 接口**<br>`ds_web.py` | 我们自己调 | 5 元/千次成功请求 | 需要拿原始结果自己筛、批量检索、做 RAG |

**默认用联网工具**，它免费且带引用。需要精确控制 query 语法或多轮批量检索时，才用 ds_web.py。

### 联网工具（ds_agent_web.py）

```bash
python3 ds_agent_web.py "小米笔记本涨价了吗"           # 联网搜索（快）
python3 ds_agent_web.py "交叉核对这个说法" --think      # 深度思考搜索（多步检索）
python3 ds_agent_web.py "总结这页 https://x.com/p" --read-only   # 只读链接不搜
```

```python
from ds_agent_web import ask
r = ask('小米笔记本涨价了吗', think=True)
print(r['answer'])
for c in r['citations']:
    print(c['title'], c['url'])
```

关键规格：
- 模型必须是 **`deepseek-flash`**（官方文档明确要求）
- 工具名 `deepseek_web_search` / `deepseek_read_url`，声明在 `tools` 里
- `thinking: {"type": "enabled"}` = 深度思考搜索；不传 = 普通搜索
- **`tool_choice` 不能指定这两个工具**（实测返回 400）；`tool_choice: none` 会连阅读链接一起关
- 引用在 Chat Completions 的 `message.annotations[].url_citation`
- 实测耗时：普通搜索 5-9 秒，深度思考 6-9 秒，输入约 11k token（搜索结果占大头）

### 图片搜索（免费，容易漏掉）

**不需要额外工具**。用户消息带图片时，`deepseek_web_search` 会自己按图搜：
- `kind` 为 `image_search`，深度思考中是 `deep_image_search`
- `queries` 是空数组（没有查询词，直接以图搜图）
- 每条结果多一个 `image_url` 字段（原站图片地址，**仅供展示，不保证能访问**）
- 同样**不计费**

用户发商品图、截图、景点照问“这是什么东西/哪里/多少钱”时，直接带图提问就够。

**🚨 图片要传 data URL（base64），不要传外部链接。**
实测传 `https://upload.wikimedia.org/...` 直接报
`Failed to download image from ...`——下载发生在**服务端**，外部图床不一定能访问
（本机连 wikimedia 直连 000、代理 400，两边都不通）。
用户发来的图本来就落在本地，直接 base64 编进去最可靠：

```python
import base64, pathlib, mimetypes
def data_url(path):
    p = pathlib.Path(path)
    mime = mimetypes.guess_type(p.name)[0] or 'image/png'
    return f'data:{mime};base64,' + base64.b64encode(p.read_bytes()).decode()

from ds_agent_web import ask
r = ask('这张图是什么产品？大概多少钱', image=data_url('/path/to/img.jpg'))
```

### 多轮对话的坑

- 历史必须**原样回传**上一轮的 assistant 消息，**保留 `kind` 和 `signature` 字段**，丢了就断链
- **搜索结果、打开的网页、上轮思考都不会进入后续上下文**，只留回答正文
- 只有「阅读链接」抓到的网页能靠 `signature` 还原并拼回该轮用户消息末尾——所以要追问网页细节，得保住 signature
- 带联网工具块的历史，可以发给没声明工具的请求

### 不能续写

用过 `deepseek_web_search` 或 `deepseek_read_url` 的回复**不能续写，返回 400**。
想接着写只能重发上一次请求（不能靠 `prefix: true`）。

### 流式输出注意

- `message_start` 里的 `usage` **只包含第一步推理**，最终用量看 `message_delta`
- 开启思考时 `message_start` 后立刻开一个 `thinking` 块，模型先去搜索时这个块可能为空
- 无新内容时会发 `: keep-alive` 注释

### 用量字段

`usage.server_tool_use` 里有 `web_search_requests`、`web_fetch_requests`、
`tool_search`、`tool_fetch`、`tool_image_search`——可以拿来核算到底搜了几次。
**这些全不计费**，只有模型 Token 计费。

---

## Search / Fetch 接口（ds_web.py）

- Key：与 DeepSeek 模型 API 同一个，在 `/opt/data/.env` 的 `DEEPSEEK_API_KEY`
- 计费：**按成功请求次数**，Search 与 Fetch 各 5 元 / 千次
- 失败、无结果、超时**不计费**——所以 `count` 调大不涨价（1~50 条同价）
- `need_content=true` 也不涨价，需要正文时尽管开

## 用法

已封装：`/opt/data/.tmp_tests/ds_web.py`

```bash
# 搜索（默认返回 summary）
python3 ds_web.py search "查询词" 5

# 搜索并带回网页正文
python3 ds_web.py search "查询词" 5 --content

# 抓单个网页成 Markdown
python3 ds_web.py fetch "https://example.com/article"
```

```python
from ds_web import search, fetch

for r in search('Redmi Book 14 2026 内存规格 site:mi.com', count=5):
    print(r['rerank_score'], r['authority'], r['title'], r['url'])
    print(r['summary'][:300])

page = fetch('https://www.mi.com/prod/redmi-book-14-2026')
print(page['title'], len(page['content']))
```

## 搜索语法（原样传给搜索服务，可组合）

| 操作符 | 示例 | 说明 |
|---|---|---|
| `site:` | `DeepSeek site:github.com` | 限定站点，多个用空格 + `OR` |
| `-site:` | `-site:example.com` | 排除站点 |
| `-` / `-"..."` | `-广告` / `-"release notes"` | 排除关键词 / 短语 |
| `"..."` | `"精确短语"` | 精确匹配 |
| `lang:` | `lang:zh,en` | 限定语言 |
| `after:` `before:` | `after:2025-01-01` | 限定日期 |

**查官方规格、买电子产品、核实政策原文时，一定加 `site:<官方域名>`**——
实测不加会混进大量二手转载站和不同地区站点（查中国小米笔记本会返回印度站的 FAQ）。

## 限速与错误处理

- Search 100 QPS、Fetch 25 QPS（账号级），Fetch 另对同一域名单独限速
- 408 / 429 / 5xx：等一会儿重试（`ds_web.py` 已内置指数退避 3 次）
- 402：余额不足，重试无意义
- 其它 4xx：改请求前别重试
- 404（Fetch）：目标页不可用、被站点策略拦、不是可提取的正文

## 踩过的坑

- **Fetch 的 `title` 可能为空**，别拿它判断成败，看 `content` 长度
- **`site:` 必须带完整域名**，写 `site:mi.com` 有效，写 `site:小米官网` 无效
- Search 返回的 `content` 在 `need_content=false` 时**恒为空字符串**，不是没抓到
- 结果是按国家/地区倾向排序的，同一 query 换 `localization`（IP 地址）会变

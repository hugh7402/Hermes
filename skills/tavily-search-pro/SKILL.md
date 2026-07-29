---
name: tavily-search-pro
slug: tavily-search-pro
description: >
  Tavily AI search platform with 5 modes: Search (web/news/finance), Extract (URL content),
  Crawl (website crawling), Map (sitemap discovery), and Research (deep research with citations).
  Use for: web search with LLM answers, content extraction, site crawling, deep research.
version: 1.0.0
author: Leo 🦁 + Hermes adaptation
tags: [search, tavily, web, news, finance, extract, crawl, research, api]
---

# Tavily Search 🔎

AI-powered web search platform with 5 modes: Search, Extract, Crawl, Map, and Research.

## Requirements

- `TAVILY_API_KEY` environment variable in `.env` (已配置)
- `tavily-python` pip package (已安装)

## Usage

通过 Hermes 终端调用：

### search — 网页搜索

```bash
python3 <skill_dir>/scripts/tavily_search.py search "query" [options]
```

### news — 新闻搜索

```bash
python3 <skill_dir>/scripts/tavily_search.py news "query" [options]
```

### finance — 财经搜索

```bash
python3 <skill_dir>/scripts/tavily_search.py finance "query" [options]
```

### extract — URL 内容提取

```bash
python3 <skill_dir>/scripts/tavily_search.py extract "https://example.com" [options]
```

### crawl — 爬取网站

```bash
python3 <skill_dir>/scripts/tavily_search.py crawl "https://docs.example.com" [options]
```

### map — 站点地图发现

```bash
python3 <skill_dir>/scripts/tavily_search.py map "https://example.com" [options]
```

### research — 深度研究（异步轮询）

```bash
python3 <skill_dir>/scripts/tavily_search.py research "research question" [options]
```

Research 是异步作业，提交后自动轮询直到完成（默认 180s 超时）。

**参数：**
- `--model mini|pro|auto` — 模型（默认 auto，推荐 mini 更快）
- `--timeout N` — 最大等待秒数（默认 180）

**示例：**
```bash
# 快速研究（约30-60s）
python3 scripts/tavily_search.py research "AI agent frameworks" --model mini

# 深度研究（约2-3min）
python3 scripts/tavily_search.py research "Impact of AI on healthcare" --model pro

# 设置更长超时
python3 scripts/tavily_search.py research "quantum computing" --model auto --timeout 300
```

## 常用选项

| 选项 | 说明 | 默认 |
|------|------|------|
| `--depth basic\|advanced` | 搜索/提取深度 | basic |
| `--time day\|week\|month\|year` | 时间范围 | 不限 |
| `-n NUM` | 结果数量 (0-20) | 5 |
| `--answer` | 包含 LLM 合成答案 | off |
| `--json` | JSON 输出 | off |
| `--format markdown\|text` | 输出格式 (extract/crawl) | markdown |
| `--model mini\|pro\|auto` | 研究模型 (research) | auto |
| `--limit N` | 最大页面数 (crawl/map) | 10/50 |

## 示例

```bash
# 搜索带答案
python3 <skill_dir>/scripts/tavily_search.py search "latest AI news" --answer

# 深度研究
python3 <skill_dir>/scripts/tavily_search.py research "Impact of AI on healthcare in 2026"

# 提取 URL 内容
python3 <skill_dir>/scripts/tavily_search.py extract "https://example.com/article"

# 新闻搜索
python3 <skill_dir>/scripts/tavily_search.py news "AI regulation" --time week
```

## Error Handling

- **Missing API key:** Clear error message with setup instructions.
- **401 Unauthorized:** Invalid API key.
- **429 Rate Limit:** Rate limit exceeded, try again later.
- **Network errors:** Descriptive error with cause.
- **Timeout:** 30-second timeout on synchronous HTTP requests (search/extract/crawl/map).
- **Research 异步轮询**: Research API 是异步的，详见 `references/research-polling.md`。
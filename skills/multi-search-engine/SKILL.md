---
name: multi-search-engine
description: >
  Multi search engine integration with 16 engines (7 CN + 9 Global).
  Supports advanced search operators, time filters, site search, privacy engines,
  and WolframAlpha knowledge queries. No API keys required.
version: 2.1.3
author: gpyangyoujun + Hermes adaptation
tags: [search, multi-engine, backup, web, no-api-key]
---

# Multi Search Engine

整合 16 个搜索引擎，无需任何 API Key。作为 Tavily 的零成本备用搜索。

## 工作机制

当 Tavily 不可用时，自动使用 web_fetch 直搜以下引擎：

**中文查询 → 国内引擎（7个）：**
百度、必应 CN、必应国际、360、搜狗、微信、神马

**英文查询 → 国际引擎（9个）：**
Google、Google HK、DuckDuckGo、Yahoo、Startpage、Brave、Ecosia、Qwant、WolframAlpha

## 使用场景

- Tavily API 不可用或超时时的降级方案
- 需要国内搜索引擎结果（百度/360/搜狗等）
- 零额外成本的简单搜索

## 参考文件

详见 `references/` 目录：
- `advanced-search.md` — 高级搜索语法
- `international-search.md` — 国际搜索引擎详情
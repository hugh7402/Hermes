# 豆包搜索（火山引擎联网搜索 API）— 接入细节

2026-07-28 上线，火山引擎将豆包 App 背后的搜索能力拆出，面向企业和开发者。**个人用户每月 500 次免费搜索额度**，超出按量付费或订阅月卡。API Key 从「联网搜索控制台」创建（console.volcengine.com → 豆包搜索/联网搜索），**与方舟模型 API Key 不通用**。

官方文档：https://www.volcengine.com/docs/85508/1650263
官方 skill 源码（含完整客户端）：`bytedance/agentkit-samples` → `skills/byted-web-search/`

## 鉴权方式（两种）

1. **API Key（推荐，个人用户）**：POST 到内部端点，`Authorization: Bearer <key>`
2. **AK/SK（企业）**：HMAC-SHA256 签名，走 `mercury.volcengineapi.com?Action=WebSearch&Version=2025-01-01`（SERVICE=volc_torchlight_api, REGION=cn-beijing）

## API Key 请求

```
POST https://open.feedcoopapi.com/search_api/web_search
Content-Type: application/json
X-Traffic-Tag: skill_web_search_common
Authorization: Bearer <API_KEY>
```

Body：
```json
{
  "Query": "搜索词",
  "SearchType": "web",          // web | image
  "Count": 10,                   // 1..10
  "NeedSummary": true,           // web 类型返回千字正文摘要
  "TimeRange": "OneWeek",        // 可选: OneDay/OneWeek/OneMonth/OneYear 或 YYYY-MM-DD..YYYY-MM-DD
  "Filter": {"AuthInfoLevel": 3},// 可选，权威分级过滤
  "QueryControl": {"QueryRewrite": true}  // 可选，宽搜语义改写
}
```

## 响应结构

```json
{
  "ResponseMetadata": {"RequestId": "..."},
  "Result": {
    "ResultCount": 3,
    "TimeCost": 123,
    "WebResults": [
      {
        "Id": "...", "SortId": 1,
        "Title": "...", "Url": "...",
        "SiteName": "新浪财经",
        "Snippet": "短摘要",
        "Summary": "千字级正文摘要（Agent 可直接引用）",
        "Content": "完整正文",
        "PublishTime": "2026-08-18T06:28:00+08:00",
        "AuthInfoDes": "一般权威", "AuthInfoLevel": 3,
        "RankScore": 0.987,
        "LogoUrl": "..."
      }
    ]
  }
}
```

特点：每条结果自带权威分级（AuthInfoLevel）、发布时间（精确到秒）、千字级正文摘要（Summary）——Agent 拿到就能判断可信度/时效性并直接引用，无需二次抓取。

## 错误码（在 ResponseMetadata.Error 里，HTTP 仍可能 200）

| 码 | 含义 |
|----|------|
| 10400 | 参数错误（Query/Count/TimeRange 格式） |
| 10402 | 搜索类型非法（仅 web/image） |
| 10403 | 账号或权限异常（Key 非联网搜索控制台签发） |
| 10406 | **免费额度已耗尽**（500 次/月用完了）→ 提示用户切回其他后端 |
| 10407 | 无可用免费策略 |
| 10500 | 服务内部错误，稍后重试 |
| 700429 | 免费链路触发限流，降频重试 |
| 100013 | 子账号未授权 TorchlightApiFullAccess |

## 已配置实例（2026-08）

- 插件：`/opt/data/plugins/web/doubao/`（Hermes 用户插件）
- Key：`/opt/data/.env` → `WEB_SEARCH_API_KEY`
- 配置：`web.search_backend: doubao`，`plugins.enabled` 含 `web/doubao`
- extract 不受影响（自动 fallback 到 TAVILY_API_KEY）
- 免费额度耗尽后切换：`hermes config set web.search_backend tavily`

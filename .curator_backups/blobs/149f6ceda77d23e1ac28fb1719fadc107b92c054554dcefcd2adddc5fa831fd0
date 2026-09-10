---
name: hermes-provider-management
description: "Manage Hermes agent providers — list, switch, add custom API backends (百炼, 硅基流动, etc.), and troubleshoot provider-level issues."
version: 1.0.0
author: Emma + Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [hermes, provider, configuration, model-selection, bailian, siliconflow]
    related_skills: [hermes-agent]
---

# Hermes Provider Management

## Overview

Hermes uses a layered provider system:
1. **Built-in providers** — `deepseek`, `alibaba`, `zai`, `openrouter`, `anthropic`, etc. Defined in `hermes_cli/models.py` via `CANONICAL_PROVIDERS`.
2. **Plugin providers** — `plugins/model-providers/<name>/` can extend the list at startup.
3. **`custom` provider** — designed for Ollama/local endpoints, NOT general OpenAI-compatible APIs.

Each provider profile declares: `base_url`, `env_vars` (which `.env` key to read for API key), model whitelist (in `hermes_cli/models.py`), and aliases.

## 主/备模型链（fallback_providers）

config.yaml 支持顶层 `fallback_providers` 列表：主模型故障时自动降级到备用 provider+model。用户说"主用 X、备用 Y"时**先看是否已由 fallback_providers 满足**——不是非改 `model.default` 不可。api_key 支持 `${ENV_VAR}` 引用 .env。

```yaml
model:
  default: deepseek-v4-flash
  provider: deepseek
  base_url: ''
fallback_providers:
  - provider: siliconflow
    model: deepseek-ai/DeepSeek-V4-Flash
    base_url: https://api.siliconflow.cn/v1
    api_key: ${SILICONFLOW_API_KEY}
```

典型组合（2026-09 实测）：主=DeepSeek 官方 `deepseek-v4-flash`，备=硅基流动 `deepseek-ai/DeepSeek-V4-Flash`（第三方渠道）。注意两渠道模型版本**不同步**——官方发新版当天，第三方托管（百炼/硅基流动）仍是旧版，恰好可充当"旧版备用"。

## Switching Day-to-Day Model

The daily conversation model is controlled by `config.yaml`:

```bash
hermes config set model.default "glm-5.2"
hermes config set model.provider "deepseek"
hermes config set model.base_url "https://..."
hermes config set model.api_key "sk-..."
hermes gateway restart
```

**⚠️ Critical: Gateway restart from outside only.** Hermes blocks `hermes gateway restart` when called from within the gateway process (prevents loop). Must be run from a real terminal.

## Adding a Custom Provider (Plugin)

When built-in providers don't match your API (wrong URL, wrong env var, missing model in whitelist):

### Step 1: Create plugin directory

```
~/.hermes/plugins/model-providers/<name>/
├── plugin.yaml
└── __init__.py
```

### Step 2: plugin.yaml

```yaml
name: bailian-provider
kind: model-provider
version: 1.0.0
description: 阿里百炼 DashScope 国内版
author: Emma
```

### Step 3: __init__.py

```python
"""阿里百炼 DashScope (国内版) provider profile."""

from providers import register_provider
from providers.base import ProviderProfile

bailian = ProviderProfile(
    name="bailian",
    aliases=("bailian", "aliyun-bailian", "dashscope-cn"),
    env_vars=("BAILIAN_API_KEY",),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

register_provider(bailian)
```

### Step 4: Point Hermes at it

```bash
hermes config set model.default "glm-5.2"
hermes config set model.provider "bailian"
hermes config set model.base_url ""         # empty = use plugin default
hermes config set model.api_key "sk-..."    # or let plugin read env var
hermes gateway restart
```

## Known Provider Quirks

### alibaba (DashScope)
- **Built-in URL**: `dashscope-intl.aliyuncs.com` (国际版) — NOT `dashscope.aliyuncs.com` (国内版)
- **Built-in env var**: `DASHSCOPE_API_KEY` — NOT `BAILIAN_API_KEY`
- **Model whitelist**: only lists `glm-5` (not `glm-5.2`). However, the whitelist is cosmetic — unlisted models may still work. If gateway reverts on restart, the real cause is likely a URL/auth mismatch, not the missing model name.

### deepseek
- **Base URL**: `api.deepseek.com` — NOT `api.siliconflow.cn`
- Using deepseek provider with a non-DeepSeek URL will cause gateway to revert config on restart.
- Use a custom plugin for alternative endpoints serving DeepSeek models.
- **模型别名映射** ⚠️：DeepSeek 官方 API 会将 `deepseek-chat` 这个别名**内部路由至 `deepseek-v4-flash`**。即你在代码里写 `model: "deepseek-chat"`，实际调用的是 `deepseek-v4-flash`。这是服务端路由策略，不是 Hermes 的配置问题。可以通过 `curl https://api.deepseek.com/v1/models`（Bearer auth）查看官方实际可用的模型列表——只会看到 `deepseek-v4-flash` 和 `deepseek-v4-pro`，没有 `deepseek-chat`。建议所有脚本直接写 `deepseek-v4-flash` 以避免混淆。
- **API Key**: `DEEPSEEK_API_KEY`（env var）
- **模型同标识平滑升级 + 服务端跨档路由（2026-09-10 V4.1 Flash 实测）**：DeepSeek 官方发布新版时通常**不换模型标识**——`deepseek-v4-flash` 发布后自动指向 V4.1 Flash（调用名不变，服务端路由）。官方还会做跨档路由：V4.1 Flash 上线后、V4.1 Pro 上线前，**对 `deepseek-v4-pro` 的请求全部路由到 V4.1 Flash 并按 V4.1 单价计费**。因此用户要求"升级到 V4.1"时大概率**零配置改动**。核查方法：发布前 `curl https://api.deepseek.com/v1/models`（Bearer auth）记基线 → 发布后重查——若仍是旧标识集合=平滑升级，别乱改 config；若出现新独立标识才需要 `config set model.default`。⚠️ 第三方托管渠道（百炼/硅基流动）版本跟进滞后，官方发布当天仍是旧版；且第三方价格与官方独立。官方定价页可能挂"近期整体上调"预告——涨价窗口前是低成本囤量期。
- **💰 高峰时段价格翻倍**：DeepSeek 在以下北京时段价格翻倍：**每日 9:00-12:00、14:00-18:00**。所有 cron 定时任务必须排在这些时段之外。可用非高峰窗口：
  - 凌晨：0:00-8:59（最佳）
  - 午休：12:00-13:59
  - 晚间：18:00-23:59

### custom
- **Designed for**: Ollama/local OpenAI-compatible endpoints
- **Also works with**: OpenAI-compatible cloud APIs (硅基流动等) that use standard Bearer token auth + `/v1/chat/completions`。**实测可用的云 API**：硅基流动 (`api.siliconflow.cn/v1`)。
- Has `think=False` and `num_ctx` Ollama-specific logic, but found to work fine for cloud APIs.
- **硅基流动 (SiliconFlow) 快速配置示例**:
  ```bash
  # 确认 SILICONFLOW_API_KEY 已写入 .env
  hermes config set model.provider "custom"
  hermes config set model.base_url "https://api.siliconflow.cn/v1"
  hermes config set model.default "deepseek-ai/DeepSeek-V4-Flash"
  hermes config set model.api_key "$SILICONFLOW_API_KEY"
  hermes gateway restart  # 从终端运行
  ```
- **⚠️ 先测后配**：用 `curl` 或原生 Python 先测试 API key + endpoint + model 连通性，避免 gateway 静默回退。
- **Model naming**: 硅基流动的模型名用 HuggingFace 格式（如 `deepseek-ai/DeepSeek-V4-Flash`），不同于 DeepSeek 官方（`deepseek-v4-flash`）。用错名称会导致 404。

### zai (Z.AI / GLM)

- **Provider slug**: `zai` (aliases: `glm`, `zhipu`, `z-ai`, `z.ai`)
- **Env var**: `GLM_API_KEY` (also `ZAI_API_KEY`, `Z_AI_API_KEY`)
- **Transport**: `openai_chat` — full OpenAI-compatible API
- **Endpoint auto-detection**: Probes 4 endpoints with model-prefix matching:
  - `global` — `api.z.ai/api/paas/v4` (prefix: `glm-5`)
  - `cn` — `open.bigmodel.cn/api/paas/v4` (prefix: `glm-5`)
  - `coding-global` — `api.z.ai/api/coding/paas/v4` (prefix: `glm-5.1`, `glm-5v-turbo`, `glm-4.7`)
  - `coding-cn` — `open.bigmodel.cn/api/coding/paas/v4` (prefix: `glm-5.1`, `glm-5v-turbo`, `glm-4.7`)
- **Override**: Set `GLM_BASE_URL` in `.env` to skip auto-detection and use a fixed endpoint
- **glm-5.2 support**: `glm-5.2` matches the `glm-5` prefix → routes to `cn` endpoint automatically. Works despite not being in the model whitelist.
- **glm-5.2 is a reasoning model**: Spends 500+ tokens on `reasoning_content` before outputting `content`. Latency ~20s even for simple queries. Ensure Hermes has adequate `max_tokens`.
- **Full details**: See `references/zai-provider-details.md` for endpoint auto-detection, glm-5.2 behavioral profile, and API testing script.

## Model Switching Checklist

When the user asks to switch models:
1. **Identify the provider**: Built-in? Or need custom plugin?
2. **Prefer built-in providers**: The model whitelist in `hermes_cli/models.py` is **cosmetic only** — for autocomplete/display. It does NOT block unlisted models. If the provider's API supports a model, Hermes will use it regardless of whitelist. Only create a custom plugin when the provider's `base_url`, `transport`, or `env_vars` genuinely don't match your API.
3. **Check env var name**: Does `.env` have the right key? (`DASHSCOPE_API_KEY` vs `BAILIAN_API_KEY` vs `GLM_API_KEY` vs `SILICONFLOW_API_KEY`)
4. **Test API directly first**: Before touching Hermes config, verify the API key + endpoint + model combo works with a raw Python `urllib.request` call. Catches auth/endpoint issues before they become "Hermes silently reverted" mysteries.
5. **Write config**: `hermes config set model.default/provider/base_url/api_key`
6. **Restart gateway**: Must be from outside terminal
7. **Verify**: Send test message, check `hermes config` after restart

## Common Pitfalls

1. **Gateway silently reverts config on restart** — usually a URL/auth mismatch (wrong base_url for provider, wrong env var name, API key not in `.env`). The model whitelist is cosmetic and does NOT cause reverts. Always test the API directly with `urllib.request` before concluding Hermes is the problem.
2. **Creating custom plugins unnecessarily** — custom provider plugins are fragile and should be a LAST resort. Built-in providers (`zai`, `deepseek`, `alibaba`) often work for models not in their whitelist. The whitelist only controls autocomplete display, not runtime access. Try the built-in provider first.
3. **`model.api_key` persists after provider change** — if you switch from `deepseek` to `zai` but forget to update `api_key`, the old key may cause auth failures. Always clear/reset all four fields together.
4. **Custom provider not discovered** — plugins are loaded lazily at Hermes startup. `CANONICAL_PROVIDERS` static list won't show them; they appear only after `get_provider_profile()` / `list_providers()` runs.
5. **Gateway cannot self-restart** — the error `Refusing to restart the gateway from inside the gateway process` is intentional. Must run from terminal.
6. **Reasoning models need high max_tokens** — models like `glm-5.2` spend most tokens on `reasoning_content` before outputting. With low `max_tokens`, they may produce only reasoning and cut off the actual reply. Test with `max_tokens: 2000` to see full output.

## Verification Checklist

- [ ] `hermes config` shows correct `model.default`
- [ ] `hermes config` shows correct `model.provider`
- [ ] API key matches provider's expected env var
- [ ] Direct API test succeeds (raw Python `urllib.request` call)
- [ ] Gateway restart completed without silent revert
- [ ] Test message confirms model is active

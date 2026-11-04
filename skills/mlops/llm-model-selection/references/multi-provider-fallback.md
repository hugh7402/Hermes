# Multi-provider model chain with automatic fallback

For any skill or script that calls an LLM and must survive one vendor going down —
proposal writing, note enhancement, OCR, batch jobs. Pattern: an ordered provider
list, each with its own endpoint, model id and credential env var; the caller walks
the list and only moves on when a provider is truly exhausted.

## Skeleton

```python
_PROVIDERS = [
    {"label": "primary vendor",  "url": "https://api.deepseek.com/v1/chat/completions",
     "model": "deepseek-flash",           "key_env": "DEEPSEEK_API_KEY"},
    {"label": "fallback vendor", "url": "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
     "model": "deepseek-v4.1-flash-1017", "key_env": "BAILIAN_API_KEY"},
]

def call_llm(prompt, max_tokens=16000, temperature=0.3):
    errors = []
    for prov in _PROVIDERS:
        key = _read_key(prov["key_env"])
        if not key:
            errors.append(f"{prov['label']}: no {prov['key_env']} in .env")
            continue
        mt = max_tokens
        for attempt in range(3):
            try:
                body = {"model": prov["model"],
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": mt, "temperature": temperature}
                # provider-specific params are gated by HOST, never assumed
                if PLAN_THINKING == "0" and "dashscope" in prov["url"]:
                    body["enable_thinking"] = False
                d = json.loads(urllib.request.urlopen(
                    urllib.request.Request(prov["url"], data=json.dumps(body).encode(),
                        headers={"Authorization": f"Bearer {key}",
                                 "Content-Type": "application/json"}), timeout=600).read())
                ch = d["choices"][0]
                content = (ch.get("message") or {}).get("content") or ""
                if not content.strip():                       # gate 1: silent empty
                    mt = min(mt * 2, 32000); raise RuntimeError("empty content")
                if ch.get("finish_reason") == "length":        # gate 2: truncated
                    mt = min(mt * 2, 32000); raise RuntimeError("truncated")
                return content
            except Exception as e:
                if attempt == 2:
                    errors.append(f"{prov['label']} failed 3x: {e}")
                else:
                    time.sleep(5)
        if prov is not _PROVIDERS[-1]:
            print(f"⚠️ {prov['label']} unavailable, switching to fallback", file=sys.stderr)
    raise RuntimeError("all providers failed:\n  " + "\n  ".join(errors))
```

## Rules that matter

**Switch only after the retry budget is spent.** One 429 or a slow response must not push
every run onto the alternative — a blunt fallback silently moves all traffic and all cost
to the secondary vendor. 3 attempts, ~5s apart, then switch.

**Missing credential → skip immediately, no retries.** A key absent from `.env` will not
appear during three backoff sleeps. Check first, record why, move on.

**Log the switch to stderr.** stdout is often parsed by the caller (progress lines, report
text). A switch notice on stdout corrupts that; on stderr it lands in logs where an operator
will actually see "we ran degraded today".

**Aggregate every provider's error into the final exception.** A bare "all failed" hides
whether it was a missing key, a 404 model id, or a persistent 500 — the three need
different fixes.

**Provider-specific request params are gated by host string.** `enable_thinking: false` is
a DashScope body parameter; the DeepSeek official endpoint does not accept it (rejected or
silently ignored). Gate with `"dashscope" in url` instead of assuming all OpenAI-compatible
endpoints behave alike.

**Explicit override must disable the chain.** If the user forces a model via env var
(`PLAN_MODEL`, `PLAN_API_URL`, `PLAN_KEY_ENV`), collapse the provider list to that one
entry. Someone who pinned a model wants that model or an error — a silent fallback to a
different model breaks reproducibility of a benchmark or a document.

**Keep the two output gates inside the per-provider loop.** Empty `content` and
`finish_reason == "length"` double `max_tokens` on the *same* provider before declaring it
failed; otherwise a reasoning-budget problem looks like a vendor outage and you switch
departments for no reason.

## Verification recipe

The happy path proves nothing — it never touches the fallback branch. Test by breaking the
primary on purpose:

1. Point the primary's `model` at a nonexistent id (keep the fallback intact).
2. Call the function once.
3. Assert the switch line appears on stderr and the fallback's content comes back.
4. Time it: 3 attempts + 2 backoffs should land around 10–15s before the switch.

Also exercise each single-provider path (`PLAN_PROVIDER=primary|fallback`) so both
credentials are proven independently, not just the one that happened to answer.

## When not to use a chain

Do not stack providers to paper over a model-quality problem. If the models genuinely
differ in capability for the task, pick one and change it deliberately with the user's
consent — a fallback exists for availability, not for hedging a decision.

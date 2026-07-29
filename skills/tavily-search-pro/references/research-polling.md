# Tavily Research Async Polling Pattern

Tavily's Research API (`POST /research`) is asynchronous — returns immediately with:

```json
{"status": "pending", "request_id": "...", "created_at": "..."}
```

To get results, poll `GET /research/{request_id}` every 5 seconds until `status` == "completed".

## Implementation approach (tavily_search.py lines 395-440)

```python
def _research_poll(request_id, interval=5, timeout=180):
    url = f"{BASE_URL}/research/{request_id}"
    deadline = time.time() + timeout
    while time.time() < deadline:
        poll GET /research/{request_id}
        if "completed" → return data
        if "failed" → print error, exit
        sleep(interval)
    print timeout error, exit

def cmd_research(args):
    submit POST /research → get request_id
    result = _research_poll(request_id, timeout=args.research_timeout)
    return _format_research_results(result)
```

## Key parameters

| Parameter | Values | Notes |
|-----------|--------|-------|
| `--model` | `mini`, `pro`, `auto` | mini: ~30-60s, pro/auto: ~2-3min |
| `--timeout` | int (default 180) | Max wait seconds |

## Pitfalls

- Research with `auto` or `pro` model can take 2-3+ minutes. Always set `--timeout` high enough.
- `--model mini` is recommended for quick results (30-60s typical).
- The initial submit has a 30s HTTP timeout; the polling phase uses the `--timeout` value.
- The Tavily dev API key may have different behavior than production keys (rate limits, model availability).

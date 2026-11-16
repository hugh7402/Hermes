# Diagnosing "the messaging channel went silent"

Use when a user says "我给你发消息了，怎么没反应" on WeChat/Telegram/Slack/etc.
Do NOT restart the gateway first — in most cases the turn is still running and a
restart destroys the in-flight work. Prove liveness or prove death, in this order.

## 1. Is the gateway loop alive?

```bash
cat $HERMES_HOME/state/gateway.heartbeat      # {"pid":…, "updated_at":…, "mem":{…}}
tail -50 $HERMES_HOME/logs/gateway.log
```

`updated_at` within the last minute or two = the loop is ticking; the channel is
not wedged at the process level. Memory pressure shows here too (`swap_used_kib`).

## 2. Is a turn in flight?

The gateway only writes log lines at turn *boundaries* (`inbound message …`,
`response ready …`). A 5-minute turn produces **no log lines at all** while it
runs its tool loop, so log silence proves nothing. The authoritative signal is
the turn lease:

```python
import sqlite3, time
con = sqlite3.connect(f"file:{HOME}/state.db?mode=ro", uri=True, timeout=15)  # HOME=/opt/data, $HERMES_HOME
for conv, holder, expires in con.execute("select conversation_id, holder, expires_at from session_turn_leases"):
    print(conv[:40], "expires in %.0fs" % (expires - time.time()), holder[:60])
```

A non-expired row for the platform conversation id = **the agent is actively
working that turn**. Do not interrupt it; report "在跑，还没回" plus what it is
doing.

Note: `state.db` may be ~1 GB. Query it with python's `sqlite3` over a `mode=ro`
URI — that is the portable path (no shell `sqlite3` dependency) and avoids
locking the live gateway.

## 3. What is it actually doing?

`messages.timestamp` is a **float epoch, UTC**; convert with
`datetime.datetime.fromtimestamp()` before quoting a clock time to the user.

```python
sid = "<session_id>"
def ts(e): return datetime.datetime.fromtimestamp(e).strftime('%H:%M:%S')
for r in con.execute("""select rowid, role, tool_name, timestamp, finish_reason,
                        substr(content,1,160)
                 from messages where session_id=? order by rowid desc limit 10""", (sid,)):
    print(r[0], r[1], r[2], ts(r[3]), r[4], (r[5] or '').replace("\n", " "))
```

The newest `rowid` advancing while you watch = alive and progressing. A newest
rowid that has not moved for several minutes with a live lease = genuinely
stuck; that is when an interrupt is justified.

## 4. The canned filler that gets mistaken for "没反应"

When a new inbound message supersedes a turn that has not started producing yet,
Hermes answers the superseded turn with the literal English string:

> `Your request was not processed. Send it again if you still want me to carry it out.`

This is what the user sees, and it reads as a refusal/silence. The classic
trigger is a **text message followed ~2 s later by an image**: the text turn is
dispatched, the image arrives, and the text turn is dropped. Count occurrences
to confirm the pattern before blaming anything else:

```python
con.execute("select session_id, count(*) from messages where content like 'Your request was not processed%' group by session_id").fetchall()
```

If the count is non-zero and the timestamps pair with text-then-image pairs,
the fix is behavioural, not config: tell the user to **send the image first,
wait for the reply, then send the text instruction** — or put everything in one
message. Do the same yourself: never emit a text reply and an image attachment
in the same breath when a follow-up instruction is still coming.

## 5. Check session bloat before recommending `/new`

Long, image-heavy platform sessions degrade quietly:

```bash
grep -E "Session hygiene|bounding the model payload|Clean EOF" $HERMES_HOME/logs/gateway.log | tail -20
```

- `bounding the model payload to 399 of 402 messages (hard limit 400)` — the
  stored transcript is over the cap; every turn silently drops older messages.
- `compression … exceeded the turn-hold budget … proceeding without compression`
  — compression is too slow to land inline, so it keeps being abandoned.
- repeated `Clean EOF, no finish_reason` from the provider — the turn is being
  re-tried mid-stream; turns get slow and flaky.

These three together mean the platform session needs a fresh start. Offer it
explicitly (`/new` on that chat), and reassure the user that disk artifacts
(generated prototypes, downloaded media, measurement data) survive — only the
conversation context resets.

## Verdicts

| Evidence | Verdict | Action |
|---|---|---|
| heartbeat fresh + live lease + rowid advancing | working, just slow | report progress, wait |
| heartbeat fresh + live lease + rowid frozen 5 min | genuinely stuck | interrupt / restart from an external shell |
| canned "not processed" message in transcript | superseded by follow-up message | explain the send order, ask to resend |
| heartbeat stale | gateway loop dead | restart (see `references/gateway-restart-verification.md`) |

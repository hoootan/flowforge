# Step primitives

FlowForge's durability comes entirely from `step.*` primitives. Each step
call yields control back to the server; the server persists the step's
input hash and output, then schedules a continuation. The function body
replays from the top on every continuation — only uncached step calls
actually execute.

This is the single most important mental model in the platform. Everything
below follows from it.

## Signatures

```python
# 1. Deterministic side effect (the workhorse).
result = await step.run("fetch-order", fetch_order_from_db, order_id)

# 2. LLM call with retries, token counting, cost tracking.
summary = await step.ai(
    "summarise",
    model="claude-sonnet-4-6",
    prompt="Summarise this order for the ops team:\n" + order_json,
)

# 3. Pause until a matching event arrives.
payment = await step.wait_for_event(
    "wait-for-payment",
    event="payment/received",
    match={"order_id": order_id},
    timeout="24h",  # optional
)

# 4. Call another function, block on its result.
shipping = await step.invoke(
    "book-shipping",
    function_id="ship-order",
    data={"order_id": order_id, "address": addr},
)

# 5. Fanout — emit an event and keep going. Non-blocking.
await step.send_event(
    "notify-ops",
    name="order/processed",
    data={"order_id": order_id},
)

# 6. Durable sleep. Survives worker restart.
await step.sleep("backoff", "5m")
```

## Rules that follow from the replay model

### Rule 1 — non-determinism lives inside steps

Wrong:

```python
@flowforge.function(id="bad")
async def bad(ctx):
    now = datetime.utcnow()        # runs on every replay; different each time
    key = uuid.uuid4().hex         # same
    await step.run("persist", save, key, now)
```

Right:

```python
async def _now_and_key():
    return {"now": datetime.utcnow().isoformat(), "key": uuid.uuid4().hex}

@flowforge.function(id="good")
async def good(ctx):
    meta = await step.run("stamp", _now_and_key)
    await step.run("persist", save, meta["key"], meta["now"])
```

The output of `_now_and_key` is memoised under the id `"stamp"`; every replay
gets the same values.

### Rule 2 — no side effects outside steps

Anything that writes to the outside world (DB, HTTP, files, message bus) has
to be inside `step.run` or `step.send_event`. Otherwise it fires N times.

Common footgun:

```python
logger.info(f"processing order {order_id}")  # fine — logging is idempotent
send_slack(f"order {order_id} started")      # NOT fine — will spam
```

If you need a one-shot side effect, wrap it:

```python
await step.run("slack-started", send_slack, f"order {order_id} started")
```

### Rule 3 — step ids must be unique within a function

The id is the memoisation key. Two `step.run("fetch", ...)` calls in the same
function replay as if they're the same step and collide. Use descriptive ids:
`"fetch-order"`, `"fetch-customer"`, not `"fetch"` twice.

If you need to do the same thing in a loop, include the iteration in the id:

```python
for item in items:
    await step.run(f"process-{item.id}", process_one, item)
```

## `step.wait_for_event` — the subtle one

`match` is a shallow dict equality check against `event.data`. The event must
still arrive at the server; `wait_for_event` just suspends the run until one
fires whose data matches.

- No match → waits forever (or until `timeout`).
- `timeout` expired → raises, the function can catch and branch.
- Multiple matches in flight → the first one wins; the rest continue past the
  waiting function and may trigger other functions.

If you want cross-function coordination, this is the primitive. If you want
fanout, use `step.send_event` (non-blocking) instead.

## `step.invoke` vs `step.send_event`

- `step.invoke` — synchronous from the caller's perspective. Caller waits for
  the invoked function's run to complete and gets its return value. Pick this
  when you need the result.
- `step.send_event` — fire-and-forget. Caller continues immediately. Pick
  this when you don't care about the downstream outcome, or when multiple
  functions might listen.

Both create new `Run` rows, both show up in `flowforge_list_runs`, and both
survive the caller's crash.

## `step.ai` internals

- Talks to the configured LLM provider via LiteLLM, so model strings like
  `claude-sonnet-4-6`, `gpt-4o`, `claude-opus-4-7` all work.
- Token counts and cost land on the step row. `flowforge_get_run_steps`
  includes these.
- No tools available here — this is a plain completion call. For agentic
  behaviour with tools, use an inline function or `step.agent`.

### Rate-limit handling (429) — durable retry

When the provider returns 429, FlowForge does **not** block the executor
worker sleeping. Instead it expands the logical `step.ai` into a chain of
real durable sub-steps and frees the worker between them:

```
foo                     # attempt 1 — rate-limited, output.__rate_limited = true
foo/retry-sleep-1       # step.sleep for Retry-After seconds (± 20% jitter)
foo/attempt-2           # attempt 2 — succeeds, normal AI response
```

Same mechanism applies inside `step.agent` — each `iter-N/think` grows its
own attempt chain; earlier iterations stay memoised and are never replayed.

**Knobs:**

- `num_retries=N` kwarg on `step.ai(...)` / `step.agent(...)` — per-call
  budget. Pass `num_retries=0` to disable retry and get an immediate
  typed exception.
- `FLOWFORGE_LLM_NUM_RETRIES` env var — workspace/worker default.
  Falls back to `LITELLM_NUM_RETRIES` for back-compat. Default 5.
- `FLOWFORGE_LLM_MAX_RETRY_DELAY` env var — per-attempt sleep ceiling in
  seconds. Default 120.

**Typed exception:** when retries exhaust, the SDK raises
`flowforge.RateLimited(retry_after, provider, model, original, ...)`.
Catchable via `except RateLimited`, `except RetryableError`, or `except
StepFailed` (all three — linear hierarchy).

```python
from flowforge import RateLimited

try:
    result = await step.agent("research", ..., num_retries=5)
except RateLimited as e:
    # Fallback: switch provider, park the run, notify the user.
    await step.send_event("fallback", name="rate_limit/park", data={"retry_after": e.retry_after})
```

### Proactive throttling (avoid 429s entirely)

Declare a token-bucket pre-flight cap on `@flowforge.function(...)`:

```python
from flowforge import TokenRateLimit

@flowforge.function(
    id="research",
    rate_limits=[TokenRateLimit("claude-sonnet-4-6", tokens_per_minute=25_000)],
)
async def research(ctx):
    ...
```

The server estimates the request size via `litellm.token_counter` and, if
the bucket is full, returns the same `__rate_limited` signal — the SDK
loop absorbs it durably. No provider 429 round-trip. Recommended when
you know your TPM tier (always cheaper than reactive retry).

## When to avoid steps

If an operation is trivially pure (string concatenation, filter, local
parsing), you don't need a step. Every step round-trips through the server
and costs latency. Reserve steps for things that:

- Write to the outside world, or
- Cost non-trivial time/money (LLM calls, network IO), or
- Must survive crashes.

## Common misuses — flag these on review

- Doing HTTP calls with `requests`/`httpx` at top-level. Wrap in `step.run`.
- Using a single `step.run("main", ...)` that does everything. Defeats the
  whole replay model — you can't see progress, can't retry individual steps.
- `await asyncio.sleep(...)` for delays. Not durable. Use `step.sleep`.
- Reading env vars / config inside the function body. If the env changes
  between replays, behaviour diverges. Either load once at module level or
  read it inside a `step.run`.

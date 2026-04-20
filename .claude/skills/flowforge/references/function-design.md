# Function design

Picking worker mode vs inline, and tuning agent_config for inline functions.

## Worker vs inline: the picker

Answer these in order. First "yes" decides it.

1. Does the function need full Python (numpy, pandas, pydantic, your own
   internal libs, framework code)? → **worker**.
2. Does the function hit services that require a long-lived network identity
   (VPN, private VPC, mTLS)? → **worker**.
3. Does the function execute business logic that can be expressed as "a
   model with these tools following these instructions"? → **inline**.
4. Is the primary author a non-engineer clicking through the dashboard? →
   **inline**.

Rule of thumb: if you find yourself reaching for `step.ai` three times in a
row, the function probably wants to be inline. Let the agent loop do the
work.

## Worker mode skeleton

```python
import flowforge

app = flowforge.FlowForge(api_key="ff_live_…")

@app.function(
    id="process-order",
    name="Process Order",
    trigger=flowforge.trigger.event("order/created"),
    retries=3,
    concurrency=10,
    rate_limit={"limit": 100, "window": "1m"},
)
async def process_order(ctx):
    order_id = ctx.event.data["order_id"]

    order = await step.run("fetch", fetch_order, order_id)
    enriched = await step.ai("enrich", model="claude-sonnet-4-6",
                             prompt=f"Enrich this order: {order}")
    await step.run("persist", save_enriched, order_id, enriched)
    await step.send_event("notify", name="order/enriched",
                          data={"order_id": order_id})
```

Config knobs on `@function()`:

- `retries` — run-level retry count. Step-level retries are separate.
- `concurrency` — max simultaneous runs of this function per tenant.
- `rate_limit` — `{limit, window}`. Server-side throttle.
- `debounce` / `throttle` — dedup windows; see SDK docs.

## Inline function skeleton

Inline functions don't have Python source — you describe them by system
prompt + tool list. Created via the dashboard, the API, or
`flowforge_create_inline_function`.

```jsonc
{
  "id": "create-post",
  "name": "Create Social Post",
  "trigger": {"type": "event", "value": "content/requested"},
  "system_prompt": "You are a social copywriter. Given a topic, use the \
    tools to research recent angles and produce one LinkedIn post under 280 \
    characters. Return JSON: {headline, body, hashtags}.",
  "tools": ["web_research", "keyword_enrichment"],
  "agent_config": {
    "model": "claude-sonnet-4-6",
    "max_iterations": 20,
    "max_tool_calls": 15
  }
}
```

Rules:

- Every name in `tools` must already exist (look up via `flowforge_list_tools`
  or the dashboard). Soft-deleted tools are excluded by the server since
  v0.4.0.
- `agent_config.model` defaults to `claude-sonnet-4-6`. LiteLLM model IDs all
  work; for Anthropic specifically use the ones from CLAUDE.md ("Opus 4.7
  → `claude-opus-4-7`", etc).
- `max_iterations` caps the agent loop; `max_tool_calls` caps individual
  tool invocations per run. When either is exceeded the run ends in a
  terminal state and the caller gets back whatever the agent last emitted.

## Sub-agents

Declare sub-agents inside `agent_config.sub_agents`. Each becomes a tool the
parent agent can call to delegate a focused task:

```jsonc
"agent_config": {
  "model": "claude-sonnet-4-6",
  "sub_agents": {
    "researcher": {
      "description": "Use to gather factual context before drafting.",
      "system_prompt": "You are a research assistant. Return bullet-point \
        findings with source URLs.",
      "tools": ["web_research"]
    }
  }
}
```

Design notes:

- Sub-agents isolate context — they have their own system prompt and
  (optionally) their own tool set. Good for expensive work the parent
  shouldn't see the raw output of.
- The `description` field is what the parent agent reads when choosing
  which sub-agent to call. Write it like you'd write any tool description:
  what it does, when to use it, what it returns.
- Sub-agents consume iterations from the parent's budget. Plan accordingly.

## Triggers

- **Event** — `trigger.event("order/created")`. Match by name. Add
  `expression="event.data.amount > 100"` to filter by data content.
- **Cron** — `trigger.cron("0 9 * * *")` for scheduled runs. No event
  payload; `ctx.event.data` is empty.
- **Webhook** — `trigger.webhook("/my-path")`. Triggered by HTTP hit, not
  event fan-out.

## Testing functions

Locally: `flowforge dev .` starts the SDK dev loop. Use
`flowforge send <event> -d '{"key": "value"}'` (or
`flowforge_send_event` via MCP) to fire. Runs show up at
`http://localhost:3000/runs`.

Run history is preserved when a function is soft-deleted — so if you need to
test with fresh state, use a different `function_id` rather than
delete-and-recreate (which resurrects the old row's history).

## Common design smells

- **Function that never completes** — missing `step.run` on an outbound
  call, so the function exits before the write finishes. Or a
  `step.wait_for_event` with no matching event ever fired. Check
  `flowforge_get_run_steps` for where the trace ends.
- **Function that calls itself** — `step.invoke` with the same
  `function_id` as the caller is allowed but dangerous; ensure termination.
- **Inline function returning wrong shape** — the system prompt must
  explicitly specify the return format. LLMs ignore weak "return JSON"
  requests; use concrete schemas.
- **Agent burns through iterations without tool calls** — usually means the
  system prompt is unclear about when to stop. Add a terminal condition
  ("Return {…} when the order is fully enriched; do not continue after that").

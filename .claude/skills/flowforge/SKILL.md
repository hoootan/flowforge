---
name: flowforge
description: Expert guidance for building, debugging, and deploying workflows on FlowForge — the durable event-driven AI workflow platform (functions, tools, agents, runs, skills, tasks, approvals). Use this skill whenever the user is writing a FlowForge function or SDK workflow, designing an inline/agent function, wiring custom or webhook tools, sending events, debugging failed runs, choosing between retry and replay, using step.run / step.ai / step.wait_for_event / step.invoke / step.send_event / step.sleep, integrating the flowforge-mcp-server, working with Redis fair queues or the Docker compose stack, planning a stravix or production deployment, authoring a migration under server/migrations, or troubleshooting soft-deleted functions and tools. Trigger even when the user doesn't say "FlowForge" but mentions flowforge_* MCP tools, ff_ API keys, or file paths under packages/flowforge-sdk, packages/flowforge-mcp, or server/src/flowforge_server.
---

# FlowForge developer skill

FlowForge is a production AI workflow orchestration platform with durable,
event-driven execution, agent team management, and a skill marketplace. This
skill helps you (a) pick the right primitives, (b) avoid the gotchas that bit
past users, and (c) ship cleanly.

The platform has three "faces":

- **SDK** (`packages/flowforge-sdk`) — Python decorators + `step.*` primitives
  for workers you run on your own infra.
- **Inline/agent functions** — Serverless functions that run on the FlowForge
  server, driven by an LLM + tools. No `endpoint_url` needed.
- **MCP server** (`packages/flowforge-mcp`, published as `flowforge-mcp-server`)
  — Exposes every resource as a tool an LLM client (Claude Code, etc.) can
  call directly. See the `packages/flowforge-mcp/README.md` for the
  description standard all tools follow.

Before writing any code, anchor on the **core execution model** below and the
**decision points** that follow. Deep dives live in `references/`.

## Core execution model

Event arrives at `POST /api/v1/events` → server matches registered **functions**
by trigger (`event` / `cron` / `webhook`) → creates a **run** and enqueues a
job to the Redis fair queue → **executor** dequeues, invokes the function →
function executes until a `step.*` call raises `StepCompleted` → server saves
the step result and re-enqueues for continuation → repeats until the function
returns (completes) or raises (fails).

Key invariants a new user reliably misses:

- **Steps are memoised by hash.** On replay the server returns the cached
  result instead of re-running the function body. This is why functions must
  be **deterministic between step boundaries** — any non-deterministic work
  (timestamps, randoms, external reads) belongs inside `step.run` so its output
  is durable.
- **The function body runs many times.** Every time a step resolves, the whole
  function replays from the top. Putting side effects outside `step.*` means
  they happen *N* times.
- **`is_active=False` stops new event matching but does not cancel in-flight
  runs.** Same for soft-deletes (functions and tools) — the row hangs around
  so history and running executions stay intact.

See `references/step-primitives.md` for the full step menu and
`references/function-design.md` for when to pick worker mode vs inline.

## When to use which primitive

Quick-triage table. Follow the reference link for nuance.

| Goal | Use | Notes |
|------|-----|-------|
| Durable side effect (API call, DB write) | `step.run(id, fn, *args)` | Memoised; idempotent on replay |
| Let an LLM do something | `step.ai(id, model=, prompt=)` | Durable 429 retry (attempt-N/retry-sleep-N chain), typed `RateLimited` on exhaustion |
| Pause until an event fires | `step.wait_for_event(id, event=, match=)` | Resumed by matching event; see `references/step-primitives.md` for match semantics |
| Call another function | `step.invoke(id, function_id=, data=)` | Blocks until target run completes |
| Emit an event (fanout) | `step.send_event(id, name=, data=)` | Non-blocking; other functions pick it up |
| Delay | `step.sleep(id, duration)` | Durable, survives restart |
| Human approval on a tool call | `requires_approval=True` on the tool | Gated via `/approvals`; not a step |

**Worker vs inline function choice:**

- Worker mode if you need full Python runtime, your own libs, your own infra,
  or heavy business logic. Register via `@flowforge.function()` in the SDK.
- Inline if the behaviour can be expressed as "an LLM with these tools and
  this system prompt." Create via the dashboard or
  `flowforge_create_inline_function` MCP tool. See `references/function-design.md`
  for agent_config knobs (model, max_iterations, max_tool_calls, sub_agents).

**Tool type choice** (see `references/tool-design.md` for the full matrix):

- `custom` — Python sandbox (`execute(**kwargs)`). Fast to author, no external
  infra, but runs inside RestrictedPython 8.x with a whitelist of imports.
  Never put secrets in the code — use `{{credential:name}}` placeholders.
- `webhook` — HTTP endpoint. Best when you already have a service. Supports
  `{{credential:name}}` and `{{env:VAR}}` placeholders in URL and headers.
- `builtin` — Platform-provided. Reference by name only.

## Authentication model (both halves)

FlowForge has two separate auth mechanisms and new users confuse them:

- **Dashboard users** — email/password → JWT. Roles: admin, member, viewer.
  Used by humans on `https://…/login`.
- **API keys** (`ff_live_*`, `ff_test_*`, `ff_ro_*`) — server-to-server, used
  by the SDK and MCP server. Format `ff_{type}_{random}`. Scoped permissions.

If an integration fails with 401, check which auth is being used. The SDK
needs an API key; the dashboard uses JWT. The MCP server uses an API key
passed via `X-FlowForge-API-Key`.

## The MCP server

If an LLM client is already connected to `flowforge-mcp-server`, prefer its
tools over ad-hoc `curl` / `psql`. Every tool's description now carries
explicit "when to use vs sibling tool" guidance (enforced by a CI lint test
in `packages/flowforge-mcp/tests/tool-descriptions.test.ts`). The siblings
that most commonly confuse callers:

- `flowforge_retry_run` ↔ `flowforge_replay_run` — retry resumes from the
  failed step with memoised successes intact; replay re-executes from
  scratch into a new run. Pick retry for transient failures, replay after
  code changes.
- `flowforge_create_function` ↔ `flowforge_create_inline_function` — worker
  mode (your server) vs serverless agent (FlowForge server).
- `flowforge_get_run_steps` ↔ `flowforge_get_run_tool_calls` — full step
  trace vs just the tool-call events.

If a user asks you to add a new MCP tool, read
`packages/flowforge-mcp/README.md` first — it codifies the description
standard (≥ 80 chars, ≥ 2 sentences, sibling cross-references, destructive
warnings, list ordering, every param `.describe()`d). The test at
`packages/flowforge-mcp/tests/tool-descriptions.test.ts` enforces it.

## Soft-delete semantics

Both `functions` and `tools` use `deleted_at`-based soft-delete:

- DELETE hides the row from user-facing queries and sets `is_active=False`
  so event matching (functions) and the executor's tool loader (tools) stop
  picking it up. In-flight runs that already loaded the row keep going —
  primary-key lookups in the executor do not filter `deleted_at`.
- Re-registering the same `function_id` (worker register, inline create) or
  creating a tool with the same name **resurrects** the soft-deleted row
  rather than hitting the unique constraint. Same UUID, cleared timestamp.
- Run history, task links, and comments continue to resolve the function or
  tool by its UUID — that's the whole point.

Anytime a user says "I deleted X but Y still references it" or "I can't
re-create X after deleting it", recall these semantics before diagnosing.
Details in `references/debugging.md`.

## Deployment

Local dev runs via `docker-compose up -d` + `flowforge dev .`. Production
deploys have two critical rules captured in user memory:

- **Always use `-f docker-compose.prod.yml`** on stravix (`135.181.109.95`,
  `ff.stravix.app`). The dev `docker-compose.override.yml` strips host ports
  and bakes the wrong `NEXT_PUBLIC_API_URL` into the dashboard image. Nginx
  splits `/api/v1/` (9473) from `/` (9474).
- Migrations live at `server/migrations/*.py` and auto-run on server startup
  via `server/src/flowforge_server/db/migrations.py`. **They only execute
  functions named `upgrade(engine)`** — files that only export `up(session)`
  are silently skipped (Copilot caught this on the soft-delete PR). When
  authoring a new migration, copy `server/migrations/add_function_soft_delete.py`
  as the template; it exposes both shapes.

The `/sx-deploy` command automates the stravix path end-to-end. See
`references/deployment.md` for the full workflow, what to rebuild after which
paths change, and how to recover from a missing-column startup crash.

## Common debugging signatures

Quick pointers; full playbooks in `references/debugging.md`:

- `'code' object has no attribute 'errors'` when creating a custom tool →
  RestrictedPython 7 → 8 API drift. Fixed in v0.4.0; if you see it, the
  server is on an older image — redeploy.
- `Failed to delete function` in the dashboard → pre-v0.4.0 ORM-cascade
  conflict with NOT NULL FK on `Run.function_id`. Fixed by soft-delete.
- Function stuck "running" forever → check executor + runner container
  health; check Redis is reachable; `flowforge_cancel_run` if truly wedged.
- Tool calls silently dropped in an agent run → check `requires_approval`
  on the tool; pending approvals live in `flowforge_list_approvals`.
- `iter-N/think` sub-step finished at 0ms with `rate_limit_error` → server
  on a pre-retry-loop build. On current builds, 429s are durable:
  expect an `attempt-1` (rate-limited) + `retry-sleep-1` + `attempt-2`…
  chain instead. Set `num_retries=N` on `step.ai`/`step.agent` or
  `FLOWFORGE_LLM_NUM_RETRIES` on the worker. For proactive back-pressure,
  add `rate_limits=[TokenRateLimit(model, tokens_per_minute=N)]` on the
  function. Typed exception on exhaustion: `flowforge.RateLimited`.

## Getting the answer right on the first try

When a user comes in with a FlowForge question, anchor first on three things
before responding:

1. **Which face are they on?** SDK worker / inline agent / MCP usage /
   dashboard / ops. Different mental models apply.
2. **Which primitive is actually the right one?** A lot of FlowForge's power
   comes from `step.*`. Reaching for `step.ai` when `step.wait_for_event` is
   right, or `step.invoke` when `step.send_event` is right, produces correct
   output but wrong architecture — flag this.
3. **What's the blast radius?** Deletes on shared resources, migrations,
   force-restarts of running workflows — pause and confirm before doing
   these, even in auto mode.

## Reference files

Read the relevant file when the question needs more than the summary here:

- `references/step-primitives.md` — all six step methods with signatures,
  memoisation behaviour, replay semantics, and common misuses.
- `references/function-design.md` — worker vs inline picker, agent_config
  knobs, sub-agents, retry/concurrency/rate-limit config.
- `references/tool-design.md` — custom vs webhook vs builtin matrix,
  sandbox limits, credential placeholders, approval flow.
- `references/deployment.md` — dev vs prod compose, migration authoring,
  stravix + production deploy commands, recovery playbooks.
- `references/debugging.md` — run state machine, retry vs replay, soft-
  delete semantics, sandbox error map, FK/cascade pitfalls.

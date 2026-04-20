# Debugging

Playbooks for the failures FlowForge users actually hit. Start with the
symptom, follow the link.

## Run state machine

A run moves through: `pending → running → (paused)* → completed | failed |
cancelled`. `paused` fires when the run is waiting on `step.wait_for_event`
or a tool approval.

- `flowforge_get_run` — header row (status, timing, trigger event).
- `flowforge_get_run_steps` — step-by-step trace with inputs/outputs/timing.
  Use this to find *where* a failure happened.
- `flowforge_get_run_tool_calls` — just the tool events (narrower view).
  Use this when debugging agent tool selection.

If the run is in `failed`, the last step's output has the error message.
If it's stuck in `running` with no recent step timestamps, suspect the
executor/runner is unhealthy (see "stuck runs" below).

## Retry vs replay — the two most confused siblings

| | retry | replay |
|---|---|---|
| Resumes from | the failed step | the very beginning |
| Memoised step results | kept | discarded |
| Creates a new run row | no (continues the same one) | yes (fresh UUID) |
| When to use | transient failure (network blip, rate limit) | after code/config change, or to reproduce a completed run |

Rule of thumb: **if the bug was outside the function, retry; if the bug
was inside the function and you've changed something, replay.**

`flowforge_retry_run` requires status=`failed`. `flowforge_replay_run`
works on both `failed` and `completed`.

## Soft-delete semantics (functions + tools)

Both use `deleted_at` timestamp + `is_active=False`.

- **DELETE hides the row from user-facing queries** but preserves it for
  history and in-flight execution.
- Event matching (functions) and tool loading (tools) filter on
  `is_active=True`, so soft-deleted rows stop being picked up for new work.
  In-flight runs that already loaded the row keep going to completion.
- **Re-creating with the same `function_id` or tool name resurrects the
  original row** (same UUID, `deleted_at` cleared). This is how you "undo"
  a delete.

Symptom → diagnosis:

- *"I deleted it but the dashboard still shows it"* → you're on a pre-v0.4.0
  server. Upgrade.
- *"I can't re-create tool X, 409 conflict"* → the soft-deleted row is
  holding the unique slot. Fixed in v0.4.0 (the create path resurrects).
  On an older server, hard-delete the row manually in SQL.
- *"I deleted tool X but my agent still called it"* → the run was already
  in flight when you deleted. Expected. New runs won't load it.
- *"I deleted function X but there's still a run for it"* → the run
  predates the delete. The function's name still resolves from the UUID
  for history purposes — that's by design.

## Sandbox errors (custom tools)

- **`'code' object has no attribute 'errors'`** — RestrictedPython 7 → 8
  API drift. Fixed in v0.4.0. If you see this, the server image is stale.
- **`SandboxSecurityError: Import of module 'X' is not allowed`** — your
  custom tool tried to import something outside the whitelist (`json`,
  `datetime`, `math`, `re`, `collections`, `itertools`, `functools`). Use
  `http_request` for HTTP (pre-injected); otherwise rethink — the sandbox
  is deliberately narrow.
- **`SandboxCompilationError: Compilation failed: ...`** — syntax error or
  `__class__`/`__bases__`/etc access. Fix the code.
- **`SandboxTimeoutError: Tool execution timed out after 30 seconds`** —
  your tool took too long. If the work is legitimately slow, move it to a
  webhook tool.

## Rate-limit (429) signatures

FlowForge expands rate-limited LLM calls into a durable chain:
`{step_id}` (first attempt, marked rate-limited) → `{step_id}/retry-sleep-1`
→ `{step_id}/attempt-2` → … until success or exhaustion.

- *"Sub-step finished in 0ms with `rate_limit_error`"* on old runs → server
  on a pre-retry-loop build. Redeploy; re-run with `flowforge_retry_run`.
- *"Run is stuck in `running` with a `.../retry-sleep-N` child"* — expected.
  The worker is free; the executor is waiting on the durable sleep. Should
  wake within `Retry-After` seconds. Check the step's `output.duration_seconds`.
- *"`RateLimited` raised, run failed"* — retries exhausted. Inspect the
  last-attempt step's `output.__retry_after` / `output.__provider`. Either
  bump `num_retries` on the call, raise `FLOWFORGE_LLM_NUM_RETRIES`, lower
  the declared `rate_limits=[TokenRateLimit(...)]` on the function, or
  upgrade the provider tier.
- *"Anthropic TPM never recovers"* — check
  `flowforge_llm_retries_total{provider="anthropic"}` in Prometheus. If it
  increases faster than real load, you're pointed at a deprecated key /
  wrong tier / shared org.
- *"Token-bucket says wait but provider has capacity"* — your declared
  `tokens_per_minute` is too low for the actual tier. Either raise it or
  remove the declaration (rely on reactive 429 retry instead).

Knobs (all live on the worker, not the server):

- `FLOWFORGE_LLM_NUM_RETRIES` (default 5) / `LITELLM_NUM_RETRIES` (fallback).
- `FLOWFORGE_LLM_MAX_RETRY_DELAY` (default 120s per attempt).

## Stuck runs

- `docker compose -f docker-compose.prod.yml ps` — check executor and
  runner are healthy. The runner invokes the user function; the executor
  handles step continuation.
- `docker logs flowforge-redis 2>&1 | tail` — the fair queue lives here.
  If Redis is down, nothing moves.
- If a run is truly wedged with no healthy path to completion, cancel it
  with `flowforge_cancel_run` and replay.

## Pending-approval traps

If an agent's tool has `requires_approval=True`, each call creates an
`Approval` row and pauses the run. Unresolved approvals keep the run in
`paused` indefinitely (or until `approval_timeout` auto-rejects).

- `flowforge_list_approvals status:"pending"` — triage.
- `flowforge_approve_tool_call` — resume with optional argument tweaks.
- `flowforge_reject_tool_call` — irreversible for this run; the step
  fails with your reason.

If a run surprises you by pausing, check approvals first.

## Migration / schema mismatches

- *"column X does not exist"* on server startup → migration didn't run.
  See `references/deployment.md` §"Migrations" for the `upgrade(engine)`
  gotcha and recovery.
- ORM cascade vs DB CASCADE — Functions have no FK references to tools
  (tools are named, not FK'd), so tool deletion never cascades into
  functions. For functions themselves, soft-delete sidesteps the cascade
  question entirely.

## "It works on my machine, not in prod"

Common causes, in rough order:

1. Dev compose rewrites `NEXT_PUBLIC_API_URL` — dashboard rebuild on prod
   without `-f docker-compose.prod.yml` bakes in the wrong URL.
2. API key type — you're using `ff_test_*` in a `ff_live_*` environment,
   or vice versa.
3. Tools referenced by name exist in dev but not prod (custom tools are
   per-tenant). Create them on prod via `flowforge_create_tool` or the
   dashboard.
4. Credentials missing on prod — webhook tools fail with 401/403 but the
   run error shows the downstream service's message, not "credential
   missing". Check `flowforge_list_credentials` before assuming the
   service itself is broken.

## Getting help out of a dead-end

If you've been debugging for 20 minutes and aren't making progress:

- Read the failing run's steps in full, not just the last one. Partial
  traces deceive.
- Check the audit log (`audit_logs` table) if present — it records deletes,
  permission changes, credential rotations.
- Compare against a known-good run of the same function. The step hash
  differences usually point at the non-determinism that's biting you.

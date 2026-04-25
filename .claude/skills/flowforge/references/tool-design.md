# Tool design

Tools are reusable capabilities inline functions and agents can call. Three
types, very different tradeoffs.

## The matrix

| | custom | webhook | builtin |
|---|---|---|---|
| Runs | inside FlowForge server (Python sandbox) | external HTTP service | inside FlowForge, maintained by the platform |
| Speed to author | minutes | depends on your service | zero (reference by name) |
| Secrets | `credentials.get("name")` (in code) | `{{credential:name}}` in URL + headers | N/A |
| Approval gate | `requires_approval=True` | same | same |
| Determinism | whatever your code does | whatever your service does | documented |
| Good for | glue, data transforms, domain-specific small logic | calling existing microservices, third-party APIs | standard capabilities (e.g. web search) |

## Custom tools (Python sandbox)

Since v0.4.0 the sandbox runs under RestrictedPython 8.x. What you get:

- Callable entry point: `def execute(**kwargs): ...`.
- Safe builtins: basic types, conversion, iteration, math, len/min/max, etc.
- Allowed imports: `json`, `datetime`, `math`, `re`, `collections`, `itertools`,
  `functools`.
- `json` / `datetime` / `math` / `re` are pre-imported into the sandbox.
- `http_request(url, method="GET", headers=None, json=None, timeout=30)` for
  SSRF-safe HTTP. Use this instead of any `requests`/`httpx`/`urllib` call.
- `credentials.get(name, default=None)` — pulls a decrypted secret from the
  encrypted credential store, scoped to the calling tenant. Created via
  `flowforge_create_credential` or the dashboard. Only `.get()` and `in` are
  exposed; you cannot enumerate names.
- Read-only `os.environ` proxy — `.get`, `[]`, `in` work; nothing else.
  Use this for non-secret runtime config; **secrets belong in `credentials`**.
- Execution cap: `DEFAULT_TIMEOUT_SECONDS = 30`.

What you don't get (by design — these raise `SandboxSecurityError`):

- `exec`, `eval`, `compile`, `open`, `__import__`, `__class__`, `__bases__`,
  `globals`, `locals`.
- `subprocess`, `os`, `sys`, `socket`, `threading`, `asyncio`, `requests`,
  `urllib`, `http`, `aiohttp`, `httpx`, `sqlite3`, `psycopg2`, etc.
- Any attribute starting with `__` via the restricted `_getattr_`.

Skeleton:

```python
def execute(url: str, selector: str) -> dict:
    # http_request is injected, not imported.
    resp = http_request(url, method="GET", timeout=10)
    if resp["status_code"] != 200:
        return {"error": f"http {resp['status_code']}", "body": resp["text"]}
    # parse (e.g. with `re` or `json`) and return plain dict
    return {"title": _extract(resp["text"], selector)}
```

With a credential (the typical third-party-API shape):

```python
def execute(query: str) -> dict:
    api_key = credentials.get("tavily_api_key")
    if not api_key:
        return {"error": "missing credential: tavily_api_key"}
    resp = http_request(
        "https://api.tavily.com/search",
        method="POST",
        headers={"Authorization": f"Bearer {api_key}"},
        json={"query": query},
    )
    return {"status": resp["status_code"], "body": resp["text"]}
```

Gotchas:

- **`a + b` vs `__iadd__`** — the sandbox's `_inplacevar_` shim uses
  `operator.iadd` so `lst += [1]` mutates in place correctly (fixed in
  v0.4.0 after a Copilot catch). Aliasing works.
- **Thread boundary** — execution happens on a daemon thread inside the
  server process. `time.time()` and blocking ops work, but anything that
  needs a real event loop does not. Use synchronous code.
- **Import of blocked module** — raises `SandboxSecurityError`, which
  bubbles out uncaught (no longer wrapped as `SandboxExecutionError` since
  v0.4.0). The agent sees this as a tool error.

## Webhook tools

Point at an HTTP endpoint you control. The server issues the request with
your method, headers, and body at tool-call time.

```json
{
  "name": "enrich_contact",
  "tool_type": "webhook",
  "webhook_url": "https://api.example.com/contacts/enrich",
  "webhook_method": "POST",
  "webhook_headers": {
    "Authorization": "Bearer {{credential:example_api_key}}",
    "X-Env": "{{env:FF_ENV}}"
  },
  "parameters": {
    "type": "object",
    "properties": {"email": {"type": "string"}},
    "required": ["email"]
  }
}
```

Placeholder rules:

- `{{credential:name}}` — looked up via the credentials store. The value is
  never returned by any API; listing credentials returns only masked
  prefixes.
- `{{env:VAR}}` — read from the FlowForge server's environment.
- Placeholders work in `webhook_url` and inside each `webhook_headers`
  value. They do not apply to the request body — the body is the tool-call
  arguments, verbatim.

The server treats non-2xx responses as errors the agent sees. If you need
partial-success semantics, return 200 with an error field inside the JSON.

## Built-in tools

Reference by name. Built-ins are protected — you can't delete them
(`flowforge_delete_tool` returns 403 on `is_builtin=True`), and you can't
override them with a same-named custom tool (409).

Use `flowforge_list_tools include_builtin:true` to see what's available.

## Credentials

Create via `flowforge_create_credential` (or the dashboard). Four types —
`api_key`, `bearer_token`, `basic_auth`, `custom` — used for UI grouping;
the value is an opaque string either way.

How to read a credential depends on the tool type:

- **Custom tools** — call `credentials.get("name")` from inside `execute()`.
  Returns the decrypted value or `None` if the credential is missing or
  inactive. Only `.get()` and `in` are exposed; the tool cannot enumerate
  names.
- **Webhook tools** — use `{{credential:name}}` placeholders inside
  `webhook_url` and `webhook_headers`. Resolved server-side before the
  request goes out.

Both paths read from the same encrypted store, scoped to the calling
tenant. FlowForge does not expose decrypted values via the credentials
API or log them. Custom tool authors must avoid returning secrets in
tool outputs or error messages after calling `credentials.get()` —
anything a tool returns flows into the agent transcript and run record.

To rotate: call `flowforge_create_credential` again with the same name. The
old encrypted value is replaced; tools pick up the new value on the next
invocation (no caching across runs).

## Human-in-the-loop approvals

Set `requires_approval=True` on the tool. Every call from an agent pauses
the run and creates an `Approval` row. Approvers act via
`flowforge_approve_tool_call` (optionally modifying the arguments) or
`flowforge_reject_tool_call` (irreversible for the current run — the
step fails with the supplied reason).

Timeouts — set `approval_timeout` like `"1h"`, `"30m"`, `"2d"`. When the
timeout fires without a decision, the approval auto-rejects.

Use approvals sparingly — every gated tool call blocks the run until a
human acts. Reserve them for high-blast-radius operations (sends email,
spends money, writes to production).

## Soft-delete semantics

DELETE on a tool sets `deleted_at = now()` and `is_active = False`. Since
`inline_executor._load_tools` filters `is_active = True`, deleted tools
stop being loaded for new runs — but runs currently executing that already
loaded the tool keep working. To resurrect, create a tool with the same
name; the server updates the existing row rather than inserting a new one.

Built-ins don't soft-delete — DELETE returns 403.

## Reviewing a new tool

Before shipping, confirm:

1. Description is LLM-friendly — what the tool does AND when to call it.
   Agents pick tools from this text.
2. `parameters` schema is tight — required fields listed, types specified,
   enums where applicable. Loose schemas produce hallucinated arguments.
3. Secrets are in `{{credential:name}}`, never inline.
4. If it's destructive (writes, sends, spends), `requires_approval=True` is
   worth considering.
5. If it's a custom tool, the code path handles errors by returning a dict
   with an `error` key rather than raising — agents reason about error
   dicts better than stack traces.

"""Example: a custom (sandboxed) FlowForge tool that uses a credential.

The string in ``CODE`` is exactly what you'd paste into the dashboard's
"Custom tool — code" editor (or send via ``flowforge_create_tool`` MCP).
The sandbox injects two globals into ``execute``:

- ``http_request(url, method=, headers=, json=, timeout=)`` — SSRF-safe
  HTTP. Use this instead of ``requests`` / ``httpx`` / ``urllib`` (those
  modules are blocked).
- ``credentials.get(name, default=None)`` — read a decrypted secret from
  the encrypted credential store, scoped to the calling tenant. Create
  the credential first via ``flowforge_create_credential`` or the
  Settings → Credentials page.

This file is documentation, not a runnable workflow — the code lives
inside FlowForge as a Tool row, not as a Python module on disk.
"""

CODE = '''
def execute(query: str) -> dict:
    """Search Tavily and return the raw response body.

    Required credential: ``tavily_api_key`` (created via the dashboard or
    ``flowforge_create_credential``). Returning a dict with an ``error``
    key — instead of raising — keeps the agent reasoning cleanly when
    the credential is missing or the upstream call fails.
    """
    api_key = credentials.get("tavily_api_key")
    if not api_key:
        return {"error": "missing credential: tavily_api_key"}

    resp = http_request(
        "https://api.tavily.com/search",
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={"query": query, "max_results": 5},
        timeout=15,
    )

    if resp["status_code"] >= 400:
        return {"error": f"tavily {resp['status_code']}", "body": resp["text"]}

    return {"status_code": resp["status_code"], "body": resp["text"]}
'''


# Example tool definition you'd send to flowforge_create_tool:
TOOL_DEFINITION = {
    "name": "tavily_search",
    "description": "Search the web via Tavily and return raw JSON results.",
    "tool_type": "custom",
    "code": CODE,
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query."},
        },
        "required": ["query"],
    },
}

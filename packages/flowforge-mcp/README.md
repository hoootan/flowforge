# flowforge-mcp-server

MCP server that exposes FlowForge workflows, agents, tasks, runs, and skills as
tools an LLM client (Claude, VS Code, etc.) can call directly.

## Running

```bash
pnpm --filter flowforge-mcp-server build
npx flowforge-mcp
```

Configuration (`FLOWFORGE_API_URL`, `FLOWFORGE_API_KEY`) is read from env. See
`src/server.ts` for the context shape.

## Tool documentation standard

LLMs pick tools and fill parameters based only on what the MCP server tells
them. Vague descriptions cause wrong-tool selection and malformed calls. Every
tool in this package must meet the rules below; `tests/tool-descriptions.test.ts`
enforces them in CI.

### 1. Description (≥ 80 characters, ≥ 2 sentences)

Structure each description as:

1. **What it does** — plain-language verb phrase. No jargon unless the jargon
   is the point (e.g., "Kanban board").
2. **When to use it** — vs sibling tools if any, or a note about scope
   ("Runs on the FlowForge server, not on your worker"). Name the sibling
   explicitly (e.g., "Use `flowforge_replay_run` to re-execute from scratch").
3. **Side effects / return shape** (optional third sentence) — destructive
   tools call this out; list tools mention ordering and pagination.

### 2. Every parameter has `.describe()`

Zod fields without `.describe()` render as bare types in the MCP schema. Always
attach a plain-language description that covers:

- What the field means in user terms.
- An example value when the format isn't obvious (IDs, expressions, dates).
- Enum values inline in the description *and* as `.enum([...])` — LLMs read the
  description more reliably than the constraint.
- Any "ignored when `other_param` is set" conditions.

### 3. Required phrasing for destructive tools

Tools whose names match `/^flowforge_(delete|archive|reject|cancel)_/` must
include **one** of these phrases in the description so LLMs understand the
stakes:

- `Irreversible`
- `cannot be undone`
- `Soft-delete` or `Soft delete`
- `preserved` (for soft-delete semantics)
- `can be restored`

### 4. Required phrasing for list tools

Tools whose names match `/^flowforge_list_/` must mention ordering so LLMs
know how results are arranged. One of: `ordered`, `order`, `sorted`,
`descending`, `ascending`, `most recent`.

### 5. Sibling tools cross-reference each other

When two tools could plausibly answer the same prompt, both descriptions name
the other:

- `flowforge_retry_run` ↔ `flowforge_replay_run`
- `flowforge_create_function` ↔ `flowforge_create_inline_function`
- `flowforge_get_run_steps` ↔ `flowforge_get_run_tool_calls`

Without this, LLMs guess and often guess wrong.

## Reference templates

These tools hit the bar today — copy their shape when adding new ones:

- `flowforge_create_tool` (`src/tools/tools.ts`) — three tool types in the
  description, placeholder syntax spelled out, every param has an example.
- `flowforge_create_inline_function` (`src/tools/functions.ts`) — explicit
  contrast with `flowforge_create_function`, rich sub-agent parameter docs.
- `flowforge_create_task` (`src/tools/tasks.ts`) — concise but fully typed,
  enum values inline in both description and schema.

## Running the lint test

```bash
cd packages/flowforge-mcp && npm test
```

The test imports every `register*Tools` function, registers them against a
capturing stub `McpServer`, and asserts each tool against the rules above.
Failures name the offending tool and the specific rule that broke.

## Adding a new tool

1. Register it in the right `src/tools/*.ts` file.
2. Write the description against the structure in §1.
3. Add `.describe()` on every parameter.
4. Add destructive/list phrasing if applicable (§3, §4).
5. Cross-reference any sibling tools in *both* directions (§5).
6. Run `npm test` locally before opening a PR.

import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { type McpContext, directFetch } from "../server.js";

export function registerToolTools(server: McpServer, ctx: McpContext): void {
  server.tool(
    "flowforge_list_tools",
    "List all AI tools registered in FlowForge, ordered by name. Tools are reusable capabilities that inline functions and agents can call — either Python sandboxes ('custom'), HTTP endpoints ('webhook'), or platform primitives ('builtin'). Use flowforge_get_tool for the full definition of a single tool.",
    {
      type: z
        .string()
        .optional()
        .describe("Filter by tool type: 'custom', 'webhook', or 'builtin'."),
      is_active: z
        .boolean()
        .optional()
        .describe("Filter by active status. Inactive tools still exist but can't be called."),
      limit: z
        .number()
        .default(20)
        .describe("Maximum number of tools to return. Server caps at 100."),
    },
    async (args) => {
      const query = ctx.client.tools.select();
      if (args.type) (query as any).eq("type", args.type);
      if (args.is_active !== undefined) query.eq("is_active", args.is_active);
      query.limit(args.limit);
      const { data, error } = await query.execute();
      if (error) {
        return {
          content: [
            { type: "text" as const, text: `Error: ${error.message}` },
          ],
          isError: true,
        };
      }
      return {
        content: [
          { type: "text" as const, text: JSON.stringify(data, null, 2) },
        ],
      };
    }
  );

  server.tool(
    "flowforge_get_tool",
    "Get the full definition of a specific AI tool by name: its parameter schema, Python code or webhook config, approval settings, and active state. Use after flowforge_list_tools to inspect a candidate before wiring it into a function.",
    {
      tool_name: z
        .string()
        .describe("The tool name from flowforge_list_tools (e.g. 'keyword_enrichment')."),
    },
    async (args) => {
      const { data, error } = await ctx.client.tools.get(args.tool_name);
      if (error) {
        return {
          content: [
            { type: "text" as const, text: `Error: ${error.message}` },
          ],
          isError: true,
        };
      }
      return {
        content: [
          { type: "text" as const, text: JSON.stringify(data, null, 2) },
        ],
      };
    }
  );

  server.tool(
    "flowforge_create_tool",
    "Create a new AI tool. Three tool types: 'custom' (Python code executed in a sandbox — must define execute(**kwargs)), 'webhook' (HTTP endpoint with {{credential:name}} and {{env:VAR}} placeholders), or 'builtin' (reference a FlowForge-provided tool by name). After creation, wire the tool into an inline function via flowforge_create_inline_function or flowforge_update_function.",
    {
      name: z
        .string()
        .describe("Unique tool name used by functions/agents to invoke it (e.g. 'summarize_text')."),
      description: z
        .string()
        .describe("Human- and LLM-readable description of what the tool does. Shown to the agent when it chooses tools."),
      parameters: z
        .record(z.unknown())
        .describe("JSON Schema describing the tool's parameters (the shape passed to execute())."),
      tool_type: z
        .enum(["custom", "webhook", "builtin"])
        .optional()
        .default("custom")
        .describe("Tool type: 'custom' (Python code), 'webhook' (HTTP), or 'builtin' (platform-provided)."),
      code: z
        .string()
        .optional()
        .describe("Python source for custom tools. Must define an execute() function taking kwargs. Ignored for webhook/builtin types."),
      webhook_url: z
        .string()
        .optional()
        .describe("URL for webhook tools. Supports {{credential:name}} and {{env:VAR}} placeholders. Ignored for custom/builtin types."),
      webhook_method: z
        .enum(["GET", "POST", "PUT", "PATCH", "DELETE"])
        .optional()
        .default("POST")
        .describe("HTTP method for webhook tools. Default POST."),
      webhook_headers: z
        .record(z.string())
        .optional()
        .describe("HTTP headers for webhook tools. Values support {{credential:name}} placeholders (e.g. 'Authorization: Bearer {{credential:openai_key}}')."),
      requires_approval: z
        .boolean()
        .optional()
        .describe("If true, each call pauses until a human approves or rejects via flowforge_approve_tool_call / flowforge_reject_tool_call."),
      approval_timeout: z
        .string()
        .optional()
        .describe("How long to wait for approval before auto-rejecting. Duration string like '1h', '30m', '2d'."),
      type: z
        .string()
        .optional()
        .describe("Deprecated alias for tool_type. Pass tool_type instead for new calls."),
    },
    async (args) => {
      const { type: _type, ...createArgs } = args;
      const body = {
        ...createArgs,
        tool_type: args.tool_type || (_type as string) || "custom",
      };
      try {
        const data = await directFetch(ctx, "POST", "/tools", body);
        return {
          content: [
            { type: "text" as const, text: JSON.stringify(data, null, 2) },
          ],
        };
      } catch (err) {
        return {
          content: [
            { type: "text" as const, text: `Error: ${(err as Error).message}` },
          ],
          isError: true,
        };
      }
    }
  );

  server.tool(
    "flowforge_update_tool",
    "Update fields on an existing AI tool — code, webhook config, approval settings, or active flag. Only provided fields are changed; omitted fields keep their current value. For creating a brand-new tool, use flowforge_create_tool; to retire a tool, set is_active=false here or call flowforge_delete_tool.",
    {
      tool_name: z
        .string()
        .describe("The tool name to update (from flowforge_list_tools)."),
      description: z
        .string()
        .optional()
        .describe("New human-readable description."),
      parameters: z
        .record(z.unknown())
        .optional()
        .describe("Replacement JSON Schema for the tool's parameters. Replaces wholesale — no deep merge."),
      tool_type: z
        .enum(["custom", "webhook", "builtin"])
        .optional()
        .describe("Change the tool type: 'custom', 'webhook', or 'builtin'."),
      code: z
        .string()
        .optional()
        .describe("Replacement Python code for custom tools."),
      webhook_url: z
        .string()
        .optional()
        .describe("New webhook URL for webhook tools."),
      webhook_method: z
        .enum(["GET", "POST", "PUT", "PATCH", "DELETE"])
        .optional()
        .describe("New HTTP method for webhook tools."),
      webhook_headers: z
        .record(z.string())
        .optional()
        .describe("Replacement HTTP headers for webhook tools. Replaces wholesale."),
      requires_approval: z
        .boolean()
        .optional()
        .describe("Toggle whether each call needs human approval."),
      approval_timeout: z
        .string()
        .optional()
        .describe("New approval timeout duration (e.g. '1h')."),
      is_active: z
        .boolean()
        .optional()
        .describe("Set active/inactive. Inactive tools still exist but can't be called."),
      type: z
        .string()
        .optional()
        .describe("Deprecated alias for tool_type. Pass tool_type instead for new calls."),
    },
    async (args) => {
      const { tool_name, type: _type, ...updates } = args;
      if (_type && !updates.tool_type) {
        (updates as Record<string, unknown>).tool_type = _type;
      }
      try {
        const data = await directFetch(ctx, "PATCH", `/tools/${encodeURIComponent(tool_name)}`, updates);
        return {
          content: [
            { type: "text" as const, text: JSON.stringify(data, null, 2) },
          ],
        };
      } catch (err) {
        return {
          content: [
            { type: "text" as const, text: `Error: ${(err as Error).message}` },
          ],
          isError: true,
        };
      }
    }
  );

  server.tool(
    "flowforge_delete_tool",
    "Delete an AI tool by name. Irreversible — the tool is removed from the registry. Any function still referencing this tool will fail on its next invocation, so remove the reference first (via flowforge_update_function) or disable the tool with flowforge_update_tool { is_active: false } if you want to preserve the row.",
    {
      tool_name: z
        .string()
        .describe("The tool name to delete (from flowforge_list_tools)."),
    },
    async (args) => {
      const { data, error } = await ctx.client.tools.delete(args.tool_name);
      if (error) {
        return {
          content: [
            { type: "text" as const, text: `Error: ${error.message}` },
          ],
          isError: true,
        };
      }
      return {
        content: [
          { type: "text" as const, text: JSON.stringify(data, null, 2) },
        ],
      };
    }
  );
}

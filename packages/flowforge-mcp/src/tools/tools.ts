import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { type McpContext, directFetch } from "../server.js";

export function registerToolTools(server: McpServer, ctx: McpContext): void {
  server.tool(
    "flowforge_list_tools",
    "List all AI tools registered in FlowForge.",
    {
      type: z.string().optional().describe("Filter by tool type"),
      is_active: z.boolean().optional().describe("Filter by active status"),
      limit: z
        .number()
        .default(20)
        .describe("Maximum number of tools to return"),
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
    "Get details of a specific AI tool by its name.",
    {
      tool_name: z.string().describe("The tool name"),
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
    "Create a new AI tool in FlowForge. Supports three tool types: 'custom' (Python code executed in sandbox), 'webhook' (HTTP endpoint with credential placeholders like {{credential:name}}), and 'builtin'.",
    {
      name: z.string().describe("Tool name (unique identifier)"),
      description: z.string().describe("Human-readable description of what the tool does"),
      parameters: z
        .record(z.unknown())
        .describe("JSON Schema describing the tool's parameters"),
      tool_type: z
        .enum(["custom", "webhook", "builtin"])
        .optional()
        .default("custom")
        .describe("Tool type: 'custom' (code), 'webhook' (HTTP config), or 'builtin'"),
      code: z
        .string()
        .optional()
        .describe("Python code for custom tools. Must define an execute() function."),
      webhook_url: z
        .string()
        .optional()
        .describe("URL for webhook tools. Supports {{credential:name}} and {{env:VAR}} placeholders."),
      webhook_method: z
        .enum(["GET", "POST", "PUT", "PATCH", "DELETE"])
        .optional()
        .default("POST")
        .describe("HTTP method for webhook tools"),
      webhook_headers: z
        .record(z.string())
        .optional()
        .describe("HTTP headers for webhook tools. Supports {{credential:name}} placeholders."),
      requires_approval: z
        .boolean()
        .optional()
        .describe("Whether this tool requires human approval before execution"),
      approval_timeout: z
        .string()
        .optional()
        .describe("Timeout for approval (e.g., '1h', '30m')"),
      type: z
        .string()
        .optional()
        .describe("Deprecated: use tool_type instead"),
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
    "Update an existing AI tool.",
    {
      tool_name: z.string().describe("The tool name to update"),
      description: z.string().optional().describe("New description"),
      parameters: z
        .record(z.unknown())
        .optional()
        .describe("Updated parameter schema"),
      tool_type: z
        .enum(["custom", "webhook", "builtin"])
        .optional()
        .describe("Updated tool type"),
      code: z.string().optional().describe("Updated Python code"),
      webhook_url: z.string().optional().describe("Updated webhook URL"),
      webhook_method: z
        .enum(["GET", "POST", "PUT", "PATCH", "DELETE"])
        .optional()
        .describe("Updated webhook HTTP method"),
      webhook_headers: z
        .record(z.string())
        .optional()
        .describe("Updated webhook headers"),
      requires_approval: z.boolean().optional().describe("Updated approval requirement"),
      approval_timeout: z.string().optional().describe("Updated approval timeout"),
      is_active: z.boolean().optional().describe("Set active status"),
      type: z.string().optional().describe("Deprecated: use tool_type instead"),
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
    "Delete an AI tool by its name.",
    {
      tool_name: z.string().describe("The tool name to delete"),
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

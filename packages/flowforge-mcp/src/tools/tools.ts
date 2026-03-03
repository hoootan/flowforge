import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import type { McpContext } from "../server.js";

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
      if (args.type) query.eq("type", args.type);
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
    "Create a new AI tool in FlowForge.",
    {
      name: z.string().describe("Tool name (unique identifier)"),
      description: z.string().describe("Human-readable description of what the tool does"),
      parameters: z
        .record(z.unknown())
        .describe("JSON Schema describing the tool's parameters"),
      type: z
        .string()
        .optional()
        .describe("Tool type classification"),
    },
    async (args) => {
      const { data, error } = await ctx.client.tools.create({
        name: args.name,
        description: args.description,
        parameters: args.parameters,
        type: args.type,
      });
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
    "flowforge_update_tool",
    "Update an existing AI tool.",
    {
      tool_name: z.string().describe("The tool name to update"),
      description: z.string().optional().describe("New description"),
      parameters: z
        .record(z.unknown())
        .optional()
        .describe("Updated parameter schema"),
      type: z.string().optional().describe("Updated tool type"),
    },
    async (args) => {
      const { tool_name, ...updates } = args;
      const { data, error } = await ctx.client.tools.update(
        tool_name,
        updates
      );
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

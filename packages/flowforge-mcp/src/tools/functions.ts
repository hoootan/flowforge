import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import type { McpContext } from "../server.js";

export function registerFunctionTools(
  server: McpServer,
  ctx: McpContext
): void {
  server.tool(
    "flowforge_list_functions",
    "List all registered workflow functions. Optionally filter by trigger type or active status.",
    {
      trigger_type: z
        .string()
        .optional()
        .describe("Filter by trigger type (e.g., 'event', 'cron')"),
      is_active: z.boolean().optional().describe("Filter by active status"),
      limit: z
        .number()
        .default(20)
        .describe("Maximum number of functions to return"),
    },
    async (args) => {
      const query = ctx.client.functions.select();
      if (args.trigger_type)
        query.eq("trigger_type", args.trigger_type as "event" | "cron");
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
    "flowforge_get_function",
    "Get details of a specific workflow function by its ID.",
    {
      function_id: z.string().describe("The function ID"),
    },
    async (args) => {
      const { data, error } = await ctx.client.functions.get(args.function_id);
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
    "flowforge_create_function",
    "Create a new workflow function.",
    {
      name: z.string().describe("Function name"),
      trigger_type: z
        .string()
        .describe("Trigger type: 'event', 'cron', or 'webhook'"),
      trigger_value: z
        .string()
        .describe("Trigger value (e.g., event name 'order/created' or cron expression)"),
      endpoint_url: z.string().describe("URL that handles function execution"),
      config: z
        .record(z.unknown())
        .optional()
        .describe("Function configuration (concurrency, retries, etc.)"),
    },
    async (args) => {
      const { data, error } = await ctx.client.functions.create({
        name: args.name,
        trigger_type: args.trigger_type as "event" | "cron" | "webhook",
        trigger_value: args.trigger_value,
        endpoint_url: args.endpoint_url,
        config: args.config,
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
    "flowforge_update_function",
    "Update an existing workflow function.",
    {
      function_id: z.string().describe("The function ID to update"),
      name: z.string().optional().describe("New function name"),
      trigger_value: z.string().optional().describe("New trigger value"),
      endpoint_url: z.string().optional().describe("New endpoint URL"),
      config: z
        .record(z.unknown())
        .optional()
        .describe("Updated configuration"),
      is_active: z.boolean().optional().describe("Set active status"),
    },
    async (args) => {
      const { function_id, ...updates } = args;
      const { data, error } = await ctx.client.functions.update(
        function_id,
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
    "flowforge_delete_function",
    "Delete a workflow function by its ID.",
    {
      function_id: z.string().describe("The function ID to delete"),
    },
    async (args) => {
      const { data, error } = await ctx.client.functions.delete(
        args.function_id
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
}

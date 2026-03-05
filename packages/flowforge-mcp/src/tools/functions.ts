import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import crypto from "node:crypto";
import { type McpContext, directFetch } from "../server.js";

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
    "Create a new workflow function (worker mode). The function runs on your own server at endpoint_url. For inline/serverless functions (AI agent), use flowforge_create_inline_function instead.",
    {
      name: z.string().describe("Function name"),
      trigger_type: z
        .enum(["event", "cron", "webhook"])
        .describe("Trigger type"),
      trigger_value: z
        .string()
        .describe("Trigger value (e.g., event name 'order/created' or cron expression '0 9 * * *')"),
      trigger_expression: z
        .string()
        .optional()
        .describe("Optional filter expression for event triggers (e.g., 'event.data.amount > 100')"),
      endpoint_url: z.string().describe("URL that handles function execution"),
      config: z
        .record(z.unknown())
        .optional()
        .describe("Function configuration (retries, timeout, concurrency, etc.)"),
    },
    async (args) => {
      const body = {
        id: crypto.randomUUID(),
        name: args.name,
        trigger: {
          type: args.trigger_type,
          value: args.trigger_value,
          expression: args.trigger_expression,
        },
        endpoint_url: args.endpoint_url,
        config: args.config || {},
      };
      try {
        const data = await directFetch(ctx, "POST", "/functions", body);
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
    "flowforge_create_inline_function",
    "Create an inline/serverless AI agent function. The function runs on the FlowForge server using an LLM with tools — no endpoint_url needed.",
    {
      name: z.string().describe("Function name (e.g., 'Create Social Post')"),
      trigger_type: z
        .enum(["event", "cron", "webhook"])
        .describe("Trigger type"),
      trigger_value: z
        .string()
        .describe("Trigger value (e.g., event name 'content/requested' or cron expression)"),
      trigger_expression: z
        .string()
        .optional()
        .describe("Optional filter expression for event triggers"),
      system_prompt: z
        .string()
        .describe("System prompt for the AI agent (defines its persona and instructions)"),
      tools: z
        .array(z.string())
        .describe("List of tool names the agent can use (must exist in tools table)"),
      agent_config: z
        .object({
          model: z
            .string()
            .optional()
            .default("claude-sonnet-4-6")
            .describe("AI model to use"),
          max_iterations: z
            .number()
            .optional()
            .default(30)
            .describe("Maximum agent loop iterations (1-100)"),
          max_tool_calls: z
            .number()
            .optional()
            .default(50)
            .describe("Maximum tool calls per run (1-200)"),
        })
        .optional()
        .describe("Agent configuration (model, iteration limits)"),
      config: z
        .record(z.unknown())
        .optional()
        .describe("Function configuration (retries, timeout, etc.)"),
    },
    async (args) => {
      const body = {
        id: crypto.randomUUID(),
        name: args.name,
        trigger: {
          type: args.trigger_type,
          value: args.trigger_value,
          expression: args.trigger_expression,
        },
        system_prompt: args.system_prompt,
        tools: args.tools,
        agent_config: args.agent_config || {},
        config: args.config || {},
      };
      try {
        const data = await directFetch(ctx, "POST", "/functions/inline", body);
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
    "flowforge_update_function",
    "Update an existing workflow function (works for both worker and inline functions).",
    {
      function_id: z.string().describe("The function ID to update"),
      name: z.string().optional().describe("New function name"),
      endpoint_url: z.string().optional().describe("New endpoint URL (worker functions only)"),
      system_prompt: z.string().optional().describe("Updated system prompt (inline functions only)"),
      tools: z
        .array(z.string())
        .optional()
        .describe("Updated tool list (inline functions only)"),
      agent_config: z
        .object({
          model: z.string().optional().describe("AI model to use"),
          max_iterations: z.number().optional().describe("Maximum agent loop iterations"),
          max_tool_calls: z.number().optional().describe("Maximum tool calls per run"),
        })
        .optional()
        .describe("Updated agent config (inline functions only)"),
      config: z
        .record(z.unknown())
        .optional()
        .describe("Updated function configuration"),
      is_active: z.boolean().optional().describe("Set active status"),
    },
    async (args) => {
      const { function_id, ...updates } = args;
      try {
        const data = await directFetch(ctx, "PATCH", `/functions/${encodeURIComponent(function_id)}`, updates);
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

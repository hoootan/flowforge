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
    "List registered workflow functions, ordered by creation time (newest first). Soft-deleted functions are excluded — their run history is preserved but they do not appear here. Use flowforge_get_function for the full definition of a single function.",
    {
      trigger_type: z
        .enum(["event", "cron", "webhook"])
        .optional()
        .describe("Filter by trigger kind: 'event' (most common), 'cron' (scheduled), or 'webhook'."),
      is_active: z
        .boolean()
        .optional()
        .describe("Filter by active status. Inactive functions still exist but don't match new events."),
      limit: z
        .number()
        .default(20)
        .describe("Maximum number of functions to return. Server caps at 100."),
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
    "Get the full record of a single workflow function — trigger config, tools, agent config, and active state. Use after flowforge_list_functions to inspect a specific function, or before flowforge_update_function so you know what fields currently exist.",
    {
      function_id: z
        .string()
        .describe("The user-defined function_id (e.g. 'process-order') or its UUID. Visible in flowforge_list_functions."),
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
    "Create a worker-mode workflow function whose code runs on your own server at endpoint_url. FlowForge calls the endpoint when the trigger fires and tracks durable execution. For serverless/agent functions that run on the FlowForge server itself (driven by an LLM + tools), use flowforge_create_inline_function instead.",
    {
      name: z
        .string()
        .describe("Function name (e.g. 'Process Order'). Becomes the display label."),
      trigger_type: z
        .enum(["event", "cron", "webhook"])
        .describe("Trigger kind: 'event' (fires on matching event), 'cron' (scheduled), or 'webhook' (HTTP invoke)."),
      trigger_value: z
        .string()
        .describe("Event name (e.g. 'order/created'), cron expression (e.g. '0 9 * * *'), or webhook path, depending on trigger_type."),
      trigger_expression: z
        .string()
        .optional()
        .describe("Optional filter expression for event triggers, e.g. 'event.data.amount > 100'. Ignored for cron/webhook."),
      endpoint_url: z
        .string()
        .describe("URL on your server that handles execution. Must accept POST with the run payload."),
      config: z
        .record(z.unknown())
        .optional()
        .describe("Execution config: retries, timeout, concurrency, rate_limit, etc. Omit to use defaults."),
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
    "Create an inline/serverless AI agent function that runs on the FlowForge server — an LLM drives execution using the listed tools, no endpoint_url is needed. For code you run on your own server instead, use flowforge_create_function. Tools referenced in the tools array must already exist (see flowforge_list_tools).",
    {
      id: z
        .string()
        .optional()
        .describe("Optional stable function_id like 'create-post'. Auto-generated if omitted."),
      name: z
        .string()
        .describe("Display name (e.g. 'Create Social Post')."),
      trigger_type: z
        .enum(["event", "cron", "webhook"])
        .describe("Trigger kind: 'event', 'cron', or 'webhook'."),
      trigger_value: z
        .string()
        .describe("Event name, cron expression, or webhook path depending on trigger_type."),
      trigger_expression: z
        .string()
        .optional()
        .describe("Optional filter expression for event triggers (e.g. 'event.data.priority == \"high\"')."),
      system_prompt: z
        .string()
        .describe("System prompt for the AI agent — defines persona, instructions, and when to call which tools."),
      tools: z
        .array(z.string())
        .describe("Names of tools the agent may call. Each must already exist (see flowforge_list_tools)."),
      agent_config: z
        .object({
          model: z
            .string()
            .optional()
            .default("claude-sonnet-4-6")
            .describe("AI model id (e.g. 'claude-sonnet-4-6', 'gpt-4o'). Default claude-sonnet-4-6."),
          max_iterations: z
            .number()
            .optional()
            .default(30)
            .describe("Maximum agent loop iterations (1-100). Guards runaway loops."),
          max_tool_calls: z
            .number()
            .optional()
            .default(50)
            .describe("Maximum tool calls per run (1-200)."),
          sub_agents: z
            .record(
              z.object({
                system_prompt: z
                  .string()
                  .describe("System prompt defining the sub-agent's focused task."),
                model: z
                  .string()
                  .optional()
                  .describe("AI model for the sub-agent. Inherits parent's model if omitted."),
                tools: z
                  .array(z.string())
                  .optional()
                  .describe("Tool names the sub-agent can call. Must exist in the tool registry."),
                max_iterations: z
                  .number()
                  .optional()
                  .describe("Iteration cap for the sub-agent."),
                max_tool_calls: z
                  .number()
                  .optional()
                  .describe("Tool-call cap for the sub-agent."),
                description: z
                  .string()
                  .optional()
                  .describe("Shown to the parent agent so it knows when to delegate to this sub-agent."),
              })
            )
            .optional()
            .describe("Sub-agent definitions keyed by name. Each becomes a tool the parent agent can call to delegate a focused task."),
        })
        .optional()
        .describe("Agent configuration (model, iteration limits, sub-agents). Omit to accept defaults."),
      config: z
        .record(z.unknown())
        .optional()
        .describe("Execution config: retries, timeout, concurrency, etc. Omit to use defaults."),
    },
    async (args) => {
      const body = {
        id: args.id || `fn-${crypto.randomUUID().slice(0, 8)}`,
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
    "Update fields on an existing workflow function. Works for both worker and inline functions — only provided fields change. Note: worker-only fields (endpoint_url) are ignored on inline functions and vice versa (system_prompt, tools, agent_config are ignored on worker functions). For creating a new function, use flowforge_create_function or flowforge_create_inline_function.",
    {
      function_id: z
        .string()
        .describe("The function_id or UUID to update (from flowforge_list_functions)."),
      name: z
        .string()
        .optional()
        .describe("New display name."),
      endpoint_url: z
        .string()
        .optional()
        .describe("New endpoint URL. Worker functions only — ignored on inline functions."),
      system_prompt: z
        .string()
        .optional()
        .describe("Replacement system prompt. Inline functions only — ignored on worker functions."),
      tools: z
        .array(z.string())
        .optional()
        .describe("Replacement list of tool names. Inline functions only. Replaces wholesale — no merge."),
      agent_config: z
        .object({
          model: z
            .string()
            .optional()
            .describe("AI model id."),
          max_iterations: z
            .number()
            .optional()
            .describe("Maximum agent loop iterations."),
          max_tool_calls: z
            .number()
            .optional()
            .describe("Maximum tool calls per run."),
          sub_agents: z
            .record(
              z.object({
                system_prompt: z
                  .string()
                  .describe("System prompt for the sub-agent."),
                model: z.string().optional().describe("AI model for the sub-agent."),
                tools: z.array(z.string()).optional().describe("Tool names the sub-agent can call."),
                max_iterations: z.number().optional().describe("Iteration cap for the sub-agent."),
                max_tool_calls: z.number().optional().describe("Tool-call cap for the sub-agent."),
                description: z.string().optional().describe("Shown to the parent agent for delegation decisions."),
              })
            )
            .optional()
            .describe("Sub-agent definitions keyed by name."),
        })
        .optional()
        .describe("Replacement agent config. Inline functions only."),
      config: z
        .record(z.unknown())
        .optional()
        .describe("Replacement execution config (retries, timeout, etc). Replaces wholesale."),
      is_active: z
        .boolean()
        .optional()
        .describe("Set active/inactive. Inactive functions don't match new events."),
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
    "Soft-delete a workflow function. The row is marked deleted and hidden from flowforge_list_functions, existing runs are preserved so run history still resolves the function name, and the function stops matching new events. Re-registering the same function_id via flowforge_create_function or flowforge_create_inline_function restores the row.",
    {
      function_id: z
        .string()
        .describe("The function_id or UUID to soft-delete (from flowforge_list_functions)."),
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

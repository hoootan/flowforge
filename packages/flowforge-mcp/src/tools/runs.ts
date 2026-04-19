import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import type { McpContext } from "../server.js";
import { directFetch } from "../server.js";

export function registerRunTools(server: McpServer, ctx: McpContext): void {
  server.tool(
    "flowforge_list_runs",
    "List workflow runs, ordered by creation time (most recent first). Use to find recent executions of a function, triage failures, or verify that a just-sent event actually triggered a run. For details of a single run, call flowforge_get_run with the id from this list.",
    {
      function_id: z
        .string()
        .optional()
        .describe("Filter to runs of one function (the user-defined function_id like 'process-order', or the UUID)."),
      status: z
        .enum(["pending", "running", "completed", "failed", "cancelled", "paused"])
        .optional()
        .describe("Filter by run status. Common picks: 'failed' (triage), 'running' (in-flight), 'completed'."),
      limit: z
        .number()
        .default(20)
        .describe("Maximum number of runs to return. Server caps at 100."),
    },
    async (args) => {
      const query = ctx.client.runs.select();
      if (args.function_id) query.eq("function_id", args.function_id);
      if (args.status)
        query.eq(
          "status",
          args.status as
            | "pending"
            | "running"
            | "completed"
            | "failed"
            | "cancelled"
            | "paused"
        );
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
    "flowforge_get_run",
    "Get the full record of a single workflow run: status, timing, input event, and summary metadata. Use after flowforge_list_runs to drill into a specific run. For the step-by-step execution trace, use flowforge_get_run_steps; for tool calls specifically, use flowforge_get_run_tool_calls.",
    {
      run_id: z
        .string()
        .describe("The run UUID returned from flowforge_list_runs or flowforge_send_event."),
    },
    async (args) => {
      const { data, error } = await ctx.client.runs.get(args.run_id);
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
    "flowforge_cancel_run",
    "Cancel a run that is currently pending or running. Irreversible — the run stops where it is and ends in 'cancelled' state. Use this to abort stuck or misfiring runs. Has no effect on runs that already finished (completed/failed).",
    {
      run_id: z
        .string()
        .describe("The run UUID to cancel. Must be in status 'pending' or 'running'."),
    },
    async (args) => {
      const { data, error } = await ctx.client.runs.cancel(args.run_id);
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
    "flowforge_retry_run",
    "Retry a failed run, resuming from the step that failed. Completed steps are memoized and NOT re-executed — the run picks up where it left off. Use this after a transient failure (network blip, rate limit) where you want to preserve prior progress. For a clean re-execution that runs every step from scratch (e.g. after fixing the function's code), use flowforge_replay_run instead.",
    {
      run_id: z
        .string()
        .describe("The run UUID to retry. Must be in status 'failed'."),
    },
    async (args) => {
      try {
        const result = await directFetch(
          ctx,
          "POST",
          `/runs/${args.run_id}/retry`
        );
        return {
          content: [
            { type: "text" as const, text: JSON.stringify(result, null, 2) },
          ],
        };
      } catch (err) {
        return {
          content: [
            {
              type: "text" as const,
              text: `Error: ${err instanceof Error ? err.message : String(err)}`,
            },
          ],
          isError: true,
        };
      }
    }
  );

  server.tool(
    "flowforge_replay_run",
    "Re-run a workflow from the very beginning with the same input event, creating a brand-new run record. All steps execute again — prior step results are discarded. Use this to test function changes against historical input, or to reproduce a completed run. For resuming a failure without redoing completed work, use flowforge_retry_run instead.",
    {
      run_id: z
        .string()
        .describe("The run UUID to replay. Works on both completed and failed runs; the new run gets a fresh UUID."),
    },
    async (args) => {
      const { data, error } = await ctx.client.runs.replay(args.run_id);
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
    "flowforge_get_run_steps",
    "Get the ordered list of durable steps executed by a run, with inputs, outputs, and timing per step. Use this to trace what a run did and why it failed at a specific point. For the narrower view of just tool calls (with approval state and arguments), use flowforge_get_run_tool_calls.",
    {
      run_id: z
        .string()
        .describe("The run UUID whose steps to fetch."),
    },
    async (args) => {
      try {
        const result = await directFetch(
          ctx,
          "GET",
          `/runs/${args.run_id}/steps`
        );
        return {
          content: [
            { type: "text" as const, text: JSON.stringify(result, null, 2) },
          ],
        };
      } catch (err) {
        return {
          content: [
            {
              type: "text" as const,
              text: `Error: ${err instanceof Error ? err.message : String(err)}`,
            },
          ],
          isError: true,
        };
      }
    }
  );

  server.tool(
    "flowforge_get_run_tool_calls",
    "Get just the tool-call events from a run — useful for auditing what an agent actually called and with which arguments. For the full step-by-step trace including sleeps, waits, and sub-function invocations, use flowforge_get_run_steps.",
    {
      run_id: z
        .string()
        .describe("The run UUID whose tool calls to fetch."),
    },
    async (args) => {
      try {
        const result = await directFetch(
          ctx,
          "GET",
          `/runs/${args.run_id}/tool-calls`
        );
        return {
          content: [
            { type: "text" as const, text: JSON.stringify(result, null, 2) },
          ],
        };
      } catch (err) {
        return {
          content: [
            {
              type: "text" as const,
              text: `Error: ${err instanceof Error ? err.message : String(err)}`,
            },
          ],
          isError: true,
        };
      }
    }
  );
}

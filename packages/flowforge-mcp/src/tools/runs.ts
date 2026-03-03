import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import type { McpContext } from "../server.js";
import { directFetch } from "../server.js";

export function registerRunTools(server: McpServer, ctx: McpContext): void {
  server.tool(
    "flowforge_list_runs",
    "List workflow runs. Filter by function_id or status.",
    {
      function_id: z.string().optional().describe("Filter by function ID"),
      status: z
        .string()
        .optional()
        .describe("Filter by status (pending, running, completed, failed, cancelled, paused)"),
      limit: z.number().default(20).describe("Maximum number of runs to return"),
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
    "Get details of a specific workflow run, including its steps.",
    {
      run_id: z.string().describe("The run ID"),
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
    "Cancel a running or pending workflow run.",
    {
      run_id: z.string().describe("The run ID to cancel"),
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
    "Retry a failed workflow run.",
    {
      run_id: z.string().describe("The run ID to retry"),
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
    "Replay a completed or failed run from the beginning.",
    {
      run_id: z.string().describe("The run ID to replay"),
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
    "Get the steps for a specific workflow run.",
    {
      run_id: z.string().describe("The run ID"),
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
    "Get the tool calls made during a specific workflow run.",
    {
      run_id: z.string().describe("The run ID"),
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

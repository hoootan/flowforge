import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import type { McpContext } from "../server.js";
import { directFetch } from "../server.js";

export function registerCommentTools(server: McpServer, ctx: McpContext): void {
  server.tool(
    "flowforge_list_comments",
    "List comments on a task or run. Shows the unified activity timeline with user and agent authors.",
    {
      task_id: z.string().optional().describe("List comments for this task UUID"),
      run_id: z.string().optional().describe("List comments for this run UUID"),
      limit: z.number().default(50).describe("Max results"),
    },
    async (args) => {
      try {
        if (!args.task_id && !args.run_id) {
          return { content: [{ type: "text" as const, text: "Error: Provide either task_id or run_id" }], isError: true };
        }
        const params: Record<string, string> = {};
        if (args.task_id) params.task_id = args.task_id;
        if (args.run_id) params.run_id = args.run_id;
        params.limit = String(args.limit);
        const qs = new URLSearchParams(params).toString();
        const data = await directFetch(ctx, "GET", `/comments?${qs}`) as { comments: unknown[]; total: number };
        return {
          content: [{ type: "text" as const, text: JSON.stringify({ items: data.comments, total: data.total }, null, 2) }],
        };
      } catch (e: unknown) {
        return { content: [{ type: "text" as const, text: `Error: ${(e as Error).message}` }], isError: true };
      }
    }
  );

  server.tool(
    "flowforge_add_comment",
    "Add a comment to a task or run. Supports agent authors for the unified activity timeline.",
    {
      task_id: z.string().optional().describe("Comment on this task UUID"),
      run_id: z.string().optional().describe("Comment on this run UUID"),
      content: z.string().describe("Comment text (markdown supported)"),
      author_agent_id: z.string().optional().describe("Agent UUID if commenting as an agent"),
      author_user_id: z.string().optional().describe("User UUID if commenting as a user"),
    },
    async (args) => {
      try {
        if (!args.task_id && !args.run_id) {
          return { content: [{ type: "text" as const, text: "Error: Provide either task_id or run_id" }], isError: true };
        }
        const data = await directFetch(ctx, "POST", "/comments", args);
        return { content: [{ type: "text" as const, text: JSON.stringify(data, null, 2) }] };
      } catch (e: unknown) {
        return { content: [{ type: "text" as const, text: `Error: ${(e as Error).message}` }], isError: true };
      }
    }
  );
}

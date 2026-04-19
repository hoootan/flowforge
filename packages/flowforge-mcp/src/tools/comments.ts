import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import type { McpContext } from "../server.js";
import { directFetch } from "../server.js";

export function registerCommentTools(server: McpServer, ctx: McpContext): void {
  server.tool(
    "flowforge_list_comments",
    "List comments on a task or run, ordered by post time (oldest first). Comments form a unified activity timeline mixing human and agent authors, with @mentions and emoji reactions. Supply exactly one of task_id or run_id. To add a comment, use flowforge_add_comment.",
    {
      task_id: z
        .string()
        .optional()
        .describe("Task UUID to list comments on. Mutually exclusive with run_id."),
      run_id: z
        .string()
        .optional()
        .describe("Run UUID to list comments on. Mutually exclusive with task_id."),
      limit: z
        .number()
        .default(50)
        .describe("Maximum number of comments to return. Server caps at 200."),
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
    "Post a new comment to a task or run. Supports both human and agent authors, markdown content, and @mentions. Supply exactly one of task_id or run_id, and exactly one of author_agent_id or author_user_id. For reading existing comments, use flowforge_list_comments.",
    {
      task_id: z
        .string()
        .optional()
        .describe("Task UUID to comment on. Mutually exclusive with run_id."),
      run_id: z
        .string()
        .optional()
        .describe("Run UUID to comment on. Mutually exclusive with task_id."),
      content: z
        .string()
        .describe("Comment body. Markdown supported. @mentions of agents and users are parsed and notified."),
      author_agent_id: z
        .string()
        .optional()
        .describe("Agent UUID if posting as an agent. Mutually exclusive with author_user_id."),
      author_user_id: z
        .string()
        .optional()
        .describe("User UUID if posting as a human. Mutually exclusive with author_agent_id."),
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

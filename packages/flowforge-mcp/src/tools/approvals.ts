import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import type { McpContext } from "../server.js";

export function registerApprovalTools(
  server: McpServer,
  ctx: McpContext
): void {
  server.tool(
    "flowforge_list_approvals",
    "List pending and resolved human-in-the-loop approvals.",
    {
      status: z
        .string()
        .optional()
        .describe("Filter by status (pending, approved, rejected)"),
      run_id: z.string().optional().describe("Filter by run ID"),
      limit: z
        .number()
        .default(20)
        .describe("Maximum number of approvals to return"),
    },
    async (args) => {
      const query = ctx.client.approvals.select();
      if (args.status)
        query.eq(
          "status",
          args.status as "pending" | "approved" | "rejected"
        );
      if (args.run_id) (query as any).eq("run_id", args.run_id);
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
    "flowforge_approve_tool_call",
    "Approve a pending tool call in a human-in-the-loop workflow.",
    {
      approval_id: z.string().describe("The approval ID"),
      modified_arguments: z
        .record(z.unknown())
        .optional()
        .describe("Optionally modify the tool call arguments before approval"),
    },
    async (args) => {
      const { data, error } = await ctx.client.approvals.approve(
        args.approval_id,
        args.modified_arguments
          ? { modifiedArguments: args.modified_arguments }
          : undefined
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
    "flowforge_reject_tool_call",
    "Reject a pending tool call in a human-in-the-loop workflow.",
    {
      approval_id: z.string().describe("The approval ID"),
      reason: z.string().describe("Reason for rejecting the tool call"),
    },
    async (args) => {
      const { data, error } = await ctx.client.approvals.reject(
        args.approval_id,
        args.reason
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

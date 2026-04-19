import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import type { McpContext } from "../server.js";

export function registerApprovalTools(
  server: McpServer,
  ctx: McpContext
): void {
  server.tool(
    "flowforge_list_approvals",
    "List human-in-the-loop tool-call approvals, ordered by creation time (most recent first). An approval is raised whenever an agent tries to call a tool whose requires_approval flag is true; the run pauses until someone approves or rejects. Use flowforge_approve_tool_call or flowforge_reject_tool_call to resolve pending items.",
    {
      status: z
        .enum(["pending", "approved", "rejected"])
        .optional()
        .describe("Filter by approval status: 'pending' (awaiting decision), 'approved', or 'rejected'."),
      run_id: z
        .string()
        .optional()
        .describe("Filter to approvals belonging to one run (the run UUID from flowforge_list_runs)."),
      limit: z
        .number()
        .default(20)
        .describe("Maximum number of approvals to return. Server caps at 100."),
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
    "Approve a pending tool-call approval. The paused run resumes and the tool is invoked, optionally with modified arguments. To deny the call instead (which fails the run's current step), use flowforge_reject_tool_call. Only works on approvals in 'pending' status.",
    {
      approval_id: z
        .string()
        .describe("The approval UUID (from flowforge_list_approvals with status='pending')."),
      modified_arguments: z
        .record(z.unknown())
        .optional()
        .describe("Optional replacement for the tool call's arguments. Omit to approve with the arguments the agent proposed."),
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
    "Reject a pending tool-call approval. Irreversible for the current run — the run's step fails with the supplied reason and moves on according to its retry policy. To allow the call through instead (with or without argument changes), use flowforge_approve_tool_call.",
    {
      approval_id: z
        .string()
        .describe("The approval UUID to reject (from flowforge_list_approvals with status='pending')."),
      reason: z
        .string()
        .describe("Rejection reason recorded on the run's audit trail and shown to the agent."),
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

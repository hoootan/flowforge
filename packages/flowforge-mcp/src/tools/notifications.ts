import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import type { McpContext } from "../server.js";
import { directFetch } from "../server.js";

export function registerNotificationTools(server: McpServer, ctx: McpContext): void {
  server.tool(
    "flowforge_list_notifications",
    "List notifications for the current user — approvals, task assignments, mentions, agent blockers, run failures.",
    {
      is_read: z.boolean().optional().describe("Filter by read/unread"),
      limit: z.number().default(20).describe("Max results"),
    },
    async (args) => {
      try {
        const params: Record<string, string> = {};
        if (args.is_read !== undefined) params.is_read = String(args.is_read);
        params.limit = String(args.limit);
        const qs = new URLSearchParams(params).toString();
        const data = await directFetch(ctx, "GET", `/notifications?${qs}`) as { notifications: unknown[]; total: number; unread_count: number };
        return {
          content: [{ type: "text" as const, text: JSON.stringify({ items: data.notifications, total: data.total, unread_count: data.unread_count }, null, 2) }],
        };
      } catch (e: unknown) {
        return { content: [{ type: "text" as const, text: `Error: ${(e as Error).message}` }], isError: true };
      }
    }
  );

  server.tool(
    "flowforge_mark_notifications_read",
    "Mark notifications as read — either a single notification or all at once.",
    {
      notification_id: z.string().optional().describe("Mark this specific notification as read. Omit to mark ALL as read."),
    },
    async (args) => {
      try {
        if (args.notification_id) {
          await directFetch(ctx, "POST", `/notifications/${args.notification_id}/read`);
          return { content: [{ type: "text" as const, text: `Notification ${args.notification_id} marked as read.` }] };
        } else {
          await directFetch(ctx, "POST", "/notifications/read-all");
          return { content: [{ type: "text" as const, text: "All notifications marked as read." }] };
        }
      } catch (e: unknown) {
        return { content: [{ type: "text" as const, text: `Error: ${(e as Error).message}` }], isError: true };
      }
    }
  );
}

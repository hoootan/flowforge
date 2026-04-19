import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import type { McpContext } from "../server.js";
import { directFetch } from "../server.js";

export function registerNotificationTools(server: McpServer, ctx: McpContext): void {
  server.tool(
    "flowforge_list_notifications",
    "List notifications for the current user, ordered by creation time (most recent first). Notifications cover approvals (pending tool calls), task assignments, @mentions, agent blockers, and run failures — the inbox that tells you what needs attention. Response includes unread_count. Mark items read with flowforge_mark_notifications_read.",
    {
      is_read: z
        .boolean()
        .optional()
        .describe("Filter by read/unread. Pass false to see only unread notifications (the typical triage view)."),
      limit: z
        .number()
        .default(20)
        .describe("Maximum number of notifications to return. Server caps at 100."),
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
    "Mark notifications as read — either one specific notification (pass notification_id) or every currently-unread notification (omit notification_id). Use after triaging flowforge_list_notifications so unread_count reflects what's still outstanding.",
    {
      notification_id: z
        .string()
        .optional()
        .describe("UUID of a single notification to mark read (from flowforge_list_notifications). Omit to mark ALL unread as read."),
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

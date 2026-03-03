import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import type { McpContext } from "../server.js";

export function registerEventTools(server: McpServer, ctx: McpContext): void {
  server.tool(
    "flowforge_send_event",
    "Send an event to trigger FlowForge workflow functions.",
    {
      name: z.string().describe("Event name (e.g., 'order/created')"),
      data: z
        .record(z.unknown())
        .default({})
        .describe("Event data payload as key-value pairs"),
      id: z
        .string()
        .optional()
        .describe("Optional event ID for idempotency"),
    },
    async (args) => {
      const { data, error } = await ctx.client.events.send(args.name, args.data as Record<string, unknown>, {
        id: args.id,
      });
      if (error) {
        return {
          content: [{ type: "text" as const, text: `Error: ${error.message}` }],
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
    "flowforge_list_events",
    "List events that have been sent to FlowForge. Optionally filter by name.",
    {
      name: z.string().optional().describe("Filter by event name"),
      limit: z.number().default(20).describe("Maximum number of events to return"),
    },
    async (args) => {
      const query = ctx.client.events.select();
      if (args.name) query.eq("name", args.name);
      query.limit(args.limit);
      const { data, error } = await query.execute();
      if (error) {
        return {
          content: [{ type: "text" as const, text: `Error: ${error.message}` }],
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
    "flowforge_get_event",
    "Get details of a specific event by its ID.",
    {
      event_id: z.string().describe("The event ID"),
    },
    async (args) => {
      const { data, error } = await ctx.client.events.get(args.event_id);
      if (error) {
        return {
          content: [{ type: "text" as const, text: `Error: ${error.message}` }],
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

import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import type { McpContext } from "../server.js";

export function registerEventTools(server: McpServer, ctx: McpContext): void {
  server.tool(
    "flowforge_send_event",
    "Send an event into FlowForge. Any function with trigger_type='event' and a matching trigger_value will fan out into a new run. Returns the event id and any runs created. Use flowforge_list_runs shortly after to monitor execution. Passing an explicit id makes the send idempotent — repeats return the original event.",
    {
      name: z
        .string()
        .describe("Event name, typically 'domain/action' (e.g. 'order/created', 'user/signup')."),
      data: z
        .record(z.unknown())
        .default({})
        .describe("Event data payload as a JSON object. Available to functions as event.data."),
      id: z
        .string()
        .optional()
        .describe("Optional client-supplied event id for idempotency. Resend with the same id to deduplicate."),
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
    "List events that have been sent to FlowForge, ordered by send time (most recent first). Use to audit what's been fired or verify that a just-sent event was accepted. For the runs that each event triggered, follow up with flowforge_list_runs.",
    {
      name: z
        .string()
        .optional()
        .describe("Filter to a single event name (e.g. 'order/created')."),
      limit: z
        .number()
        .default(20)
        .describe("Maximum number of events to return. Server caps at 100."),
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
    "Get the full record of a single event — name, data payload, timestamp, and ingest metadata. Use after flowforge_list_events to inspect a specific event, or as a starting point for flowforge_list_runs (filter by the event's function matches).",
    {
      event_id: z
        .string()
        .describe("The event UUID (from flowforge_list_events or a prior flowforge_send_event response)."),
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

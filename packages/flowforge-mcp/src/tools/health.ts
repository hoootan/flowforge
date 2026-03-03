import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import type { McpContext } from "../server.js";

export function registerHealthTools(server: McpServer, ctx: McpContext): void {
  server.tool(
    "flowforge_health_check",
    "Check if the FlowForge server is healthy and reachable.",
    {},
    async () => {
      const { data, error } = await ctx.client.health.check();
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
          {
            type: "text" as const,
            text: data ? "FlowForge server is healthy" : "FlowForge server is unhealthy",
          },
        ],
      };
    }
  );

  server.tool(
    "flowforge_get_stats",
    "Get FlowForge server statistics (run counts, function counts, queue depth, etc.).",
    {},
    async () => {
      const { data, error } = await ctx.client.health.stats();
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

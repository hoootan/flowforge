import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import type { McpContext } from "../server.js";

export function registerHealthTools(server: McpServer, ctx: McpContext): void {
  server.tool(
    "flowforge_health_check",
    "Binary reachability check — returns a short 'healthy' / 'unhealthy' string telling you whether the FlowForge server is up and responding. Takes no parameters. Use this as a first step before other tool calls, or to diagnose a string of unrelated errors. For platform usage stats (run counts, queue depth), use flowforge_get_stats instead.",
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
    "Get aggregate platform statistics: total runs by status, function count, queue depth, active workers, and recent throughput. Takes no parameters — returns a one-shot snapshot, not a time series. Use for a high-level pulse check. For just connectivity (is the server up?), use flowforge_health_check. For granular per-function details, use flowforge_list_runs with a function_id filter.",
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

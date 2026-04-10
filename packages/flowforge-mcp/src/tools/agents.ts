import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import type { McpContext } from "../server.js";
import { directFetch } from "../server.js";

export function registerAgentTools(server: McpServer, ctx: McpContext): void {
  server.tool(
    "flowforge_list_agents",
    "List AI agents in the workspace. Agents are named AI identities that can be assigned tasks and execute workflows.",
    {
      status: z.enum(["online", "idle", "busy", "offline"]).optional().describe("Filter by agent status"),
      is_active: z.boolean().optional().describe("Filter by active/inactive"),
    },
    async (args) => {
      try {
        const params: Record<string, string> = {};
        if (args.status) params.status = args.status;
        if (args.is_active !== undefined) params.is_active = String(args.is_active);
        const qs = new URLSearchParams(params).toString();
        const data = await directFetch(ctx, "GET", `/agents${qs ? `?${qs}` : ""}`);
        const result = data as { agents: unknown[]; total: number };
        return {
          content: [{ type: "text" as const, text: JSON.stringify({ items: result.agents, total: result.total, has_more: false }, null, 2) }],
        };
      } catch (e: unknown) {
        return { content: [{ type: "text" as const, text: `Error: ${(e as Error).message}` }], isError: true };
      }
    }
  );

  server.tool(
    "flowforge_get_agent",
    "Get details of a specific agent including status, model, skills, and performance stats.",
    {
      agent_id: z.string().describe("The agent UUID"),
    },
    async (args) => {
      try {
        const data = await directFetch(ctx, "GET", `/agents/${args.agent_id}`);
        return { content: [{ type: "text" as const, text: JSON.stringify(data, null, 2) }] };
      } catch (e: unknown) {
        return { content: [{ type: "text" as const, text: `Error: ${(e as Error).message}` }], isError: true };
      }
    }
  );

  server.tool(
    "flowforge_create_agent",
    "Create a new AI agent. Agents are team members that can be assigned to tasks and linked to functions.",
    {
      name: z.string().describe("Display name (e.g., 'Code Reviewer', 'Deploy Bot')"),
      description: z.string().optional().describe("What this agent does"),
      model: z.string().optional().describe("Default AI model (e.g., 'claude-sonnet-4-6')"),
      system_prompt: z.string().optional().describe("Agent personality/instructions"),
    },
    async (args) => {
      try {
        const data = await directFetch(ctx, "POST", "/agents", args);
        return { content: [{ type: "text" as const, text: JSON.stringify(data, null, 2) }] };
      } catch (e: unknown) {
        return { content: [{ type: "text" as const, text: `Error: ${(e as Error).message}` }], isError: true };
      }
    }
  );

  server.tool(
    "flowforge_update_agent",
    "Update an agent's properties — name, status, model, system prompt, or active state.",
    {
      agent_id: z.string().describe("The agent UUID"),
      name: z.string().optional().describe("New display name"),
      status: z.enum(["online", "idle", "busy", "offline"]).optional().describe("New status"),
      model: z.string().optional().describe("New default model"),
      system_prompt: z.string().optional().describe("New instructions"),
      is_active: z.boolean().optional().describe("Enable or disable the agent"),
    },
    async (args) => {
      try {
        const { agent_id, ...updates } = args;
        const data = await directFetch(ctx, "PATCH", `/agents/${agent_id}`, updates);
        return { content: [{ type: "text" as const, text: JSON.stringify(data, null, 2) }] };
      } catch (e: unknown) {
        return { content: [{ type: "text" as const, text: `Error: ${(e as Error).message}` }], isError: true };
      }
    }
  );

  server.tool(
    "flowforge_set_agent_skills",
    "Set which skills are enabled for an agent. Enabled skills inject their knowledge into the agent's context at runtime.",
    {
      agent_id: z.string().describe("The agent UUID"),
      skill_ids: z.array(z.string()).describe("List of skill template UUIDs to enable. Pass empty array to disable all."),
    },
    async (args) => {
      try {
        const data = await directFetch(ctx, "PUT", `/agents/${args.agent_id}/skills`, args.skill_ids);
        return { content: [{ type: "text" as const, text: JSON.stringify(data, null, 2) }] };
      } catch (e: unknown) {
        return { content: [{ type: "text" as const, text: `Error: ${(e as Error).message}` }], isError: true };
      }
    }
  );
}

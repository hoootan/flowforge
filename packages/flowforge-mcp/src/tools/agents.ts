import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import type { McpContext } from "../server.js";
import { directFetch } from "../server.js";

export function registerAgentTools(server: McpServer, ctx: McpContext): void {
  server.tool(
    "flowforge_list_agents",
    "List AI agents in the workspace, ordered by creation time (newest first). Agents are named AI identities — each has its own model, system prompt, and skill set — that can be assigned to tasks and linked to functions. Use flowforge_get_agent for a single agent's full record.",
    {
      status: z
        .enum(["online", "idle", "busy", "offline"])
        .optional()
        .describe("Filter by current agent status: online, idle, busy, or offline."),
      is_active: z
        .boolean()
        .optional()
        .describe("Filter by active/inactive. Inactive agents still exist but can't be assigned new work."),
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
    "Get a single agent's full record: status, model, system prompt, enabled skills, and aggregate performance stats (tasks completed, tool calls, etc.). Use after flowforge_list_agents to inspect a specific agent.",
    {
      agent_id: z
        .string()
        .describe("The agent UUID (from flowforge_list_agents)."),
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
    "Create a new AI agent in the workspace. Agents are team members that can be assigned tasks (flowforge_create_task) and linked to functions. To enable skills on the agent, follow up with flowforge_set_agent_skills.",
    {
      name: z
        .string()
        .describe("Display name (e.g. 'Code Reviewer', 'Deploy Bot'). Visible across the dashboard."),
      description: z
        .string()
        .optional()
        .describe("Short description of what the agent does. Shown to teammates."),
      model: z
        .string()
        .optional()
        .describe("Default AI model id (e.g. 'claude-sonnet-4-6', 'gpt-4o'). Falls back to the workspace default if omitted."),
      system_prompt: z
        .string()
        .optional()
        .describe("Agent personality/instructions applied on every run. Can be overridden per function."),
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
    "Update fields on an existing agent — name, current status, model, system prompt, or active flag. Only provided fields are changed; omitted fields keep their current value. For creating a new agent, use flowforge_create_agent; for managing skills, use flowforge_set_agent_skills.",
    {
      agent_id: z
        .string()
        .describe("The agent UUID to update (from flowforge_list_agents)."),
      name: z
        .string()
        .optional()
        .describe("New display name."),
      status: z
        .enum(["online", "idle", "busy", "offline"])
        .optional()
        .describe("Manual status override: online, idle, busy, or offline."),
      model: z
        .string()
        .optional()
        .describe("New default AI model id."),
      system_prompt: z
        .string()
        .optional()
        .describe("Replacement system prompt (not merged)."),
      is_active: z
        .boolean()
        .optional()
        .describe("Toggle active/inactive. Inactive agents can't be assigned new work."),
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
    "Set the complete list of skills enabled for an agent. Enabled skills have their SKILL.md content injected into the agent's context at runtime. Replaces wholesale — pass an empty array to disable all skills. The function-side equivalent is flowforge_set_function_skills.",
    {
      agent_id: z
        .string()
        .describe("The agent UUID (from flowforge_list_agents)."),
      skill_ids: z
        .array(z.string())
        .describe("List of skill template UUIDs to enable (from flowforge_list_skills). Empty array disables all."),
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

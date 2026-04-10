import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import type { FlowForgeClient } from "flowforge-client";
import { registerEventTools } from "./tools/events.js";
import { registerFunctionTools } from "./tools/functions.js";
import { registerRunTools } from "./tools/runs.js";
import { registerToolTools } from "./tools/tools.js";
import { registerApprovalTools } from "./tools/approvals.js";
import { registerHealthTools } from "./tools/health.js";
import { registerCredentialTools } from "./tools/credentials.js";
import { registerAgentTools } from "./tools/agents.js";
import { registerTaskTools } from "./tools/tasks.js";
import { registerSkillTools } from "./tools/skills.js";
import { registerCommentTools } from "./tools/comments.js";
import { registerNotificationTools } from "./tools/notifications.js";

export interface McpContext {
  client: FlowForgeClient;
  serverUrl: string;
  apiKey?: string;
}

export async function directFetch(
  ctx: McpContext,
  method: string,
  path: string,
  body?: unknown
): Promise<unknown> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (ctx.apiKey) {
    headers["X-FlowForge-API-Key"] = ctx.apiKey;
  }

  const response = await fetch(
    `${ctx.serverUrl.replace(/\/$/, "")}/api/v1${path}`,
    {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    }
  );

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(
      (error as Record<string, string>).detail || `HTTP ${response.status}`
    );
  }

  if (response.status === 204) {
    return { success: true };
  }

  return response.json();
}

export function createMcpServer(
  client: FlowForgeClient,
  config: { serverUrl: string; apiKey?: string }
): McpServer {
  const server = new McpServer(
    { name: "FlowForge", version: "0.2.0" },
    {
      instructions: `FlowForge is an AI workflow orchestration platform with durable execution, agent team management, and a skill marketplace.

Suggested workflow:
1. flowforge_health_check — verify server connectivity
2. flowforge_list_functions — see available workflows
3. flowforge_list_agents — see AI team members and their status
4. flowforge_get_task_board — view project status (Kanban board)
5. flowforge_send_event — trigger a workflow
6. flowforge_list_runs — monitor execution progress
7. flowforge_list_skills — browse available skills and marketplace imports
8. flowforge_list_notifications — check for approvals, mentions, and alerts

Key concepts:
- Functions are triggered by events, cron, or webhooks
- Agents are AI team members with their own model, skills, and personality
- Tasks are Kanban work items assignable to humans or agents
- Skills provide reusable knowledge injected into agents at runtime
- Approvals gate tool calls that need human review`,
    }
  );

  const ctx: McpContext = {
    client,
    serverUrl: config.serverUrl,
    apiKey: config.apiKey,
  };

  // Core workflow tools
  registerEventTools(server, ctx);
  registerFunctionTools(server, ctx);
  registerRunTools(server, ctx);
  registerToolTools(server, ctx);
  registerApprovalTools(server, ctx);

  // Agent team platform tools
  registerAgentTools(server, ctx);
  registerTaskTools(server, ctx);
  registerSkillTools(server, ctx);
  registerCommentTools(server, ctx);
  registerNotificationTools(server, ctx);

  // Infrastructure tools
  registerHealthTools(server, ctx);
  registerCredentialTools(server, ctx);

  return server;
}

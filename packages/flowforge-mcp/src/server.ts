import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import type { FlowForgeClient } from "flowforge-client";
import { registerEventTools } from "./tools/events.js";
import { registerFunctionTools } from "./tools/functions.js";
import { registerRunTools } from "./tools/runs.js";
import { registerToolTools } from "./tools/tools.js";
import { registerApprovalTools } from "./tools/approvals.js";
import { registerHealthTools } from "./tools/health.js";
import { registerCredentialTools } from "./tools/credentials.js";

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

  return response.json();
}

export function createMcpServer(
  client: FlowForgeClient,
  config: { serverUrl: string; apiKey?: string }
): McpServer {
  const server = new McpServer({
    name: "FlowForge",
    version: "0.1.0",
  });

  const ctx: McpContext = {
    client,
    serverUrl: config.serverUrl,
    apiKey: config.apiKey,
  };

  registerEventTools(server, ctx);
  registerFunctionTools(server, ctx);
  registerRunTools(server, ctx);
  registerToolTools(server, ctx);
  registerApprovalTools(server, ctx);
  registerHealthTools(server, ctx);
  registerCredentialTools(server, ctx);

  return server;
}

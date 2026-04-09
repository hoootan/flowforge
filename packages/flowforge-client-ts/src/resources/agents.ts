/**
 * FlowForge TypeScript Client - Agents Resource
 */

import type { RequestFn } from "../builder";
import type { Result } from "../types";

export interface Agent {
  id: string;
  name: string;
  slug: string;
  avatar_url: string | null;
  description: string | null;
  status: "online" | "idle" | "busy" | "offline";
  model: string | null;
  system_prompt: string | null;
  capabilities: Record<string, unknown>;
  config: Record<string, unknown>;
  stats: Record<string, unknown>;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface CreateAgentInput {
  name: string;
  description?: string;
  avatar_url?: string;
  model?: string;
  system_prompt?: string;
  capabilities?: Record<string, unknown>;
  config?: Record<string, unknown>;
}

export interface AgentListResponse {
  agents: Agent[];
  total: number;
}

export class AgentsResource {
  constructor(private request: RequestFn) {}

  async list(params?: { status?: string; is_active?: boolean }): Promise<Result<AgentListResponse>> {
    const query = new URLSearchParams();
    if (params?.status) query.set("status", params.status);
    if (params?.is_active !== undefined) query.set("is_active", String(params.is_active));
    const qs = query.toString();
    return this.request<AgentListResponse>("GET", `/agents${qs ? `?${qs}` : ""}`);
  }

  async get(agentId: string): Promise<Result<Agent>> {
    return this.request<Agent>("GET", `/agents/${agentId}`);
  }

  async create(data: CreateAgentInput): Promise<Result<Agent>> {
    return this.request<Agent>("POST", "/agents", data);
  }

  async update(agentId: string, data: Partial<CreateAgentInput> & { status?: string; is_active?: boolean }): Promise<Result<Agent>> {
    return this.request<Agent>("PATCH", `/agents/${agentId}`, data);
  }

  async delete(agentId: string): Promise<Result<{ success: boolean }>> {
    return this.request<{ success: boolean }>("DELETE", `/agents/${agentId}`);
  }
}

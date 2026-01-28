/**
 * FlowForge API client for the dashboard.
 */

import type {
  User,
  UserWithPermissions,
  CreateUserRequest,
  UpdateUserRequest,
  UsersResponse,
} from "@/lib/auth/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export interface Run {
  id: string;
  function_id: string;
  event_id: string | null;
  status: "pending" | "running" | "completed" | "failed" | "paused" | "cancelled";
  trigger_type: string;
  trigger_data: Record<string, unknown>;
  output: Record<string, unknown> | null;
  error: Record<string, unknown> | null;
  attempt: number;
  max_attempts: number;
  started_at: string | null;
  ended_at: string | null;
  created_at: string;
}

export interface Step {
  id: string;
  step_id: string;
  step_type: "run" | "sleep" | "ai" | "wait_for_event" | "invoke" | "send_event" | "agent";
  status: "pending" | "running" | "completed" | "failed" | "sleeping" | "waiting";
  input: Record<string, unknown> | null;
  output: Record<string, unknown> | null;
  error: Record<string, unknown> | null;
  attempt: number;
  max_attempts: number;
  started_at: string | null;
  ended_at: string | null;
  created_at: string;
}

export interface AgentResult {
  output: string;
  status: "completed" | "max_iterations" | "max_tool_calls" | "failed";
  iterations: number;
  tool_calls_count: number;
  tokens_used: number;
  messages: any[];
  tool_calls: any[];
}

export interface PendingApproval {
  id: string;
  tool_call_id: string;
  tool_name: string;
  arguments: Record<string, any>;
  run_id: string;
  function_id: string;
  agent_conversation: any[];
  created_at: string;
  status: string;
  timeout_at: string;
}

// Server returns different field names
interface ServerApproval {
  id: string;
  tool_call_id: string;
  tool_name: string;
  tool_arguments: Record<string, any>;
  run_id: string;
  step_id: string;
  created_at: string;
  status: string;
  timeout_at: string;
}

export interface ApprovalsResponse {
  approvals: PendingApproval[];
  total: number;
}

export interface RunWithSteps extends Run {
  steps: Step[];
}

export interface Function {
  id: string;
  function_id: string;
  name: string;
  trigger_type: "event" | "cron" | "webhook";
  trigger_value: string;
  trigger_expression: string | null;
  endpoint_url: string | null;
  is_inline: boolean;
  system_prompt: string | null;
  tools_config: string[] | null;
  agent_config: Record<string, unknown> | null;
  config: Record<string, unknown>;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Tool {
  id: string;
  name: string;
  description: string;
  parameters: Record<string, unknown>;
  code: string | null;
  is_builtin: boolean;
  requires_approval: boolean;
  approval_timeout: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ToolsResponse {
  tools: Tool[];
  total: number;
}

export interface Event {
  id: string;
  event_id: string;
  name: string;
  data: Record<string, unknown>;
  timestamp: string;
  received_at: string;
  user_id: string | null;
  processed: boolean;
}

export interface RunsResponse {
  runs: Run[];
  total: number;
  page: number;
  page_size: number;
}

export interface FunctionsResponse {
  functions: Function[];
  total: number;
}

export interface EventsResponse {
  events: Event[];
  total: number;
  page: number;
  page_size: number;
}

export interface Stats {
  runs: { total: number; completed: number; failed: number; running: number };
  functions: { total: number; active: number };
  events: { today: number; total: number };
  queue: { pending: number; running: number; scheduled: number };
}

// API Key types
export interface ApiKey {
  id: string;
  name: string;
  key_prefix: string;
  key_type: "live" | "test" | "ro";
  scopes: string[];
  expires_at: string | null;
  last_used_at: string | null;
  is_active: boolean;
  created_at: string;
}

export interface ApiKeyCreated extends ApiKey {
  key: string; // Only returned once on creation
}

export interface ApiKeysResponse {
  keys: ApiKey[];
  total: number;
}

export interface CreateApiKeyRequest {
  name: string;
  key_type?: "live" | "test" | "ro";
  scopes?: string[];
  expires_in_days?: number;
}

const emptyRunsResponse: RunsResponse = { runs: [], total: 0, page: 1, page_size: 50 };
const emptyFunctionsResponse: FunctionsResponse = { functions: [], total: 0 };
const emptyEventsResponse: EventsResponse = { events: [], total: 0, page: 1, page_size: 50 };
const emptyToolsResponse: ToolsResponse = { tools: [], total: 0 };
const emptyApprovalsResponse: ApprovalsResponse = { approvals: [], total: 0 };
const emptyUsersResponse: UsersResponse = { users: [], total: 0 };
const emptyApiKeysResponse: ApiKeysResponse = { keys: [], total: 0 };
const emptyStats: Stats = {
  runs: { total: 0, completed: 0, failed: 0, running: 0 },
  functions: { total: 0, active: 0 },
  events: { today: 0, total: 0 },
  queue: { pending: 0, running: 0, scheduled: 0 },
};

class FlowForgeAPI {
  private baseUrl: string;
  private getToken: (() => string | null) | null = null;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  /**
   * Set a function to get the auth token.
   * This allows the API client to be used with the auth store.
   */
  setTokenProvider(getToken: () => string | null) {
    this.getToken = getToken;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;

    // Get auth token if provider is set
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...(options.headers as Record<string, string>),
    };

    if (this.getToken) {
      const token = this.getToken();
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }
    }

    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
  }

  // Runs
  async getRuns(params?: {
    page?: number;
    page_size?: number;
    status?: string;
    function_id?: string;
  }): Promise<RunsResponse> {
    const searchParams = new URLSearchParams();
    if (params?.page) searchParams.set("page", String(params.page));
    if (params?.page_size) searchParams.set("page_size", String(params.page_size));
    if (params?.status && params.status !== "all") searchParams.set("status", params.status);
    if (params?.function_id) searchParams.set("function_id", params.function_id);

    const query = searchParams.toString();
    try {
      return await this.request<RunsResponse>(`/runs${query ? `?${query}` : ""}`);
    } catch {
      return emptyRunsResponse;
    }
  }

  async getRun(runId: string): Promise<RunWithSteps | null> {
    try {
      return await this.request<RunWithSteps>(`/runs/${runId}`);
    } catch {
      return null;
    }
  }

  async cancelRun(runId: string): Promise<{ success: boolean; message: string; run_id: string } | null> {
    try {
      return await this.request(`/runs/${runId}/cancel`, { method: "POST" });
    } catch {
      return null;
    }
  }

  async replayRun(runId: string): Promise<RunWithSteps | null> {
    try {
      return await this.request<RunWithSteps>(`/runs/${runId}/replay`, { method: "POST" });
    } catch {
      return null;
    }
  }

  // Functions
  async getFunctions(params?: {
    trigger_type?: string;
    is_active?: boolean;
  }): Promise<FunctionsResponse> {
    const searchParams = new URLSearchParams();
    if (params?.trigger_type) searchParams.set("trigger_type", params.trigger_type);
    if (params?.is_active !== undefined) searchParams.set("is_active", String(params.is_active));

    const query = searchParams.toString();
    try {
      return await this.request<FunctionsResponse>(`/functions${query ? `?${query}` : ""}`);
    } catch {
      return emptyFunctionsResponse;
    }
  }

  async getFunction(functionId: string): Promise<Function | null> {
    try {
      return await this.request<Function>(`/functions/${functionId}`);
    } catch {
      return null;
    }
  }

  // Tools
  async getTools(params?: {
    include_builtin?: boolean;
    is_active?: boolean;
    requires_approval?: boolean;
  }): Promise<ToolsResponse> {
    const searchParams = new URLSearchParams();
    if (params?.include_builtin !== undefined) searchParams.set("include_builtin", String(params.include_builtin));
    if (params?.is_active !== undefined) searchParams.set("is_active", String(params.is_active));
    if (params?.requires_approval !== undefined) searchParams.set("requires_approval", String(params.requires_approval));

    const query = searchParams.toString();
    try {
      return await this.request<ToolsResponse>(`/tools${query ? `?${query}` : ""}`);
    } catch {
      return emptyToolsResponse;
    }
  }

  async getTool(toolName: string): Promise<Tool | null> {
    try {
      return await this.request<Tool>(`/tools/${toolName}`);
    } catch {
      return null;
    }
  }

  async createTool(data: {
    name: string;
    description: string;
    parameters: Record<string, unknown>;
    code?: string;
    requires_approval?: boolean;
    approval_timeout?: string;
  }): Promise<Tool | null> {
    try {
      return await this.request<Tool>("/tools", {
        method: "POST",
        body: JSON.stringify(data),
      });
    } catch {
      return null;
    }
  }

  async updateTool(
    toolName: string,
    data: Partial<{
      description: string;
      parameters: Record<string, unknown>;
      code: string;
      requires_approval: boolean;
      approval_timeout: string;
      is_active: boolean;
    }>
  ): Promise<Tool | null> {
    try {
      return await this.request<Tool>(`/tools/${toolName}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      });
    } catch {
      return null;
    }
  }

  async deleteTool(toolName: string): Promise<boolean> {
    try {
      await this.request(`/tools/${toolName}`, {
        method: "DELETE",
      });
      return true;
    } catch {
      return false;
    }
  }

  async createInlineFunction(data: {
    id: string;
    name: string;
    trigger: { type: string; value: string; expression?: string };
    system_prompt: string;
    tools: string[];
    agent_config?: { model?: string; max_iterations?: number; max_tool_calls?: number };
    config?: Record<string, unknown>;
  }): Promise<Function | null> {
    try {
      return await this.request<Function>("/functions/inline", {
        method: "POST",
        body: JSON.stringify(data),
      });
    } catch {
      return null;
    }
  }

  async createWorkerFunction(data: {
    id: string;
    name: string;
    trigger: { type: string; value: string; expression?: string };
    endpoint_url: string;
    config?: Record<string, unknown>;
  }): Promise<Function | null> {
    try {
      return await this.request<Function>("/functions/worker", {
        method: "POST",
        body: JSON.stringify(data),
      });
    } catch {
      return null;
    }
  }

  async updateFunction(
    functionId: string,
    data: Partial<{
      name: string;
      trigger: { type: string; value: string; expression?: string };
      system_prompt: string;
      tools: string[];
      agent_config: { model?: string; max_iterations?: number; max_tool_calls?: number };
      endpoint_url: string;
      config: Record<string, unknown>;
      is_active: boolean;
    }>
  ): Promise<Function | null> {
    try {
      return await this.request<Function>(`/functions/${functionId}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      });
    } catch {
      return null;
    }
  }

  async deleteFunction(functionId: string): Promise<boolean> {
    try {
      await this.request(`/functions/${functionId}`, {
        method: "DELETE",
      });
      return true;
    } catch {
      return false;
    }
  }

  // Events
  async getEvents(params?: {
    page?: number;
    page_size?: number;
    name?: string;
  }): Promise<EventsResponse> {
    const searchParams = new URLSearchParams();
    if (params?.page) searchParams.set("page", String(params.page));
    if (params?.page_size) searchParams.set("page_size", String(params.page_size));
    if (params?.name) searchParams.set("name", params.name);

    const query = searchParams.toString();
    try {
      return await this.request<EventsResponse>(`/events${query ? `?${query}` : ""}`);
    } catch {
      return emptyEventsResponse;
    }
  }

  async getEvent(eventId: string): Promise<Event | null> {
    try {
      return await this.request<Event>(`/events/${eventId}`);
    } catch {
      return null;
    }
  }

  async sendEvent(data: {
    name: string;
    data: Record<string, unknown>;
    id?: string;
    user_id?: string;
    timestamp?: string;
  }): Promise<Event | null> {
    try {
      return await this.request<Event>("/events", {
        method: "POST",
        body: JSON.stringify(data),
      });
    } catch {
      return null;
    }
  }

  // Stats
  async getStats(): Promise<Stats> {
    try {
      return await this.request<Stats>("/stats");
    } catch {
      return emptyStats;
    }
  }

  // Health check
  async checkHealth(): Promise<boolean> {
    try {
      await this.request("/health");
      return true;
    } catch {
      return false;
    }
  }

  // Agent / Approvals
  async getApprovals(params?: {
    pending_only?: boolean;
  }): Promise<ApprovalsResponse> {
    const searchParams = new URLSearchParams();
    if (params?.pending_only !== undefined) {
      searchParams.set("pending_only", String(params.pending_only));
    }

    const query = searchParams.toString();
    try {
      const response = await this.request<{ approvals: ServerApproval[]; total: number }>(`/approvals${query ? `?${query}` : ""}`);
      // Transform server response to expected format
      const approvals: PendingApproval[] = response.approvals.map((a) => ({
        id: a.id,
        tool_call_id: a.tool_call_id,
        tool_name: a.tool_name,
        arguments: a.tool_arguments || {},
        run_id: a.run_id,
        function_id: a.step_id, // Use step_id as function_id for now
        agent_conversation: [], // Server doesn't provide this yet
        created_at: a.created_at,
        status: a.status,
        timeout_at: a.timeout_at,
      }));
      return { approvals, total: response.total };
    } catch {
      return emptyApprovalsResponse;
    }
  }

  async approveToolCall(id: string): Promise<{ success: boolean; message: string } | null> {
    try {
      return await this.request(`/approvals/${id}/approve`, {
        method: "POST",
        body: JSON.stringify({}),  // Server requires JSON body
      });
    } catch {
      return null;
    }
  }

  async rejectToolCall(id: string, reason: string): Promise<{ success: boolean; message: string } | null> {
    try {
      return await this.request(`/approvals/${id}/reject`, {
        method: "POST",
        body: JSON.stringify({ reason }),
      });
    } catch {
      return null;
    }
  }

  // Users (Admin only)
  async getUsers(params?: {
    include_inactive?: boolean;
  }): Promise<UsersResponse> {
    const searchParams = new URLSearchParams();
    if (params?.include_inactive !== undefined) {
      searchParams.set("include_inactive", String(params.include_inactive));
    }

    const query = searchParams.toString();
    try {
      return await this.request<UsersResponse>(`/users${query ? `?${query}` : ""}`);
    } catch {
      return emptyUsersResponse;
    }
  }

  async getUser(userId: string): Promise<User | null> {
    try {
      return await this.request<User>(`/users/${userId}`);
    } catch {
      return null;
    }
  }

  async createUser(data: CreateUserRequest): Promise<User | null> {
    try {
      return await this.request<User>("/users", {
        method: "POST",
        body: JSON.stringify(data),
      });
    } catch {
      return null;
    }
  }

  async updateUser(userId: string, data: UpdateUserRequest): Promise<User | null> {
    try {
      return await this.request<User>(`/users/${userId}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      });
    } catch {
      return null;
    }
  }

  async deleteUser(userId: string): Promise<boolean> {
    try {
      await this.request(`/users/${userId}`, {
        method: "DELETE",
      });
      return true;
    } catch {
      return false;
    }
  }

  async getCurrentUser(): Promise<UserWithPermissions | null> {
    try {
      return await this.request<UserWithPermissions>("/users/me");
    } catch {
      return null;
    }
  }

  // API Keys
  async getApiKeys(params?: {
    include_revoked?: boolean;
  }): Promise<ApiKeysResponse> {
    const searchParams = new URLSearchParams();
    if (params?.include_revoked !== undefined) {
      searchParams.set("include_revoked", String(params.include_revoked));
    }

    const query = searchParams.toString();
    try {
      return await this.request<ApiKeysResponse>(`/auth/keys${query ? `?${query}` : ""}`);
    } catch {
      return emptyApiKeysResponse;
    }
  }

  async createApiKey(data: CreateApiKeyRequest): Promise<ApiKeyCreated | null> {
    try {
      return await this.request<ApiKeyCreated>("/auth/keys", {
        method: "POST",
        body: JSON.stringify(data),
      });
    } catch {
      return null;
    }
  }

  async revokeApiKey(keyId: string, reason?: string): Promise<boolean> {
    try {
      await this.request(`/auth/keys/${keyId}`, {
        method: "DELETE",
        body: reason ? JSON.stringify({ reason }) : undefined,
      });
      return true;
    } catch {
      return false;
    }
  }
}

export const api = new FlowForgeAPI();
export default api;

// Re-export auth types for convenience
export type {
  User,
  UserWithPermissions,
  CreateUserRequest,
  UpdateUserRequest,
  UsersResponse,
} from "@/lib/auth/types";

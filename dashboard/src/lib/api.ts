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
  step_type: "run" | "sleep" | "ai" | "wait_for_event" | "invoke" | "send_event" | "agent" | "sub_agent";
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
  tool_type: string;
  code: string | null;
  webhook_url: string | null;
  webhook_method: string;
  webhook_headers: Record<string, string> | null;
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

// AI Provider types
export type AuthType = "api_key" | "oauth_token";

export interface AIProvider {
  id: string;
  provider_name: string;
  display_name: string;
  api_key_prefix: string;
  auth_type: AuthType;
  base_url: string | null;
  is_active: boolean;
  is_default: boolean;
  config: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface AIProvidersResponse {
  providers: AIProvider[];
  total: number;
}

export interface KnownProviderInfo {
  name: string;
  display_name: string;
  models: string[];
  default_model: string | null;
}

export interface KnownProvidersResponse {
  providers: KnownProviderInfo[];
}

export interface CreateAIProviderRequest {
  provider_name: "openai" | "anthropic" | "google" | "mistral" | "cohere" | "custom";
  api_key: string;
  auth_type?: AuthType;
  display_name?: string;
  base_url?: string;
  is_default?: boolean;
  config?: Record<string, unknown>;
}

export interface UpdateAIProviderRequest {
  api_key?: string;
  auth_type?: AuthType;
  display_name?: string;
  base_url?: string;
  is_active?: boolean;
  is_default?: boolean;
  config?: Record<string, unknown>;
}

export interface AIProviderTestResult {
  status: "healthy" | "error" | "unknown";
  message: string;
  model_tested?: string;
}

// Usage types
export interface UsageSummary {
  total_requests: number;
  total_tokens: number;
  prompt_tokens: number;
  completion_tokens: number;
  total_cost_usd: number;
  avg_latency_ms: number;
  period_start: string | null;
  period_end: string | null;
}

export interface UsageByProvider {
  provider: string;
  requests: number;
  total_tokens: number;
  cost_usd: number;
  avg_latency_ms: number;
}

export interface UsageByModel {
  model: string;
  provider: string;
  requests: number;
  total_tokens: number;
  cost_usd: number;
  avg_latency_ms: number;
}

export interface DailyUsage {
  date: string;
  requests: number;
  total_tokens: number;
  cost_usd: number;
}

// Model Pricing types
export type PricingSource = "tenant" | "global" | "default" | "fallback";

export interface ModelPricingConfig {
  id: string;
  model_id: string;
  provider: string;
  input_price_per_m: number;
  output_price_per_m: number;
  display_name: string | null;
  is_active: boolean;
  is_global: boolean;
  created_at: string;
  updated_at: string;
}

export interface ModelPricingListResponse {
  pricing_configs: ModelPricingConfig[];
  total: number;
}

export interface EffectiveModelPricing {
  model_id: string;
  provider: string;
  input_price_per_m: number;
  output_price_per_m: number;
  display_name: string | null;
  source: PricingSource;
  pricing_id: string | null;
}

export interface EffectiveModelPricingListResponse {
  models: EffectiveModelPricing[];
  total: number;
}

export interface DefaultModelPricing {
  model_id: string;
  provider: string;
  input_price_per_m: number;
  output_price_per_m: number;
}

export interface DefaultModelPricingListResponse {
  defaults: DefaultModelPricing[];
  total: number;
  fallback_input_price: number;
  fallback_output_price: number;
}

export interface CreateModelPricingRequest {
  model_id: string;
  provider: string;
  input_price_per_m: number;
  output_price_per_m: number;
  display_name?: string;
  is_global?: boolean;
}

export interface UpdateModelPricingRequest {
  input_price_per_m?: number;
  output_price_per_m?: number;
  display_name?: string;
  is_active?: boolean;
}

// Credential types
export interface Credential {
  id: string;
  name: string;
  credential_type: string;
  value_prefix: string;
  description: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface CredentialsResponse {
  credentials: Credential[];
  total: number;
}

export interface CreateCredentialRequest {
  name: string;
  credential_type?: string;
  value: string;
  description?: string;
}

export interface UpdateCredentialRequest {
  value?: string;
  description?: string;
  credential_type?: string;
  is_active?: boolean;
}

// ── Agent types ──────────────────────────────────────────────

export interface AgentType {
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
  enabled_skills: string[];
  is_active: boolean;
  created_at: string | null;
  updated_at: string | null;
}

export interface AgentsResponse {
  agents: AgentType[];
  total: number;
}

export interface CreateAgentRequest {
  name: string;
  description?: string;
  avatar_url?: string;
  model?: string;
  system_prompt?: string;
  capabilities?: Record<string, unknown>;
  config?: Record<string, unknown>;
}

export interface AgentStats {
  agent_id: string;
  total_runs: number;
  completed_runs: number;
  failed_runs: number;
  success_rate: number;
  total_tokens: number;
  total_cost_usd: number;
  avg_duration_ms: number;
  period_days: number;
}

// ── Task types ───────────────────────────────────────────────

export interface TaskType {
  id: string;
  identifier: string;
  title: string;
  description: string | null;
  status: "todo" | "in_progress" | "in_review" | "done" | "blocked" | "cancelled";
  priority: "urgent" | "high" | "medium" | "low" | "none";
  labels: string[];
  assignee_type: "user" | "agent" | null;
  assignee_user_id: string | null;
  assignee_agent_id: string | null;
  assignee_user: { id: string; name: string; email: string } | null;
  assignee_agent: { id: string; name: string; slug: string; avatar_url: string | null; status: string } | null;
  created_by_user_id: string | null;
  parent_task_id: string | null;
  function_id: string | null;
  run_id: string | null;
  sub_tasks_count: number;
  comments_count: number;
  metadata: Record<string, unknown>;
  created_at: string | null;
  updated_at: string | null;
}

export interface TasksResponse {
  tasks: TaskType[];
  total: number;
}

export interface TaskBoardResponse {
  columns: Record<string, TaskType[]>;
  total: number;
}

export interface CreateTaskRequest {
  title: string;
  description?: string;
  status?: string;
  priority?: string;
  labels?: string[];
  assignee_user_id?: string;
  assignee_agent_id?: string;
  parent_task_id?: string;
  function_id?: string;
  metadata?: Record<string, unknown>;
}

// ── Comment types ────────────────────────────────────────────

export interface CommentType {
  id: string;
  task_id: string | null;
  run_id: string | null;
  author_type: "user" | "agent" | "system";
  author_user_id: string | null;
  author_agent_id: string | null;
  author: { id?: string; name: string; email?: string; avatar_url?: string | null; type: string } | null;
  content: string;
  comment_type: string;
  mentions: unknown[];
  reactions: Record<string, string[]>;
  created_at: string | null;
  updated_at: string | null;
}

export interface CommentsResponse {
  comments: CommentType[];
  total: number;
}

export interface CreateCommentRequest {
  task_id?: string;
  run_id?: string;
  content: string;
  comment_type?: string;
  author_user_id?: string;
  author_agent_id?: string;
  mentions?: Record<string, unknown>[];
}

// ── Notification types ───────────────────────────────────────

export interface NotificationType {
  id: string;
  notification_type: string;
  title: string;
  body: string | null;
  resource_type: string | null;
  resource_id: string | null;
  data: Record<string, unknown>;
  is_read: boolean;
  is_archived: boolean;
  created_at: string | null;
}

export interface NotificationsResponse {
  notifications: NotificationType[];
  total: number;
  unread_count: number;
}

// ── Skill types ──────────────────────────────────────────────

export interface SkillType {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  category: string | null;
  icon: string | null;
  version: number;
  function_config: Record<string, unknown>;
  tools_config: Record<string, unknown>[];
  usage_count: number;
  is_builtin: boolean;
  is_active: boolean;
  tags: string[];
  source: "local" | "skills_sh" | "github";
  instructions: string | null;
  source_metadata: {
    repo?: string;
    path?: string;
    fetched_at?: string;
    external_id?: string;
    install_count?: number;
    frontmatter?: Record<string, unknown>;
  } | null;
  created_by_user_id: string | null;
  created_at: string | null;
  updated_at: string | null;
}

// ── Marketplace types ────────────────────────────────────────

export interface MarketplaceSearchResult {
  external_id: string;
  name: string;
  description: string;
  source: "skills_sh" | "github";
  repo: string;
  install_count: number;
  preview_url: string | null;
}

export interface MarketplaceSearchResponse {
  results: MarketplaceSearchResult[];
  total: number;
}

export interface SkillPreview {
  name: string;
  description: string;
  raw_content: string;
  frontmatter: Record<string, unknown>;
  body: string;
  repo: string;
  path: string;
}

export interface ImportSkillRequest {
  repo: string;
  path?: string;
  source?: string;
  external_id?: string;
  name_override?: string;
  category?: string;
  tags?: string[];
}

export interface SkillsResponse {
  skills: SkillType[];
  total: number;
}

export interface CreateSkillRequest {
  name: string;
  description?: string;
  category?: string;
  icon?: string;
  function_config?: Record<string, unknown>;
  tools_config?: Record<string, unknown>[];
  tags?: string[];
}

// ── Cost Dashboard types ─────────────────────────────────────

export interface CostDashboardData {
  summary: { summary: UsageSummary };
  by_provider: { providers: UsageByProvider[] };
  by_model: { models: UsageByModel[] };
  daily: { daily: DailyUsage[] };
}

const emptyCredentialsResponse: CredentialsResponse = { credentials: [], total: 0 };
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
  private refreshAccessToken: (() => Promise<boolean>) | null = null;
  private onAuthFailure: (() => void) | null = null;
  private isRefreshing: boolean = false;
  private refreshPromise: Promise<boolean> | null = null;

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

  /**
   * Set a function to refresh the access token.
   * Called automatically on 401 responses.
   */
  setRefreshHandler(refreshFn: () => Promise<boolean>) {
    this.refreshAccessToken = refreshFn;
  }

  /**
   * Set a callback for when authentication fails completely.
   * Called when refresh token is invalid or expired.
   */
  setAuthFailureHandler(handler: () => void) {
    this.onAuthFailure = handler;
  }

  private async tryRefresh(): Promise<boolean> {
    // If already refreshing, wait for that to complete
    if (this.isRefreshing && this.refreshPromise) {
      return this.refreshPromise;
    }

    if (!this.refreshAccessToken) {
      return false;
    }

    this.isRefreshing = true;
    this.refreshPromise = this.refreshAccessToken();

    try {
      const success = await this.refreshPromise;
      return success;
    } finally {
      this.isRefreshing = false;
      this.refreshPromise = null;
    }
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {},
    retryCount: number = 0
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

    // Handle 401 with automatic token refresh
    if (response.status === 401 && retryCount === 0) {
      const refreshed = await this.tryRefresh();
      if (refreshed) {
        // Retry the original request with new token
        return this.request<T>(endpoint, options, retryCount + 1);
      }
      // Refresh failed - trigger auth failure callback
      if (this.onAuthFailure) {
        this.onAuthFailure();
      }
      throw new Error("Session expired");
    }

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    // Handle 204 No Content responses (e.g., DELETE operations)
    if (response.status === 204) {
      return undefined as T;
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
    agent_config?: {
      model?: string;
      max_iterations?: number;
      max_tool_calls?: number;
      sub_agents?: Record<string, {
        system_prompt: string;
        model?: string;
        tools?: string[];
        max_iterations?: number;
        max_tool_calls?: number;
        description?: string;
      }>;
    };
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
      agent_config: {
        model?: string;
        max_iterations?: number;
        max_tool_calls?: number;
        sub_agents?: Record<string, {
          system_prompt: string;
          model?: string;
          tools?: string[];
          max_iterations?: number;
          max_tool_calls?: number;
          description?: string;
        }>;
      };
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

  // AI Providers
  async getAIProviders(params?: { include_inactive?: boolean }): Promise<AIProvidersResponse> {
    const searchParams = new URLSearchParams();
    if (params?.include_inactive !== undefined) {
      searchParams.set("include_inactive", String(params.include_inactive));
    }
    const query = searchParams.toString();
    try {
      return await this.request<AIProvidersResponse>(`/ai/providers${query ? `?${query}` : ""}`);
    } catch {
      return { providers: [], total: 0 };
    }
  }

  async getKnownProviders(): Promise<KnownProvidersResponse> {
    try {
      return await this.request<KnownProvidersResponse>("/ai/providers/known");
    } catch {
      return { providers: [] };
    }
  }

  async createAIProvider(data: CreateAIProviderRequest): Promise<AIProvider | null> {
    try {
      return await this.request<AIProvider>("/ai/providers", {
        method: "POST",
        body: JSON.stringify(data),
      });
    } catch {
      return null;
    }
  }

  async getAIProvider(providerId: string): Promise<AIProvider | null> {
    try {
      return await this.request<AIProvider>(`/ai/providers/${providerId}`);
    } catch {
      return null;
    }
  }

  async updateAIProvider(providerId: string, data: UpdateAIProviderRequest): Promise<AIProvider | null> {
    try {
      return await this.request<AIProvider>(`/ai/providers/${providerId}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      });
    } catch {
      return null;
    }
  }

  async deleteAIProvider(providerId: string): Promise<boolean> {
    try {
      await this.request(`/ai/providers/${providerId}`, {
        method: "DELETE",
      });
      return true;
    } catch {
      return false;
    }
  }

  async testAIProvider(providerId: string): Promise<AIProviderTestResult | null> {
    try {
      return await this.request<AIProviderTestResult>(`/ai/providers/${providerId}/test`, {
        method: "POST",
      });
    } catch {
      return null;
    }
  }

  async rotateAIProviderKey(providerId: string, newApiKey: string): Promise<AIProvider | null> {
    try {
      return await this.request<AIProvider>(`/ai/providers/${providerId}/rotate`, {
        method: "POST",
        body: JSON.stringify({ new_api_key: newApiKey }),
      });
    } catch {
      return null;
    }
  }

  // Usage API
  async getUsageSummary(days: number = 30): Promise<UsageSummary | null> {
    try {
      const response = await this.request<{ summary: UsageSummary }>(`/usage/summary?days=${days}`);
      return response.summary;
    } catch {
      return null;
    }
  }

  async getUsageByProvider(days: number = 30): Promise<UsageByProvider[]> {
    try {
      const response = await this.request<{ providers: UsageByProvider[] }>(`/usage/by-provider?days=${days}`);
      return response.providers;
    } catch {
      return [];
    }
  }

  async getUsageByModel(days: number = 30): Promise<UsageByModel[]> {
    try {
      const response = await this.request<{ models: UsageByModel[] }>(`/usage/by-model?days=${days}`);
      return response.models;
    } catch {
      return [];
    }
  }

  async getDailyUsage(days: number = 30): Promise<DailyUsage[]> {
    try {
      const response = await this.request<{ daily: DailyUsage[] }>(`/usage/daily?days=${days}`);
      return response.daily;
    } catch {
      return [];
    }
  }

  // Audit Logs (Admin only)
  async getAuditLogs(params?: {
    offset?: number;
    limit?: number;
    action?: string;
    actor_id?: string;
    resource_type?: string;
    success?: boolean;
  }): Promise<{ logs: any[]; total: number; limit: number; offset: number }> {
    const searchParams = new URLSearchParams();
    if (params?.offset !== undefined) searchParams.set("offset", String(params.offset));
    if (params?.limit !== undefined) searchParams.set("limit", String(params.limit));
    if (params?.action) searchParams.set("action", params.action);
    if (params?.actor_id) searchParams.set("actor_id", params.actor_id);
    if (params?.resource_type) searchParams.set("resource_type", params.resource_type);
    if (params?.success !== undefined) searchParams.set("success", String(params.success));

    const query = searchParams.toString();
    try {
      return await this.request(`/audit${query ? `?${query}` : ""}`);
    } catch {
      return { logs: [], total: 0, limit: params?.limit ?? 20, offset: params?.offset ?? 0 };
    }
  }

  // Model Pricing API
  async getModelPricingConfigs(includeGlobal: boolean = true): Promise<ModelPricingListResponse> {
    try {
      return await this.request<ModelPricingListResponse>(
        `/ai/pricing?include_global=${includeGlobal}`
      );
    } catch {
      return { pricing_configs: [], total: 0 };
    }
  }

  async getEffectiveModelPricing(): Promise<EffectiveModelPricingListResponse> {
    try {
      return await this.request<EffectiveModelPricingListResponse>("/ai/pricing/effective");
    } catch {
      return { models: [], total: 0 };
    }
  }

  async getDefaultModelPricing(): Promise<DefaultModelPricingListResponse> {
    try {
      return await this.request<DefaultModelPricingListResponse>("/ai/pricing/defaults");
    } catch {
      return { defaults: [], total: 0, fallback_input_price: 1.0, fallback_output_price: 2.0 };
    }
  }

  async createModelPricing(data: CreateModelPricingRequest): Promise<ModelPricingConfig | null> {
    try {
      return await this.request<ModelPricingConfig>("/ai/pricing", {
        method: "POST",
        body: JSON.stringify(data),
      });
    } catch {
      return null;
    }
  }

  async updateModelPricing(
    pricingId: string,
    data: UpdateModelPricingRequest
  ): Promise<ModelPricingConfig | null> {
    try {
      return await this.request<ModelPricingConfig>(`/ai/pricing/${pricingId}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      });
    } catch {
      return null;
    }
  }

  async deleteModelPricing(pricingId: string): Promise<boolean> {
    try {
      await this.request(`/ai/pricing/${pricingId}`, {
        method: "DELETE",
      });
      return true;
    } catch {
      return false;
    }
  }

  // Credentials
  async getCredentials(): Promise<CredentialsResponse> {
    try {
      return await this.request<CredentialsResponse>("/credentials");
    } catch {
      return emptyCredentialsResponse;
    }
  }

  async createCredential(data: CreateCredentialRequest): Promise<Credential | null> {
    try {
      return await this.request<Credential>("/credentials", {
        method: "POST",
        body: JSON.stringify(data),
      });
    } catch {
      return null;
    }
  }

  async updateCredential(name: string, data: UpdateCredentialRequest): Promise<Credential | null> {
    try {
      return await this.request<Credential>(`/credentials/${name}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      });
    } catch {
      return null;
    }
  }

  async deleteCredential(name: string): Promise<boolean> {
    try {
      await this.request(`/credentials/${name}`, {
        method: "DELETE",
      });
      return true;
    } catch {
      return false;
    }
  }

  // ── Agents API ──────────────────────────────────────────────

  async getAgents(params?: { status?: string; is_active?: boolean }): Promise<AgentsResponse> {
    const searchParams = new URLSearchParams();
    if (params?.status) searchParams.set("status", params.status);
    if (params?.is_active !== undefined) searchParams.set("is_active", String(params.is_active));
    const query = searchParams.toString();
    try {
      return await this.request<AgentsResponse>(`/agents${query ? `?${query}` : ""}`);
    } catch {
      return { agents: [], total: 0 };
    }
  }

  async getAgent(agentId: string): Promise<AgentType | null> {
    try {
      return await this.request<AgentType>(`/agents/${agentId}`);
    } catch {
      return null;
    }
  }

  async createAgent(data: CreateAgentRequest): Promise<AgentType | null> {
    try {
      return await this.request<AgentType>("/agents", {
        method: "POST",
        body: JSON.stringify(data),
      });
    } catch {
      return null;
    }
  }

  async updateAgent(agentId: string, data: Partial<CreateAgentRequest> & { status?: string; is_active?: boolean }): Promise<AgentType | null> {
    try {
      return await this.request<AgentType>(`/agents/${agentId}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      });
    } catch {
      return null;
    }
  }

  async deleteAgent(agentId: string): Promise<boolean> {
    try {
      await this.request(`/agents/${agentId}`, { method: "DELETE" });
      return true;
    } catch {
      return false;
    }
  }

  async getAgentStats(agentId: string, days: number = 30): Promise<AgentStats | null> {
    try {
      return await this.request<AgentStats>(`/agents/${agentId}/stats?days=${days}`);
    } catch {
      return null;
    }
  }

  async setAgentSkills(agentId: string, skillIds: string[]): Promise<{ enabled_skills: string[] } | null> {
    try {
      return await this.request(`/agents/${agentId}/skills`, {
        method: "PUT",
        body: JSON.stringify(skillIds),
      });
    } catch {
      return null;
    }
  }

  async getAgentSkills(agentId: string): Promise<{ enabled_skills: string[] }> {
    try {
      return await this.request(`/agents/${agentId}/skills`);
    } catch {
      return { enabled_skills: [] };
    }
  }

  // ── Function Skills API ─────────────────────────────────────

  async setFunctionSkills(functionId: string, skillIds: string[]): Promise<{ enabled_skills: string[] } | null> {
    try {
      return await this.request(`/functions/${functionId}/skills`, {
        method: "PUT",
        body: JSON.stringify(skillIds),
      });
    } catch {
      return null;
    }
  }

  async getFunctionSkills(functionId: string): Promise<{ enabled_skills: string[] }> {
    try {
      return await this.request(`/functions/${functionId}/skills`);
    } catch {
      return { enabled_skills: [] };
    }
  }

  // ── Tasks API ───────────────────────────────────────────────

  async getTasks(params?: {
    status?: string;
    priority?: string;
    assignee_user_id?: string;
    assignee_agent_id?: string;
    limit?: number;
    offset?: number;
  }): Promise<TasksResponse> {
    const searchParams = new URLSearchParams();
    if (params?.status) searchParams.set("status", params.status);
    if (params?.priority) searchParams.set("priority", params.priority);
    if (params?.assignee_user_id) searchParams.set("assignee_user_id", params.assignee_user_id);
    if (params?.assignee_agent_id) searchParams.set("assignee_agent_id", params.assignee_agent_id);
    if (params?.limit) searchParams.set("limit", String(params.limit));
    if (params?.offset) searchParams.set("offset", String(params.offset));
    const query = searchParams.toString();
    try {
      return await this.request<TasksResponse>(`/tasks${query ? `?${query}` : ""}`);
    } catch {
      return { tasks: [], total: 0 };
    }
  }

  async getTaskBoard(params?: {
    assignee_user_id?: string;
    assignee_agent_id?: string;
  }): Promise<TaskBoardResponse> {
    const searchParams = new URLSearchParams();
    if (params?.assignee_user_id) searchParams.set("assignee_user_id", params.assignee_user_id);
    if (params?.assignee_agent_id) searchParams.set("assignee_agent_id", params.assignee_agent_id);
    const query = searchParams.toString();
    try {
      return await this.request<TaskBoardResponse>(`/tasks/board${query ? `?${query}` : ""}`);
    } catch {
      return { columns: {}, total: 0 };
    }
  }

  async createTask(data: CreateTaskRequest): Promise<TaskType | null> {
    try {
      return await this.request<TaskType>("/tasks", {
        method: "POST",
        body: JSON.stringify(data),
      });
    } catch {
      return null;
    }
  }

  async getTask(taskId: string): Promise<TaskType | null> {
    try {
      return await this.request<TaskType>(`/tasks/${taskId}`);
    } catch {
      return null;
    }
  }

  async updateTask(taskId: string, data: Partial<CreateTaskRequest> & { run_id?: string }): Promise<TaskType | null> {
    try {
      return await this.request<TaskType>(`/tasks/${taskId}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      });
    } catch {
      return null;
    }
  }

  async deleteTask(taskId: string): Promise<boolean> {
    try {
      await this.request(`/tasks/${taskId}`, { method: "DELETE" });
      return true;
    } catch {
      return false;
    }
  }

  // ── Comments API ────────────────────────────────────────────

  async getComments(params: { task_id?: string; run_id?: string }): Promise<CommentsResponse> {
    const searchParams = new URLSearchParams();
    if (params.task_id) searchParams.set("task_id", params.task_id);
    if (params.run_id) searchParams.set("run_id", params.run_id);
    const query = searchParams.toString();
    try {
      return await this.request<CommentsResponse>(`/comments${query ? `?${query}` : ""}`);
    } catch {
      return { comments: [], total: 0 };
    }
  }

  async createComment(data: CreateCommentRequest): Promise<CommentType | null> {
    try {
      return await this.request<CommentType>("/comments", {
        method: "POST",
        body: JSON.stringify(data),
      });
    } catch {
      return null;
    }
  }

  async addReaction(commentId: string, emoji: string, userId: string): Promise<CommentType | null> {
    try {
      return await this.request<CommentType>(`/comments/${commentId}/reactions`, {
        method: "POST",
        body: JSON.stringify({ emoji, user_id: userId }),
      });
    } catch {
      return null;
    }
  }

  // ── Notifications API ───────────────────────────────────────

  async getNotifications(params?: {
    is_read?: boolean;
    is_archived?: boolean;
    limit?: number;
  }): Promise<NotificationsResponse> {
    const searchParams = new URLSearchParams();
    if (params?.is_read !== undefined) searchParams.set("is_read", String(params.is_read));
    if (params?.is_archived !== undefined) searchParams.set("is_archived", String(params.is_archived));
    if (params?.limit) searchParams.set("limit", String(params.limit));
    const query = searchParams.toString();
    try {
      return await this.request<NotificationsResponse>(`/notifications${query ? `?${query}` : ""}`);
    } catch {
      return { notifications: [], total: 0, unread_count: 0 };
    }
  }

  async markNotificationRead(notificationId: string): Promise<boolean> {
    try {
      await this.request(`/notifications/${notificationId}/read`, { method: "POST" });
      return true;
    } catch {
      return false;
    }
  }

  async markAllNotificationsRead(): Promise<boolean> {
    try {
      await this.request("/notifications/read-all", { method: "POST" });
      return true;
    } catch {
      return false;
    }
  }

  async archiveNotification(notificationId: string): Promise<boolean> {
    try {
      await this.request(`/notifications/${notificationId}/archive`, { method: "POST" });
      return true;
    } catch {
      return false;
    }
  }

  // ── Skills API ──────────────────────────────────────────────

  async getSkills(params?: { category?: string; search?: string }): Promise<SkillsResponse> {
    const searchParams = new URLSearchParams();
    if (params?.category) searchParams.set("category", params.category);
    if (params?.search) searchParams.set("search", params.search);
    const query = searchParams.toString();
    try {
      return await this.request<SkillsResponse>(`/skills${query ? `?${query}` : ""}`);
    } catch {
      return { skills: [], total: 0 };
    }
  }

  async createSkill(data: CreateSkillRequest): Promise<SkillType | null> {
    try {
      return await this.request<SkillType>("/skills", {
        method: "POST",
        body: JSON.stringify(data),
      });
    } catch {
      return null;
    }
  }

  async useSkill(skillId: string): Promise<{ function_config: Record<string, unknown>; tools_config: Record<string, unknown>[]; instructions?: string; system_prompt_append?: string } | null> {
    try {
      return await this.request(`/skills/${skillId}/use`, { method: "POST" });
    } catch {
      return null;
    }
  }

  // ── Skill Marketplace API ───────────────────────────────────

  async searchMarketplace(params: { q: string; source?: string; limit?: number }): Promise<MarketplaceSearchResponse> {
    const searchParams = new URLSearchParams();
    searchParams.set("q", params.q);
    if (params.source) searchParams.set("source", params.source);
    if (params.limit) searchParams.set("limit", String(params.limit));
    const query = searchParams.toString();
    try {
      return await this.request<MarketplaceSearchResponse>(`/skills/marketplace/search?${query}`);
    } catch {
      return { results: [], total: 0 };
    }
  }

  async previewSkill(repo: string, path: string = "SKILL.md"): Promise<SkillPreview | null> {
    const searchParams = new URLSearchParams();
    searchParams.set("repo", repo);
    searchParams.set("path", path);
    try {
      return await this.request<SkillPreview>(`/skills/marketplace/preview?${searchParams.toString()}`);
    } catch {
      return null;
    }
  }

  async importSkill(data: ImportSkillRequest): Promise<SkillType | null> {
    try {
      return await this.request<SkillType>("/skills/marketplace/import", {
        method: "POST",
        body: JSON.stringify(data),
      });
    } catch {
      return null;
    }
  }

  async refreshSkill(skillId: string): Promise<SkillType | null> {
    try {
      return await this.request<SkillType>(`/skills/${skillId}/refresh`, {
        method: "POST",
      });
    } catch {
      return null;
    }
  }

  // ── Cost Dashboard API ──────────────────────────────────────

  async getCostDashboard(days: number = 30): Promise<CostDashboardData> {
    const emptySummary: UsageSummary = { total_requests: 0, total_tokens: 0, prompt_tokens: 0, completion_tokens: 0, total_cost_usd: 0, avg_latency_ms: 0, period_start: "", period_end: "" };
    try {
      const [summary, byProvider, byModel, daily] = await Promise.all([
        this.getUsageSummary(days),
        this.getUsageByProvider(days),
        this.getUsageByModel(days),
        this.getDailyUsage(days),
      ]);
      return {
        summary: { summary: summary || emptySummary },
        by_provider: { providers: byProvider || [] },
        by_model: { models: byModel || [] },
        daily: { daily: daily || [] },
      };
    } catch {
      return {
        summary: { summary: emptySummary },
        by_provider: { providers: [] },
        by_model: { models: [] },
        daily: { daily: [] },
      };
    }
  }
}

const realApi = new FlowForgeAPI();

// Use mock API when NEXT_PUBLIC_USE_MOCK=true (local dev without backend).
// Dynamic import so mock code is tree-shaken out of production builds.
let _api: FlowForgeAPI = realApi;
if (process.env.NEXT_PUBLIC_USE_MOCK === "true") {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const { mockApi } = require("./mock-api") as { mockApi: unknown };
  _api = mockApi as FlowForgeAPI;
}
export const api = _api;
export default api;

// Re-export auth types for convenience
export type {
  User,
  UserWithPermissions,
  CreateUserRequest,
  UpdateUserRequest,
  UsersResponse,
} from "@/lib/auth/types";

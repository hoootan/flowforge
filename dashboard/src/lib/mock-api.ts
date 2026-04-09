/**
 * Mock API client for local development.
 * Implements the same interface as FlowForgeAPI but returns mock data.
 * Only used when NEXT_PUBLIC_USE_MOCK=true.
 */

import type {
  Run,
  RunWithSteps,
  RunsResponse,
  Function,
  FunctionsResponse,
  Tool,
  ToolsResponse,
  Event,
  EventsResponse,
  Stats,
  PendingApproval,
  ApprovalsResponse,
  ApiKey,
  ApiKeyCreated,
  ApiKeysResponse,
  CreateApiKeyRequest,
  AIProvider,
  AIProvidersResponse,
  KnownProvidersResponse,
  CreateAIProviderRequest,
  UpdateAIProviderRequest,
  AIProviderTestResult,
  UsageSummary,
  DailyUsage,
  UsageByProvider,
  UsageByModel,
  ModelPricingConfig,
  ModelPricingListResponse,
  EffectiveModelPricingListResponse,
  DefaultModelPricingListResponse,
  CreateModelPricingRequest,
  UpdateModelPricingRequest,
  Credential,
  CredentialsResponse,
  CreateCredentialRequest,
  UpdateCredentialRequest,
  AgentType,
  AgentsResponse,
  CreateAgentRequest,
  AgentStats,
  TaskType,
  TasksResponse,
  TaskBoardResponse,
  CreateTaskRequest,
  CommentType,
  CommentsResponse,
  CreateCommentRequest,
  NotificationType,
  NotificationsResponse,
  SkillType,
  SkillsResponse,
  CreateSkillRequest,
  ImportSkillRequest,
  MarketplaceSearchResponse,
  SkillPreview,
  CostDashboardData,
} from "./api";
import type {
  User,
  UserWithPermissions,
  CreateUserRequest,
  UpdateUserRequest,
  UsersResponse,
} from "@/lib/auth/types";
import {
  mockRuns,
  mockRunsWithSteps,
  mockFunctions,
  mockTools,
  mockEvents,
  mockStats,
  mockApprovals,
  mockUsers,
  mockCurrentUser,
  mockApiKeys,
  mockAIProviders,
  mockUsageSummary,
  mockDailyUsage,
  mockUsageByProvider,
  mockUsageByModel,
  mockAuditLogs,
  mockCredentials,
  mockModelPricingConfigs,
  mockEffectiveModelPricing,
  mockDefaultModelPricing,
  mockKnownProviders,
  mockAgents,
  mockTasks,
  mockComments,
  mockNotifications,
  mockSkills,
  mockMarketplaceResults,
} from "./mock-data";

// Simulate network latency
const delay = (ms = 80) =>
  new Promise<void>((resolve) => setTimeout(resolve, ms + Math.random() * 120));

// Deep clone to avoid mutation issues
const clone = <T>(obj: T): T => JSON.parse(JSON.stringify(obj));

// Mutable copies for write operations
let _runs = clone(mockRuns);
let _functions = clone(mockFunctions);
let _tools = clone(mockTools);
let _events = clone(mockEvents);
let _users = clone(mockUsers);
let _apiKeys = clone(mockApiKeys);
let _aiProviders = clone(mockAIProviders);
let _approvals = clone(mockApprovals);
let _credentials = clone(mockCredentials);
let _pricingConfigs = clone(mockModelPricingConfigs);
let _agents = clone(mockAgents);
let _tasks = clone(mockTasks);
let _comments = clone(mockComments);
let _notifications = clone(mockNotifications);
let _skills = clone(mockSkills);

let _taskSequence = _tasks.length;

class MockFlowForgeAPI {
  // Auth setup methods (no-ops for mock)
  setTokenProvider(_getToken: () => string | null) {}
  setRefreshHandler(_refreshFn: () => Promise<boolean>) {}
  setAuthFailureHandler(_handler: () => void) {}

  // ── Runs ─────────────────────────────────────────────────────────
  async getRuns(params?: {
    page?: number;
    page_size?: number;
    status?: string;
    function_id?: string;
  }): Promise<RunsResponse> {
    await delay();
    let filtered = clone(_runs);
    if (params?.status && params.status !== "all") {
      filtered = filtered.filter((r: Run) => r.status === params.status);
    }
    if (params?.function_id) {
      filtered = filtered.filter((r: Run) => r.function_id === params.function_id);
    }
    const page = params?.page ?? 1;
    const pageSize = params?.page_size ?? 50;
    const start = (page - 1) * pageSize;
    return {
      runs: filtered.slice(start, start + pageSize),
      total: filtered.length,
      page,
      page_size: pageSize,
    };
  }

  async getRun(runId: string): Promise<RunWithSteps | null> {
    await delay();
    if (mockRunsWithSteps[runId]) return clone(mockRunsWithSteps[runId]);
    const run = _runs.find((r: Run) => r.id === runId);
    if (!run) return null;
    return { ...clone(run), steps: [] };
  }

  async cancelRun(runId: string) {
    await delay();
    const run = _runs.find((r: Run) => r.id === runId);
    if (run) run.status = "cancelled";
    return { success: true, message: "Run cancelled", run_id: runId };
  }

  async replayRun(runId: string): Promise<RunWithSteps | null> {
    await delay();
    const run = _runs.find((r: Run) => r.id === runId);
    if (!run) return null;
    const newRun: Run = { ...clone(run), id: `run-replay-${Date.now()}`, status: "pending", attempt: 1, started_at: null, ended_at: null, created_at: new Date().toISOString() };
    _runs.unshift(newRun);
    return { ...newRun, steps: [] };
  }

  // ── Functions ────────────────────────────────────────────────────
  async getFunctions(params?: {
    trigger_type?: string;
    is_active?: boolean;
  }): Promise<FunctionsResponse> {
    await delay();
    let filtered = clone(_functions);
    if (params?.trigger_type) {
      filtered = filtered.filter((f: Function) => f.trigger_type === params.trigger_type);
    }
    if (params?.is_active !== undefined) {
      filtered = filtered.filter((f: Function) => f.is_active === params.is_active);
    }
    return { functions: filtered, total: filtered.length };
  }

  async getFunction(functionId: string): Promise<Function | null> {
    await delay();
    const fn = _functions.find((f: Function) => f.id === functionId || f.function_id === functionId);
    return fn ? clone(fn) : null;
  }

  async createInlineFunction(data: {
    id: string;
    name: string;
    trigger: { type: string; value: string; expression?: string };
    system_prompt: string;
    tools: string[];
    agent_config?: Record<string, unknown>;
    config?: Record<string, unknown>;
  }): Promise<Function | null> {
    await delay();
    const fn: Function = {
      id: `fn-${Date.now()}`,
      function_id: data.id,
      name: data.name,
      trigger_type: data.trigger.type as "event" | "cron" | "webhook",
      trigger_value: data.trigger.value,
      trigger_expression: data.trigger.expression ?? null,
      endpoint_url: null,
      is_inline: true,
      system_prompt: data.system_prompt,
      tools_config: data.tools,
      agent_config: (data.agent_config as Record<string, unknown>) ?? null,
      config: data.config ?? {},
      is_active: true,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    _functions.unshift(fn);
    return clone(fn);
  }

  async createWorkerFunction(data: {
    id: string;
    name: string;
    trigger: { type: string; value: string; expression?: string };
    endpoint_url: string;
    config?: Record<string, unknown>;
  }): Promise<Function | null> {
    await delay();
    const fn: Function = {
      id: `fn-${Date.now()}`,
      function_id: data.id,
      name: data.name,
      trigger_type: data.trigger.type as "event" | "cron" | "webhook",
      trigger_value: data.trigger.value,
      trigger_expression: data.trigger.expression ?? null,
      endpoint_url: data.endpoint_url,
      is_inline: false,
      system_prompt: null,
      tools_config: null,
      agent_config: null,
      config: data.config ?? {},
      is_active: true,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    _functions.unshift(fn);
    return clone(fn);
  }

  async updateFunction(functionId: string, data: Partial<Record<string, unknown>>): Promise<Function | null> {
    await delay();
    const fn = _functions.find((f: Function) => f.id === functionId || f.function_id === functionId);
    if (!fn) return null;
    Object.assign(fn, data, { updated_at: new Date().toISOString() });
    return clone(fn);
  }

  async deleteFunction(functionId: string): Promise<boolean> {
    await delay();
    const idx = _functions.findIndex((f: Function) => f.id === functionId || f.function_id === functionId);
    if (idx === -1) return false;
    _functions.splice(idx, 1);
    return true;
  }

  // ── Tools ────────────────────────────────────────────────────────
  async getTools(params?: {
    include_builtin?: boolean;
    is_active?: boolean;
    requires_approval?: boolean;
  }): Promise<ToolsResponse> {
    await delay();
    let filtered = clone(_tools);
    if (params?.include_builtin === false) {
      filtered = filtered.filter((t: Tool) => !t.is_builtin);
    }
    if (params?.is_active !== undefined) {
      filtered = filtered.filter((t: Tool) => t.is_active === params.is_active);
    }
    if (params?.requires_approval !== undefined) {
      filtered = filtered.filter((t: Tool) => t.requires_approval === params.requires_approval);
    }
    return { tools: filtered, total: filtered.length };
  }

  async getTool(toolName: string): Promise<Tool | null> {
    await delay();
    const tool = _tools.find((t: Tool) => t.name === toolName || t.id === toolName);
    return tool ? clone(tool) : null;
  }

  async createTool(data: {
    name: string;
    description: string;
    parameters: Record<string, unknown>;
    code?: string;
    requires_approval?: boolean;
    approval_timeout?: string;
  }): Promise<Tool | null> {
    await delay();
    const tool: Tool = {
      id: `tool-${Date.now()}`,
      name: data.name,
      description: data.description,
      parameters: data.parameters,
      tool_type: "custom",
      code: data.code ?? null,
      webhook_url: null,
      webhook_method: "POST",
      webhook_headers: null,
      is_builtin: false,
      requires_approval: data.requires_approval ?? false,
      approval_timeout: data.approval_timeout ?? null,
      is_active: true,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    _tools.push(tool);
    return clone(tool);
  }

  async updateTool(toolName: string, data: Partial<Record<string, unknown>>): Promise<Tool | null> {
    await delay();
    const tool = _tools.find((t: Tool) => t.name === toolName);
    if (!tool) return null;
    Object.assign(tool, data, { updated_at: new Date().toISOString() });
    return clone(tool);
  }

  async deleteTool(toolName: string): Promise<boolean> {
    await delay();
    const idx = _tools.findIndex((t: Tool) => t.name === toolName);
    if (idx === -1) return false;
    _tools.splice(idx, 1);
    return true;
  }

  // ── Events ───────────────────────────────────────────────────────
  async getEvents(params?: {
    page?: number;
    page_size?: number;
    name?: string;
  }): Promise<EventsResponse> {
    await delay();
    let filtered = clone(_events);
    if (params?.name) {
      filtered = filtered.filter((e: Event) => e.name.includes(params.name!));
    }
    const page = params?.page ?? 1;
    const pageSize = params?.page_size ?? 50;
    const start = (page - 1) * pageSize;
    return {
      events: filtered.slice(start, start + pageSize),
      total: filtered.length,
      page,
      page_size: pageSize,
    };
  }

  async getEvent(eventId: string): Promise<Event | null> {
    await delay();
    const evt = _events.find((e: Event) => e.id === eventId || e.event_id === eventId);
    return evt ? clone(evt) : null;
  }

  async sendEvent(data: {
    name: string;
    data: Record<string, unknown>;
    id?: string;
    user_id?: string;
    timestamp?: string;
  }): Promise<Event | null> {
    await delay();
    const evt: Event = {
      id: `evt-${Date.now()}`,
      event_id: data.id ?? `evt-ext-${Date.now()}`,
      name: data.name,
      data: data.data,
      timestamp: data.timestamp ?? new Date().toISOString(),
      received_at: new Date().toISOString(),
      user_id: data.user_id ?? null,
      processed: false,
    };
    _events.unshift(evt);
    return clone(evt);
  }

  // ── Stats ────────────────────────────────────────────────────────
  async getStats(): Promise<Stats> {
    await delay();
    return clone(mockStats);
  }

  // ── Health ───────────────────────────────────────────────────────
  async checkHealth(): Promise<boolean> {
    await delay(30);
    return true;
  }

  // ── Approvals ────────────────────────────────────────────────────
  async getApprovals(params?: {
    pending_only?: boolean;
  }): Promise<ApprovalsResponse> {
    await delay();
    let filtered = clone(_approvals);
    if (params?.pending_only) {
      filtered = filtered.filter((a: PendingApproval) => a.status === "pending");
    }
    return { approvals: filtered, total: filtered.length };
  }

  async approveToolCall(id: string) {
    await delay();
    const appr = _approvals.find((a: PendingApproval) => a.id === id);
    if (appr) appr.status = "approved";
    return { success: true, message: "Approved" };
  }

  async rejectToolCall(id: string, _reason: string) {
    await delay();
    const appr = _approvals.find((a: PendingApproval) => a.id === id);
    if (appr) appr.status = "rejected";
    return { success: true, message: "Rejected" };
  }

  // ── Users ────────────────────────────────────────────────────────
  async getUsers(_params?: { include_inactive?: boolean }): Promise<UsersResponse> {
    await delay();
    return { users: clone(_users), total: _users.length };
  }

  async getUser(userId: string): Promise<User | null> {
    await delay();
    const user = _users.find((u: User) => u.id === userId);
    return user ? clone(user) : null;
  }

  async createUser(data: CreateUserRequest): Promise<User | null> {
    await delay();
    const user: User = {
      id: `usr-${Date.now()}`,
      email: data.email,
      name: data.name,
      role: data.role,
      is_active: true,
      last_login_at: null,
      created_at: new Date().toISOString(),
    };
    _users.push(user);
    return clone(user);
  }

  async updateUser(userId: string, data: UpdateUserRequest): Promise<User | null> {
    await delay();
    const user = _users.find((u: User) => u.id === userId);
    if (!user) return null;
    Object.assign(user, data);
    return clone(user);
  }

  async deleteUser(userId: string): Promise<boolean> {
    await delay();
    const idx = _users.findIndex((u: User) => u.id === userId);
    if (idx === -1) return false;
    _users.splice(idx, 1);
    return true;
  }

  async getCurrentUser(): Promise<UserWithPermissions | null> {
    await delay();
    return clone(mockCurrentUser);
  }

  // ── API Keys ─────────────────────────────────────────────────────
  async getApiKeys(_params?: { include_revoked?: boolean }): Promise<ApiKeysResponse> {
    await delay();
    return { keys: clone(_apiKeys), total: _apiKeys.length };
  }

  async createApiKey(data: CreateApiKeyRequest): Promise<ApiKeyCreated | null> {
    await delay();
    const key: ApiKeyCreated = {
      id: `key-${Date.now()}`,
      name: data.name,
      key_prefix: `ff_${data.key_type ?? "test"}_${Math.random().toString(36).slice(2, 6)}`,
      key_type: data.key_type ?? "test",
      scopes: data.scopes ?? ["events:send", "events:read", "runs:read"],
      expires_at: data.expires_in_days ? new Date(Date.now() + data.expires_in_days * 86400000).toISOString() : null,
      last_used_at: null,
      is_active: true,
      created_at: new Date().toISOString(),
      key: `ff_${data.key_type ?? "test"}_${Math.random().toString(36).slice(2, 34)}`,
    };
    _apiKeys.push(key);
    return clone(key);
  }

  async revokeApiKey(keyId: string, _reason?: string): Promise<boolean> {
    await delay();
    const idx = _apiKeys.findIndex((k: ApiKey) => k.id === keyId);
    if (idx === -1) return false;
    _apiKeys[idx].is_active = false;
    return true;
  }

  // ── AI Providers ─────────────────────────────────────────────────
  async getAIProviders(_params?: { include_inactive?: boolean }): Promise<AIProvidersResponse> {
    await delay();
    return { providers: clone(_aiProviders), total: _aiProviders.length };
  }

  async getKnownProviders(): Promise<KnownProvidersResponse> {
    await delay();
    return { providers: clone(mockKnownProviders) };
  }

  async createAIProvider(data: CreateAIProviderRequest): Promise<AIProvider | null> {
    await delay();
    const provider: AIProvider = {
      id: `prov-${Date.now()}`,
      provider_name: data.provider_name,
      display_name: data.display_name ?? data.provider_name,
      api_key_prefix: data.api_key.slice(0, 8) + "...",
      auth_type: data.auth_type ?? "api_key",
      base_url: data.base_url ?? null,
      is_active: true,
      is_default: data.is_default ?? false,
      config: data.config ?? {},
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    _aiProviders.push(provider);
    return clone(provider);
  }

  async getAIProvider(providerId: string): Promise<AIProvider | null> {
    await delay();
    const p = _aiProviders.find((p: AIProvider) => p.id === providerId);
    return p ? clone(p) : null;
  }

  async updateAIProvider(providerId: string, data: UpdateAIProviderRequest): Promise<AIProvider | null> {
    await delay();
    const p = _aiProviders.find((p: AIProvider) => p.id === providerId);
    if (!p) return null;
    Object.assign(p, data, { updated_at: new Date().toISOString() });
    return clone(p);
  }

  async deleteAIProvider(providerId: string): Promise<boolean> {
    await delay();
    const idx = _aiProviders.findIndex((p: AIProvider) => p.id === providerId);
    if (idx === -1) return false;
    _aiProviders.splice(idx, 1);
    return true;
  }

  async testAIProvider(_providerId: string): Promise<AIProviderTestResult | null> {
    await delay(500);
    return { status: "healthy", message: "Connection successful", model_tested: "gpt-4o" };
  }

  async rotateAIProviderKey(providerId: string, newApiKey: string): Promise<AIProvider | null> {
    await delay();
    const p = _aiProviders.find((p: AIProvider) => p.id === providerId);
    if (!p) return null;
    p.api_key_prefix = newApiKey.slice(0, 8) + "...";
    p.updated_at = new Date().toISOString();
    return clone(p);
  }

  // ── Usage ────────────────────────────────────────────────────────
  async getUsageSummary(_days: number = 30): Promise<UsageSummary | null> {
    await delay();
    return clone(mockUsageSummary);
  }

  async getUsageByProvider(_days: number = 30): Promise<UsageByProvider[]> {
    await delay();
    return clone(mockUsageByProvider);
  }

  async getUsageByModel(_days: number = 30): Promise<UsageByModel[]> {
    await delay();
    return clone(mockUsageByModel);
  }

  async getDailyUsage(_days: number = 30): Promise<DailyUsage[]> {
    await delay();
    return clone(mockDailyUsage);
  }

  // ── Audit Logs ───────────────────────────────────────────────────
  async getAuditLogs(params?: {
    offset?: number;
    limit?: number;
    action?: string;
    actor_id?: string;
    resource_type?: string;
    success?: boolean;
  }): Promise<{ logs: any[]; total: number; limit: number; offset: number }> {
    await delay();
    let filtered = clone(mockAuditLogs);
    if (params?.action) {
      filtered = filtered.filter((l: any) => l.action === params.action);
    }
    if (params?.actor_id) {
      filtered = filtered.filter((l: any) => l.actor_id === params.actor_id);
    }
    if (params?.resource_type) {
      filtered = filtered.filter((l: any) => l.resource_type === params.resource_type);
    }
    if (params?.success !== undefined) {
      filtered = filtered.filter((l: any) => l.success === params.success);
    }
    const offset = params?.offset ?? 0;
    const limit = params?.limit ?? 20;
    return {
      logs: filtered.slice(offset, offset + limit),
      total: filtered.length,
      limit,
      offset,
    };
  }

  // ── Model Pricing ───────────────────────────────────────────────
  async getModelPricingConfigs(_includeGlobal: boolean = true): Promise<ModelPricingListResponse> {
    await delay();
    return { pricing_configs: clone(_pricingConfigs), total: _pricingConfigs.length };
  }

  async getEffectiveModelPricing(): Promise<EffectiveModelPricingListResponse> {
    await delay();
    return { models: clone(mockEffectiveModelPricing), total: mockEffectiveModelPricing.length };
  }

  async getDefaultModelPricing(): Promise<DefaultModelPricingListResponse> {
    await delay();
    return {
      defaults: clone(mockDefaultModelPricing),
      total: mockDefaultModelPricing.length,
      fallback_input_price: 1.0,
      fallback_output_price: 2.0,
    };
  }

  async createModelPricing(data: CreateModelPricingRequest): Promise<ModelPricingConfig | null> {
    await delay();
    const config: ModelPricingConfig = {
      id: `mp-${Date.now()}`,
      model_id: data.model_id,
      provider: data.provider,
      input_price_per_m: data.input_price_per_m,
      output_price_per_m: data.output_price_per_m,
      display_name: data.display_name ?? null,
      is_active: true,
      is_global: data.is_global ?? false,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    _pricingConfigs.push(config);
    return clone(config);
  }

  async updateModelPricing(pricingId: string, data: UpdateModelPricingRequest): Promise<ModelPricingConfig | null> {
    await delay();
    const config = _pricingConfigs.find((c: ModelPricingConfig) => c.id === pricingId);
    if (!config) return null;
    Object.assign(config, data, { updated_at: new Date().toISOString() });
    return clone(config);
  }

  async deleteModelPricing(pricingId: string): Promise<boolean> {
    await delay();
    const idx = _pricingConfigs.findIndex((c: ModelPricingConfig) => c.id === pricingId);
    if (idx === -1) return false;
    _pricingConfigs.splice(idx, 1);
    return true;
  }

  // ── Credentials ──────────────────────────────────────────────────
  async getCredentials(): Promise<CredentialsResponse> {
    await delay();
    return { credentials: clone(_credentials), total: _credentials.length };
  }

  async createCredential(data: CreateCredentialRequest): Promise<Credential | null> {
    await delay();
    const cred: Credential = {
      id: `cred-${Date.now()}`,
      name: data.name,
      credential_type: data.credential_type ?? "api_key",
      value_prefix: data.value.slice(0, 8) + "...",
      description: data.description ?? null,
      is_active: true,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    _credentials.push(cred);
    return clone(cred);
  }

  async updateCredential(name: string, data: UpdateCredentialRequest): Promise<Credential | null> {
    await delay();
    const cred = _credentials.find((c: Credential) => c.name === name);
    if (!cred) return null;
    if (data.value) cred.value_prefix = data.value.slice(0, 8) + "...";
    if (data.description !== undefined) cred.description = data.description;
    if (data.credential_type) cred.credential_type = data.credential_type;
    if (data.is_active !== undefined) cred.is_active = data.is_active;
    cred.updated_at = new Date().toISOString();
    return clone(cred);
  }

  async deleteCredential(name: string): Promise<boolean> {
    await delay();
    const idx = _credentials.findIndex((c: Credential) => c.name === name);
    if (idx === -1) return false;
    _credentials.splice(idx, 1);
    return true;
  }

  // ── Agents ──────────────────────────────────────────────────────
  async getAgents(params?: { status?: string; is_active?: boolean }): Promise<AgentsResponse> {
    await delay();
    let filtered = clone(_agents);
    if (params?.status) {
      filtered = filtered.filter((a: AgentType) => a.status === params.status);
    }
    if (params?.is_active !== undefined) {
      filtered = filtered.filter((a: AgentType) => a.is_active === params.is_active);
    }
    return { agents: filtered, total: filtered.length };
  }

  async getAgent(agentId: string): Promise<AgentType | null> {
    await delay();
    const agent = _agents.find((a: AgentType) => a.id === agentId);
    return agent ? clone(agent) : null;
  }

  async createAgent(data: CreateAgentRequest): Promise<AgentType | null> {
    await delay();
    const slug = data.name.toLowerCase().replace(/[^\w]+/g, "-").replace(/-+/g, "-").replace(/^-|-$/g, "");
    const agent: AgentType = {
      id: `agent-${Date.now()}`,
      name: data.name,
      slug,
      avatar_url: data.avatar_url ?? null,
      description: data.description ?? null,
      status: "idle",
      model: data.model ?? null,
      system_prompt: null,
      capabilities: data.capabilities ?? {},
      config: data.config ?? {},
      stats: { total_runs: 0, completed_runs: 0, failed_runs: 0, success_rate: 0, total_tokens: 0, total_cost_usd: 0 },
      enabled_skills: [],
      is_active: true,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    _agents.push(agent);
    return clone(agent);
  }

  async updateAgent(agentId: string, data: Partial<CreateAgentRequest> & { status?: string; is_active?: boolean }): Promise<AgentType | null> {
    await delay();
    const agent = _agents.find((a: AgentType) => a.id === agentId);
    if (!agent) return null;
    Object.assign(agent, data, { updated_at: new Date().toISOString() });
    return clone(agent);
  }

  async deleteAgent(agentId: string): Promise<boolean> {
    await delay();
    const idx = _agents.findIndex((a: AgentType) => a.id === agentId);
    if (idx === -1) return false;
    _agents.splice(idx, 1);
    return true;
  }

  async getAgentStats(agentId: string, days: number = 30): Promise<AgentStats | null> {
    await delay();
    const agent = _agents.find((a: AgentType) => a.id === agentId);
    if (!agent) return null;
    const stats = agent.stats as Record<string, number>;
    return {
      agent_id: agentId,
      total_runs: stats.total_runs ?? 0,
      completed_runs: stats.completed_runs ?? 0,
      failed_runs: stats.failed_runs ?? 0,
      success_rate: stats.success_rate ?? 0,
      total_tokens: stats.total_tokens ?? 0,
      total_cost_usd: stats.total_cost_usd ?? 0,
      avg_duration_ms: 4500,
      period_days: days,
    };
  }

  async setAgentSkills(agentId: string, skillIds: string[]): Promise<{ enabled_skills: string[] } | null> {
    await delay();
    const agent = _agents.find((a: AgentType) => a.id === agentId);
    if (!agent) return null;
    agent.enabled_skills = skillIds;
    return { enabled_skills: skillIds };
  }

  async getAgentSkills(agentId: string): Promise<{ enabled_skills: string[] }> {
    await delay();
    const agent = _agents.find((a: AgentType) => a.id === agentId);
    return { enabled_skills: agent?.enabled_skills ?? [] };
  }

  async setFunctionSkills(functionId: string, skillIds: string[]): Promise<{ enabled_skills: string[] } | null> {
    await delay();
    return { enabled_skills: skillIds };
  }

  async getFunctionSkills(functionId: string): Promise<{ enabled_skills: string[] }> {
    await delay();
    return { enabled_skills: [] };
  }

  // ── Tasks ───────────────────────────────────────────────────────
  async getTasks(params?: {
    status?: string;
    priority?: string;
    assignee_user_id?: string;
    assignee_agent_id?: string;
    limit?: number;
    offset?: number;
  }): Promise<TasksResponse> {
    await delay();
    let filtered = clone(_tasks);
    if (params?.status) {
      filtered = filtered.filter((t: TaskType) => t.status === params.status);
    }
    if (params?.priority) {
      filtered = filtered.filter((t: TaskType) => t.priority === params.priority);
    }
    if (params?.assignee_user_id) {
      filtered = filtered.filter((t: TaskType) => t.assignee_user_id === params.assignee_user_id);
    }
    if (params?.assignee_agent_id) {
      filtered = filtered.filter((t: TaskType) => t.assignee_agent_id === params.assignee_agent_id);
    }
    const offset = params?.offset ?? 0;
    const limit = params?.limit ?? 50;
    return { tasks: filtered.slice(offset, offset + limit), total: filtered.length };
  }

  async getTaskBoard(params?: {
    assignee_user_id?: string;
    assignee_agent_id?: string;
  }): Promise<TaskBoardResponse> {
    await delay();
    let filtered = clone(_tasks);
    if (params?.assignee_user_id) {
      filtered = filtered.filter((t: TaskType) => t.assignee_user_id === params.assignee_user_id);
    }
    if (params?.assignee_agent_id) {
      filtered = filtered.filter((t: TaskType) => t.assignee_agent_id === params.assignee_agent_id);
    }
    const columns: Record<string, TaskType[]> = {
      todo: [], in_progress: [], in_review: [], done: [], blocked: [], cancelled: [],
    };
    for (const task of filtered) {
      const col = task.status in columns ? task.status : "todo";
      columns[col].push(task);
    }
    return { columns, total: filtered.length };
  }

  async createTask(data: CreateTaskRequest): Promise<TaskType | null> {
    await delay();
    _taskSequence++;
    const task: TaskType = {
      id: `task-${Date.now()}`,
      identifier: `FF-${_taskSequence}`,
      title: data.title,
      description: data.description ?? null,
      status: (data.status as TaskType["status"]) ?? "todo",
      priority: (data.priority as TaskType["priority"]) ?? "none",
      labels: data.labels ?? [],
      assignee_type: data.assignee_agent_id ? "agent" : data.assignee_user_id ? "user" : null,
      assignee_user_id: data.assignee_user_id ?? null,
      assignee_agent_id: data.assignee_agent_id ?? null,
      assignee_user: null,
      assignee_agent: data.assignee_agent_id
        ? (() => {
            const a = _agents.find((a: AgentType) => a.id === data.assignee_agent_id);
            return a ? { id: a.id, name: a.name, slug: a.slug, avatar_url: a.avatar_url, status: a.status } : null;
          })()
        : null,
      created_by_user_id: null,
      parent_task_id: data.parent_task_id ?? null,
      function_id: data.function_id ?? null,
      run_id: null,
      sub_tasks_count: 0,
      comments_count: 0,
      metadata: data.metadata ?? {},
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    _tasks.unshift(task);
    return clone(task);
  }

  async getTask(taskId: string): Promise<TaskType | null> {
    await delay();
    const task = _tasks.find((t: TaskType) => t.id === taskId);
    return task ? clone(task) : null;
  }

  async updateTask(taskId: string, data: Partial<CreateTaskRequest> & { run_id?: string }): Promise<TaskType | null> {
    await delay();
    const task = _tasks.find((t: TaskType) => t.id === taskId);
    if (!task) return null;
    Object.assign(task, data, { updated_at: new Date().toISOString() });
    return clone(task);
  }

  async deleteTask(taskId: string): Promise<boolean> {
    await delay();
    const idx = _tasks.findIndex((t: TaskType) => t.id === taskId);
    if (idx === -1) return false;
    _tasks.splice(idx, 1);
    return true;
  }

  // ── Comments ────────────────────────────────────────────────────
  async getComments(params: { task_id?: string; run_id?: string }): Promise<CommentsResponse> {
    await delay();
    let filtered = clone(_comments);
    if (params.task_id) {
      filtered = filtered.filter((c: CommentType) => c.task_id === params.task_id);
    }
    if (params.run_id) {
      filtered = filtered.filter((c: CommentType) => c.run_id === params.run_id);
    }
    return { comments: filtered, total: filtered.length };
  }

  async createComment(data: CreateCommentRequest): Promise<CommentType | null> {
    await delay();
    const comment: CommentType = {
      id: `cmt-${Date.now()}`,
      task_id: data.task_id ?? null,
      run_id: data.run_id ?? null,
      author_type: data.author_agent_id ? "agent" : data.author_user_id ? "user" : "system",
      author_user_id: data.author_user_id ?? null,
      author_agent_id: data.author_agent_id ?? null,
      author: { type: "user", name: "Alex Rivera", email: "admin@flowforge.dev" },
      content: data.content,
      comment_type: data.comment_type ?? "comment",
      mentions: data.mentions ?? [],
      reactions: {},
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    _comments.push(comment);
    // Bump comment count on task if applicable
    if (data.task_id) {
      const task = _tasks.find((t: TaskType) => t.id === data.task_id);
      if (task) task.comments_count++;
    }
    return clone(comment);
  }

  async addReaction(commentId: string, emoji: string, userId: string): Promise<CommentType | null> {
    await delay();
    const comment = _comments.find((c: CommentType) => c.id === commentId);
    if (!comment) return null;
    if (!comment.reactions[emoji]) comment.reactions[emoji] = [];
    if (!comment.reactions[emoji].includes(userId)) comment.reactions[emoji].push(userId);
    return clone(comment);
  }

  // ── Notifications ───────────────────────────────────────────────
  async getNotifications(params?: {
    is_read?: boolean;
    is_archived?: boolean;
    limit?: number;
  }): Promise<NotificationsResponse> {
    await delay();
    let filtered = clone(_notifications);
    if (params?.is_read !== undefined) {
      filtered = filtered.filter((n: NotificationType) => n.is_read === params.is_read);
    }
    if (params?.is_archived !== undefined) {
      filtered = filtered.filter((n: NotificationType) => n.is_archived === params.is_archived);
    }
    const unread = _notifications.filter((n: NotificationType) => !n.is_read && !n.is_archived).length;
    const limit = params?.limit ?? 50;
    return { notifications: filtered.slice(0, limit), total: filtered.length, unread_count: unread };
  }

  async markNotificationRead(notificationId: string): Promise<boolean> {
    await delay();
    const notif = _notifications.find((n: NotificationType) => n.id === notificationId);
    if (!notif) return false;
    notif.is_read = true;
    return true;
  }

  async markAllNotificationsRead(): Promise<boolean> {
    await delay();
    for (const n of _notifications) n.is_read = true;
    return true;
  }

  async archiveNotification(notificationId: string): Promise<boolean> {
    await delay();
    const notif = _notifications.find((n: NotificationType) => n.id === notificationId);
    if (!notif) return false;
    notif.is_archived = true;
    notif.is_read = true;
    return true;
  }

  // ── Skills ──────────────────────────────────────────────────────
  async getSkills(params?: { category?: string; search?: string }): Promise<SkillsResponse> {
    await delay();
    let filtered = clone(_skills);
    if (params?.category) {
      filtered = filtered.filter((s: SkillType) => s.category === params.category);
    }
    if (params?.search) {
      const q = params.search.toLowerCase();
      filtered = filtered.filter((s: SkillType) =>
        s.name.toLowerCase().includes(q) || (s.description ?? "").toLowerCase().includes(q)
      );
    }
    return { skills: filtered, total: filtered.length };
  }

  async createSkill(data: CreateSkillRequest): Promise<SkillType | null> {
    await delay();
    const slug = data.name.toLowerCase().replace(/[^\w]+/g, "-").replace(/-+/g, "-").replace(/^-|-$/g, "");
    const skill: SkillType = {
      id: `skill-${Date.now()}`,
      name: data.name,
      slug,
      description: data.description ?? null,
      category: data.category ?? null,
      icon: data.icon ?? null,
      version: 1,
      function_config: data.function_config ?? {},
      tools_config: data.tools_config ?? [],
      usage_count: 0,
      is_builtin: false,
      is_active: true,
      tags: data.tags ?? [],
      source: "local",
      instructions: null,
      source_metadata: null,
      created_by_user_id: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    _skills.push(skill);
    return clone(skill);
  }

  async useSkill(skillId: string): Promise<{ function_config: Record<string, unknown>; tools_config: Record<string, unknown>[] } | null> {
    await delay();
    const skill = _skills.find((s: SkillType) => s.id === skillId);
    if (!skill) return null;
    skill.usage_count++;
    return { function_config: clone(skill.function_config), tools_config: clone(skill.tools_config) as Record<string, unknown>[] };
  }

  // ── Skill Marketplace ────────────────────────────────────────────
  async searchMarketplace(params: { q: string; source?: string; limit?: number }): Promise<MarketplaceSearchResponse> {
    await delay(200);
    const q = params.q.toLowerCase();
    const filtered = clone(mockMarketplaceResults).filter(
      (r: any) => r.name.toLowerCase().includes(q) || r.description.toLowerCase().includes(q) || r.repo.toLowerCase().includes(q)
    );
    return { results: filtered.slice(0, params.limit ?? 10), total: filtered.length };
  }

  async previewSkill(repo: string, _path: string = "SKILL.md"): Promise<SkillPreview | null> {
    await delay(300);
    // Return mock preview based on repo name
    const repoName = repo.split("/").pop() || "unknown";
    return {
      name: repoName.replace(/-/g, " ").replace(/\b\w/g, c => c.toUpperCase()),
      description: `A skill from ${repo}`,
      raw_content: `---\nname: ${repoName}\ndescription: A skill from ${repo}\n---\n\n# ${repoName.replace(/-/g, " ").replace(/\b\w/g, c => c.toUpperCase())}\n\n## Instructions\n\nThis is a preview of the SKILL.md content from the repository.\n\n## Best Practices\n\n- Follow the patterns described in this skill\n- Apply these guidelines consistently\n- Adapt to your project's specific needs`,
      frontmatter: { name: repoName, description: `A skill from ${repo}` },
      body: `# ${repoName.replace(/-/g, " ").replace(/\b\w/g, c => c.toUpperCase())}\n\n## Instructions\n\nThis is a preview of the SKILL.md content from the repository.\n\n## Best Practices\n\n- Follow the patterns described in this skill\n- Apply these guidelines consistently\n- Adapt to your project's specific needs`,
      repo,
      path: "SKILL.md",
    };
  }

  async importSkill(data: ImportSkillRequest): Promise<SkillType | null> {
    await delay(400);
    const repoName = data.repo.split("/").pop() || "imported-skill";
    const name = data.name_override || repoName.replace(/-/g, " ").replace(/\b\w/g, c => c.toUpperCase());
    const slug = repoName.toLowerCase().replace(/[^\w]+/g, "-");
    const skill: SkillType = {
      id: `skill-${Date.now()}`,
      name,
      slug,
      description: `Imported from ${data.repo}`,
      category: data.category ?? null,
      icon: null,
      version: 1,
      function_config: { system_prompt_append: true },
      tools_config: [],
      usage_count: 0,
      is_builtin: false,
      is_active: true,
      tags: data.tags ?? [],
      source: (data.source as "skills_sh" | "github") ?? "skills_sh",
      instructions: `# ${name}\n\nImported skill instructions from ${data.repo}.\n\n## Guidelines\n\n- Follow the patterns in this skill\n- Adapt to your project needs`,
      source_metadata: { repo: data.repo, path: data.path ?? "SKILL.md", fetched_at: new Date().toISOString(), external_id: data.external_id },
      created_by_user_id: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    _skills.push(skill);
    return clone(skill);
  }

  async refreshSkill(skillId: string): Promise<SkillType | null> {
    await delay(300);
    const skill = _skills.find((s: SkillType) => s.id === skillId);
    if (!skill || skill.source === "local") return null;
    skill.version++;
    skill.updated_at = new Date().toISOString();
    if (skill.source_metadata) (skill.source_metadata as any).fetched_at = new Date().toISOString();
    return clone(skill);
  }

  // ── Cost Dashboard ──────────────────────────────────────────────
  async getCostDashboard(days: number = 30): Promise<CostDashboardData> {
    await delay();
    return {
      summary: { summary: clone(mockUsageSummary) },
      by_provider: { providers: clone(mockUsageByProvider) },
      by_model: { models: clone(mockUsageByModel) },
      daily: { daily: clone(mockDailyUsage) },
    };
  }
}

export const mockApi = new MockFlowForgeAPI();

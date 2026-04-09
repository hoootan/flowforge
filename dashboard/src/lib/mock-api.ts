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
}

export const mockApi = new MockFlowForgeAPI();

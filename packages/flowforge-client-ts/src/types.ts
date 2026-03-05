/**
 * FlowForge TypeScript Client - Type Definitions
 */

// ============================================================================
// Result Type (Supabase-style)
// ============================================================================

export type Result<T> =
  | { data: T; error: null }
  | { data: null; error: FlowForgeError };

// ============================================================================
// Error
// ============================================================================

export class FlowForgeError extends Error {
  constructor(
    message: string,
    public status: number,
    public code?: string,
    public detail?: unknown
  ) {
    super(message);
    this.name = "FlowForgeError";
  }
}

// ============================================================================
// Core Types
// ============================================================================

export type RunStatus =
  | "pending"
  | "running"
  | "completed"
  | "failed"
  | "paused"
  | "cancelled";

export type StepType =
  | "run"
  | "sleep"
  | "ai"
  | "wait_for_event"
  | "invoke"
  | "send_event"
  | "agent";

export type StepStatus =
  | "pending"
  | "running"
  | "completed"
  | "failed"
  | "sleeping"
  | "waiting";

export type TriggerType = "event" | "cron" | "webhook";

export type ApprovalStatus = "pending" | "approved" | "rejected" | "expired";

// ============================================================================
// Domain Models
// ============================================================================

export interface Run {
  id: string;
  function_id: string;
  event_id: string | null;
  status: RunStatus;
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
  step_type: StepType;
  status: StepStatus;
  input: Record<string, unknown> | null;
  output: Record<string, unknown> | null;
  error: Record<string, unknown> | null;
  attempt: number;
  max_attempts: number;
  started_at: string | null;
  ended_at: string | null;
  created_at: string;
}

export interface RunWithSteps extends Run {
  steps: Step[];
}

export interface FlowForgeFunction {
  id: string;
  function_id: string;
  name: string;
  trigger_type: TriggerType;
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

export type ToolType = "custom" | "webhook" | "builtin";

export interface Tool {
  id: string;
  name: string;
  description: string;
  parameters: Record<string, unknown>;
  tool_type: ToolType;
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

export interface SendEventResponse extends Event {
  runs: Array<{ id: string; function_id: string }>;
}

export interface Approval {
  id: string;
  tool_call_id: string;
  tool_name: string;
  arguments: Record<string, unknown>;
  run_id: string;
  step_id: string;
  status: ApprovalStatus;
  created_at: string;
  timeout_at: string;
}

export interface Stats {
  runs: { total: number; completed: number; failed: number; running: number };
  functions: { total: number; active: number };
  events: { today: number; total: number };
  queue: { pending: number; running: number; scheduled: number };
}

export interface HealthStatus {
  status: "healthy" | "unhealthy";
  version?: string;
  uptime?: number;
}

// ============================================================================
// Filter Types (for type-safe query building)
// ============================================================================

export interface RunFilters {
  status: RunStatus;
  function_id: string;
}

export interface FunctionFilters {
  trigger_type: TriggerType;
  is_active: boolean;
}

export interface EventFilters {
  name: string;
  processed: boolean;
}

export interface ToolFilters {
  is_active: boolean;
  requires_approval: boolean;
  is_builtin: boolean;
}

export interface ApprovalFilters {
  status: ApprovalStatus;
}

// ============================================================================
// Input Types (for create/update operations)
// ============================================================================

export interface CreateFunctionInput {
  id: string;
  name: string;
  trigger_type: TriggerType;
  trigger_value: string;
  trigger_expression?: string;
  endpoint_url?: string;
  is_inline?: boolean;
  system_prompt?: string;
  tools_config?: string[];
  agent_config?: Record<string, unknown>;
  config?: Record<string, unknown>;
  is_active?: boolean;
}

export interface UpdateFunctionInput {
  name?: string;
  trigger_value?: string;
  trigger_expression?: string;
  endpoint_url?: string;
  system_prompt?: string;
  tools_config?: string[];
  agent_config?: Record<string, unknown>;
  config?: Record<string, unknown>;
  is_active?: boolean;
}

export interface CreateToolInput {
  name: string;
  description: string;
  parameters: Record<string, unknown>;
  tool_type?: ToolType;
  code?: string;
  webhook_url?: string;
  webhook_method?: string;
  webhook_headers?: Record<string, string>;
  requires_approval?: boolean;
  approval_timeout?: string;
  is_active?: boolean;
}

export interface UpdateToolInput {
  description?: string;
  parameters?: Record<string, unknown>;
  tool_type?: ToolType;
  code?: string;
  webhook_url?: string;
  webhook_method?: string;
  webhook_headers?: Record<string, string>;
  requires_approval?: boolean;
  approval_timeout?: string;
  is_active?: boolean;
}

export interface CreateCredentialInput {
  name: string;
  credential_type?: string;
  value: string;
  description?: string;
}

export interface UpdateCredentialInput {
  value?: string;
  description?: string;
  credential_type?: string;
  is_active?: boolean;
}

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

export interface SendEventInput {
  id?: string;
  user_id?: string;
  timestamp?: string;
}

// ============================================================================
// Auth Types
// ============================================================================

export type UserRole = "admin" | "member" | "viewer";

export interface User {
  id: string;
  email: string;
  name: string;
  role: UserRole;
  is_active: boolean;
  last_login_at: string | null;
  created_at: string;
}

export interface CreateUserInput {
  email: string;
  password: string;
  name: string;
  role: UserRole;
}

export interface UpdateUserInput {
  email?: string;
  name?: string;
  role?: UserRole;
  is_active?: boolean;
}

export interface UsersResponse {
  users: User[];
  total: number;
}

// ============================================================================
// API Key Types
// ============================================================================

export type ApiKeyType = "live" | "test" | "ro";

export interface ApiKey {
  id: string;
  name: string;
  key_prefix: string;
  key_type: ApiKeyType;
  scopes: string[];
  expires_at: string | null;
  last_used_at: string | null;
  is_active: boolean;
  created_at: string;
}

export interface ApiKeyCreated extends ApiKey {
  key: string; // Only returned once on creation
}

export interface CreateApiKeyInput {
  name: string;
  key_type?: ApiKeyType;
  scopes?: string[];
  expires_in_days?: number;
}

export interface ApiKeysResponse {
  keys: ApiKey[];
  total: number;
}

export interface ApiKeyFilters {
  include_revoked: boolean;
}

// ============================================================================
// Client Options
// ============================================================================

export interface ClientOptions {
  /**
   * API key for authentication.
   * Uses the X-FlowForge-API-Key header.
   * Format: ff_{type}_{random} (e.g., ff_live_a1b2c3d4...)
   *
   * Key types:
   * - ff_live_xxx - Production keys with full access
   * - ff_test_xxx - Test/development keys
   * - ff_ro_xxx   - Read-only keys
   */
  apiKey?: string;

  /** Custom fetch implementation (for testing or custom environments) */
  fetch?: typeof fetch;

  /**
   * Request timeout in milliseconds.
   * Requests will be aborted if they exceed this duration.
   * Default: 30000 (30 seconds)
   */
  timeout?: number;

  /**
   * Retry configuration for failed requests.
   */
  retry?: {
    /** Maximum number of retry attempts (default: 3) */
    maxAttempts?: number;
    /** Base delay in milliseconds for exponential backoff (default: 1000) */
    baseDelay?: number;
    /** Maximum delay in milliseconds (default: 30000) */
    maxDelay?: number;
    /** Whether to retry on timeout errors (default: true) */
    retryOnTimeout?: boolean;
    /** HTTP status codes that should trigger a retry (default: [429, 500, 502, 503, 504]) */
    retryableStatuses?: number[];
  };
}

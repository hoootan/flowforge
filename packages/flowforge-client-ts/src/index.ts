/**
 * FlowForge TypeScript Client
 *
 * A type-safe, Supabase-style client for interacting with FlowForge server.
 *
 * @example
 * ```ts
 * import { createClient } from 'flowforge-client';
 *
 * const ff = createClient('http://localhost:8000');
 *
 * // Send an event - returns { data, error }, never throws
 * const { data, error } = await ff.events.send('order/created', {
 *   order_id: '123',
 *   customer: 'Alice',
 *   total: 99.99
 * });
 *
 * if (error) {
 *   console.error('Failed to send event:', error.message);
 * } else {
 *   console.log('Triggered runs:', data.runs);
 * }
 *
 * // Query runs with type-safe filters
 * const { data: runs } = await ff.runs
 *   .select()
 *   .eq('status', 'completed')
 *   .order('created_at', 'desc')
 *   .limit(10)
 *   .execute();
 *
 * // Wait for a run to complete
 * const { data: run } = await ff.runs.waitFor('run-id', { timeout: 60000 });
 * ```
 */

// Main client factory
export { createClient } from "./client";
export type { FlowForgeClient } from "./client";

// Types
export {
  FlowForgeError,
  type Result,
  type RunStatus,
  type StepType,
  type StepStatus,
  type TriggerType,
  type ApprovalStatus,
  type Run,
  type Step,
  type RunWithSteps,
  type FlowForgeFunction,
  type Tool,
  type Event,
  type SendEventResponse,
  type Approval,
  type Stats,
  type HealthStatus,
  type RunFilters,
  type FunctionFilters,
  type EventFilters,
  type ToolType,
  type ToolFilters,
  type ApprovalFilters,
  type SubAgentConfig,
  type AgentConfig,
  type CreateFunctionInput,
  type UpdateFunctionInput,
  type CreateToolInput,
  type UpdateToolInput,
  type Credential,
  type CredentialsResponse,
  type CreateCredentialInput,
  type UpdateCredentialInput,
  type SendEventInput,
  type ClientOptions,
  // User types (admin API key required)
  type UserRole,
  type User,
  type CreateUserInput,
  type UpdateUserInput,
  type UsersResponse,
  // API Key types
  type ApiKeyType,
  type ApiKey,
  type ApiKeyCreated,
  type CreateApiKeyInput,
  type ApiKeysResponse,
  type ApiKeyFilters,
  // SSE streaming types
  type RunEventType,
  type RunStreamEvent,
  type StreamOptions,
  type StreamConfig,
} from "./types";

// Query builder (for advanced usage)
export { QueryBuilder, type OrderDirection, type QueryParams } from "./builder";

// Resources (for advanced usage / extension)
export { AgentsResource, type Agent, type CreateAgentInput, type AgentListResponse } from "./resources/agents";
export { EventsResource } from "./resources/events";
export { RunsResource } from "./resources/runs";
export { FunctionsResource } from "./resources/functions";
export { ToolsResource } from "./resources/tools";
export { TasksResource, type Task, type CreateTaskInput, type TaskListResponse, type TaskBoardResponse } from "./resources/tasks";
export { SkillsResource, type Skill, type CreateSkillInput, type SkillListResponse } from "./resources/skills";
export { ApprovalsResource } from "./resources/approvals";
export { HealthResource } from "./resources/health";
export { UsersResource } from "./resources/users";
export { ApiKeysResource } from "./resources/api-keys";
export { CredentialsResource } from "./resources/credentials";

// SSE streaming
export { RunStream } from "./stream";

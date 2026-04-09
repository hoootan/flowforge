/**
 * FlowForge TypeScript Client - Main Client Factory
 */

import type { ClientOptions, Result, FlowForgeError } from "./types";
import { AgentsResource } from "./resources/agents";
import { EventsResource } from "./resources/events";
import { RunsResource } from "./resources/runs";
import { FunctionsResource } from "./resources/functions";
import { ToolsResource } from "./resources/tools";
import { ApprovalsResource } from "./resources/approvals";
import { HealthResource } from "./resources/health";
import { UsersResource } from "./resources/users";
import { ApiKeysResource } from "./resources/api-keys";
import { CredentialsResource } from "./resources/credentials";
import { TasksResource } from "./resources/tasks";
import { SkillsResource } from "./resources/skills";

/**
 * FlowForge client instance with typed resource accessors.
 */
export interface FlowForgeClient {
  /** Agents resource - manage AI agent identities */
  agents: AgentsResource;
  /** Events resource - send and query events */
  events: EventsResource;
  /** Runs resource - query and manage workflow runs */
  runs: RunsResource;
  /** Functions resource - manage workflow functions */
  functions: FunctionsResource;
  /** Tools resource - manage AI tools */
  tools: ToolsResource;
  /** Tasks resource - Kanban task management */
  tasks: TasksResource;
  /** Skills resource - reusable function templates */
  skills: SkillsResource;
  /** Approvals resource - human-in-the-loop approvals */
  approvals: ApprovalsResource;
  /** Health resource - server health and stats */
  health: HealthResource;
  /** Users resource - authentication and user management */
  users: UsersResource;
  /** API Keys resource - manage API key authentication */
  apiKeys: ApiKeysResource;
  /** Credentials resource - manage encrypted service credentials */
  credentials: CredentialsResource;
}

/**
 * Create a FlowForge client instance.
 *
 * @param baseUrl - The base URL of the FlowForge server
 * @param options - Optional client configuration
 * @returns A FlowForge client instance
 *
 * @example Basic usage
 * ```ts
 * import { createClient } from 'flowforge-client';
 *
 * const ff = createClient('http://localhost:8000');
 *
 * // Send an event
 * const { data, error } = await ff.events.send('order/created', {
 *   order_id: '123',
 *   customer: 'Alice'
 * });
 * ```
 *
 * @example With API key
 * ```ts
 * const ff = createClient('http://localhost:8000', {
 *   apiKey: process.env.FLOWFORGE_API_KEY  // ff_live_xxx
 * });
 * ```
 */
// Default timeout: 30 seconds
const DEFAULT_TIMEOUT = 30000;

/**
 * Combine multiple AbortSignals into one that aborts when any of them abort.
 */
function anySignal(signals: AbortSignal[]): AbortSignal {
  const controller = new AbortController();

  for (const signal of signals) {
    if (signal.aborted) {
      controller.abort(signal.reason);
      return controller.signal;
    }

    signal.addEventListener(
      "abort",
      () => controller.abort(signal.reason),
      { once: true }
    );
  }

  return controller.signal;
}

// Default retry configuration
const DEFAULT_RETRY = {
  maxAttempts: 3,
  baseDelay: 1000,
  maxDelay: 30000,
  retryOnTimeout: true,
  retryableStatuses: [429, 500, 502, 503, 504],
};

/**
 * Calculate delay with exponential backoff and jitter.
 */
function calculateBackoff(
  attempt: number,
  baseDelay: number,
  maxDelay: number
): number {
  const exponentialDelay = baseDelay * Math.pow(2, attempt);
  const jitter = 0.5 + Math.random(); // 0.5 to 1.5
  return Math.min(exponentialDelay * jitter, maxDelay);
}

/**
 * Sleep for a given number of milliseconds.
 */
function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Create a FlowForge client instance.
 *
 * @param baseUrl - The base URL of the FlowForge server
 * @param options - Optional client configuration
 * @returns A FlowForge client instance
 *
 * @example Basic usage
 * ```ts
 * import { createClient } from 'flowforge-client';
 *
 * const ff = createClient('http://localhost:8000');
 *
 * // Send an event
 * const { data, error } = await ff.events.send('order/created', {
 *   order_id: '123',
 *   customer: 'Alice'
 * });
 * ```
 *
 * @example With API key and timeout
 * ```ts
 * const ff = createClient('http://localhost:8000', {
 *   apiKey: process.env.FLOWFORGE_API_KEY,
 *   timeout: 60000, // 60 seconds
 *   retry: {
 *     maxAttempts: 5,
 *     baseDelay: 2000,
 *   }
 * });
 * ```
 */
export function createClient(
  baseUrl: string,
  options: ClientOptions = {}
): FlowForgeClient {
  const normalizedBaseUrl = baseUrl.replace(/\/$/, "");
  const fetchFn = options.fetch || globalThis.fetch;
  const timeout = options.timeout ?? DEFAULT_TIMEOUT;
  const retryConfig = { ...DEFAULT_RETRY, ...options.retry };

  /**
   * Execute a single request with timeout.
   */
  async function executeRequest<T>(
    method: string,
    path: string,
    body: unknown | undefined,
    signal?: AbortSignal
  ): Promise<Result<T>> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };

    // API key authentication
    if (options.apiKey) {
      headers["X-FlowForge-API-Key"] = options.apiKey;
    }

    // Create timeout abort controller
    const timeoutController = new AbortController();
    const timeoutId = setTimeout(() => timeoutController.abort(), timeout);

    // Combine with external signal if provided
    const combinedSignal = signal
      ? anySignal([signal, timeoutController.signal])
      : timeoutController.signal;

    try {
      const response = await fetchFn(`${normalizedBaseUrl}/api/v1${path}`, {
        method,
        headers,
        body: body ? JSON.stringify(body) : undefined,
        signal: combinedSignal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        const errorBody = await response.json().catch(() => ({}));
        const error = {
          message: errorBody.detail || `HTTP ${response.status}`,
          status: response.status,
          code: errorBody.code,
          detail: errorBody,
          name: "FlowForgeError",
        } as FlowForgeError;

        return { data: null, error };
      }

      // Handle 204 No Content (e.g. DELETE responses)
      if (response.status === 204) {
        return { data: { success: true, message: "Deleted" } as T, error: null };
      }

      const data = await response.json();
      return { data: data as T, error: null };
    } catch (err) {
      clearTimeout(timeoutId);

      // Check if aborted due to timeout
      if (timeoutController.signal.aborted) {
        const error = {
          message: `Request timed out after ${timeout}ms`,
          status: 0,
          code: "TIMEOUT",
          detail: { timeout },
          name: "FlowForgeError",
        } as FlowForgeError;
        return { data: null, error };
      }

      // Check if aborted by external signal
      if (signal?.aborted) {
        const error = {
          message: "Request was cancelled",
          status: 0,
          code: "CANCELLED",
          detail: err,
          name: "FlowForgeError",
        } as FlowForgeError;
        return { data: null, error };
      }

      const error = {
        message: err instanceof Error ? err.message : "Network error",
        status: 0,
        code: "NETWORK_ERROR",
        detail: err,
        name: "FlowForgeError",
      } as FlowForgeError;

      return { data: null, error };
    }
  }

  /**
   * Check if an error is retryable.
   */
  function isRetryable(error: FlowForgeError): boolean {
    // Retry on timeout if configured
    if (error.code === "TIMEOUT" && retryConfig.retryOnTimeout) {
      return true;
    }

    // Retry on network errors
    if (error.code === "NETWORK_ERROR") {
      return true;
    }

    // Retry on specific HTTP statuses
    if (retryConfig.retryableStatuses.includes(error.status)) {
      return true;
    }

    return false;
  }

  /**
   * Internal request function that returns Result<T>.
   * Never throws - all errors are captured in the error field.
   * Implements retry with exponential backoff.
   */
  async function request<T>(
    method: string,
    path: string,
    body?: unknown
  ): Promise<Result<T>> {
    let lastError: FlowForgeError | null = null;

    for (let attempt = 0; attempt < retryConfig.maxAttempts; attempt++) {
      const result = await executeRequest<T>(method, path, body);

      // Success - return immediately
      if (result.data !== null) {
        return result;
      }

      lastError = result.error;

      // Don't retry if not retryable or last attempt
      if (!lastError || !isRetryable(lastError) || attempt === retryConfig.maxAttempts - 1) {
        return result;
      }

      // Calculate backoff delay
      const delay = calculateBackoff(
        attempt,
        retryConfig.baseDelay,
        retryConfig.maxDelay
      );

      await sleep(delay);
    }

    // Should never reach here, but just in case
    return {
      data: null,
      error: lastError || ({
        message: "Unknown error",
        status: 0,
        code: "UNKNOWN",
        name: "FlowForgeError",
      } as FlowForgeError),
    };
  }

  return {
    agents: new AgentsResource(request),
    events: new EventsResource(request),
    runs: new RunsResource(request, {
      baseUrl: normalizedBaseUrl,
      apiKey: options.apiKey,
      fetchFn,
    }),
    functions: new FunctionsResource(request),
    tools: new ToolsResource(request),
    tasks: new TasksResource(request),
    skills: new SkillsResource(request),
    approvals: new ApprovalsResource(request),
    health: new HealthResource(request),
    users: new UsersResource(request),
    apiKeys: new ApiKeysResource(request),
    credentials: new CredentialsResource(request),
  };
}

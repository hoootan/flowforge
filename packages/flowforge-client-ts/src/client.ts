/**
 * FlowForge TypeScript Client - Main Client Factory
 */

import type { ClientOptions, Result, FlowForgeError } from "./types";
import { EventsResource } from "./resources/events";
import { RunsResource } from "./resources/runs";
import { FunctionsResource } from "./resources/functions";
import { ToolsResource } from "./resources/tools";
import { ApprovalsResource } from "./resources/approvals";
import { HealthResource } from "./resources/health";
import { UsersResource } from "./resources/users";
import { ApiKeysResource } from "./resources/api-keys";

/**
 * FlowForge client instance with typed resource accessors.
 */
export interface FlowForgeClient {
  /** Events resource - send and query events */
  events: EventsResource;
  /** Runs resource - query and manage workflow runs */
  runs: RunsResource;
  /** Functions resource - manage workflow functions */
  functions: FunctionsResource;
  /** Tools resource - manage AI tools */
  tools: ToolsResource;
  /** Approvals resource - human-in-the-loop approvals */
  approvals: ApprovalsResource;
  /** Health resource - server health and stats */
  health: HealthResource;
  /** Users resource - authentication and user management */
  users: UsersResource;
  /** API Keys resource - manage API key authentication */
  apiKeys: ApiKeysResource;
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
export function createClient(
  baseUrl: string,
  options: ClientOptions = {}
): FlowForgeClient {
  const normalizedBaseUrl = baseUrl.replace(/\/$/, "");
  const fetchFn = options.fetch || globalThis.fetch;

  /**
   * Internal request function that returns Result<T>.
   * Never throws - all errors are captured in the error field.
   */
  async function request<T>(
    method: string,
    path: string,
    body?: unknown
  ): Promise<Result<T>> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };

    // API key authentication
    if (options.apiKey) {
      headers["X-FlowForge-API-Key"] = options.apiKey;
    }

    try {
      const response = await fetchFn(`${normalizedBaseUrl}/api/v1${path}`, {
        method,
        headers,
        body: body ? JSON.stringify(body) : undefined,
      });

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

      const data = await response.json();
      return { data: data as T, error: null };
    } catch (err) {
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

  return {
    events: new EventsResource(request),
    runs: new RunsResource(request),
    functions: new FunctionsResource(request),
    tools: new ToolsResource(request),
    approvals: new ApprovalsResource(request),
    health: new HealthResource(request),
    users: new UsersResource(request),
    apiKeys: new ApiKeysResource(request),
  };
}

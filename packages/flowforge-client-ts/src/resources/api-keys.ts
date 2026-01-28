/**
 * FlowForge TypeScript Client - API Keys Resource
 */

import type {
  Result,
  ApiKey,
  ApiKeyCreated,
  ApiKeysResponse,
  CreateApiKeyInput,
} from "../types";

type RequestFn = <T>(
  method: string,
  path: string,
  body?: unknown
) => Promise<Result<T>>;

/**
 * API Keys resource for managing API key authentication.
 */
export class ApiKeysResource {
  constructor(private request: RequestFn) {}

  /**
   * List all API keys for the tenant.
   *
   * @param options - Filter options
   * @returns List of API keys (without the actual key values)
   *
   * @example
   * ```ts
   * const { data } = await ff.apiKeys.list();
   * data?.keys.forEach(key => {
   *   console.log(`${key.name}: ${key.key_prefix}... (${key.key_type})`);
   * });
   * ```
   */
  async list(options?: {
    includeRevoked?: boolean;
  }): Promise<Result<ApiKeysResponse>> {
    const params = new URLSearchParams();
    if (options?.includeRevoked) {
      params.set("include_revoked", "true");
    }
    const query = params.toString();
    return this.request<ApiKeysResponse>(
      "GET",
      `/auth/keys${query ? `?${query}` : ""}`
    );
  }

  /**
   * Get an API key by ID.
   *
   * @param keyId - API key ID
   * @returns API key details (without the actual key value)
   */
  async get(keyId: string): Promise<Result<ApiKey>> {
    return this.request<ApiKey>("GET", `/auth/keys/${keyId}`);
  }

  /**
   * Create a new API key.
   *
   * @param input - API key configuration
   * @returns Created API key WITH the actual key value (only returned once!)
   *
   * @example
   * ```ts
   * const { data, error } = await ff.apiKeys.create({
   *   name: 'Production API Key',
   *   key_type: 'live',
   *   scopes: ['events:send', 'runs:read']
   * });
   *
   * if (data) {
   *   // IMPORTANT: Store this key - it won't be shown again!
   *   console.log('New API key:', data.key);  // ff_live_a1b2c3...
   * }
   * ```
   */
  async create(input: CreateApiKeyInput): Promise<Result<ApiKeyCreated>> {
    return this.request<ApiKeyCreated>("POST", "/auth/keys", input);
  }

  /**
   * Revoke an API key.
   *
   * @param keyId - API key ID
   * @param reason - Optional reason for revocation
   * @returns Success message
   *
   * @example
   * ```ts
   * const { error } = await ff.apiKeys.revoke('key-id', 'Compromised');
   * if (!error) {
   *   console.log('Key revoked successfully');
   * }
   * ```
   */
  async revoke(
    keyId: string,
    reason?: string
  ): Promise<Result<{ message: string }>> {
    return this.request<{ message: string }>(
      "DELETE",
      `/auth/keys/${keyId}`,
      reason ? { reason } : undefined
    );
  }
}

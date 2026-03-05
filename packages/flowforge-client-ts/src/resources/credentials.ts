/**
 * FlowForge TypeScript Client - Credentials Resource
 */

import type { RequestFn } from "../builder";
import type {
  Credential,
  CredentialsResponse,
  CreateCredentialInput,
  UpdateCredentialInput,
  Result,
} from "../types";

export class CredentialsResource {
  constructor(private request: RequestFn) {}

  /**
   * List all credentials for the tenant.
   * Values are never returned — only masked prefixes.
   */
  async list(): Promise<Result<CredentialsResponse>> {
    return this.request<CredentialsResponse>("GET", "/credentials");
  }

  /**
   * Get a credential by name (metadata only, no decrypted value).
   */
  async get(name: string): Promise<Result<Credential>> {
    return this.request<Credential>("GET", `/credentials/${name}`);
  }

  /**
   * Create a new encrypted credential.
   */
  async create(input: CreateCredentialInput): Promise<Result<Credential>> {
    return this.request<Credential>("POST", "/credentials", input);
  }

  /**
   * Update an existing credential.
   * If value is provided, it will be re-encrypted.
   */
  async update(
    name: string,
    input: UpdateCredentialInput
  ): Promise<Result<Credential>> {
    return this.request<Credential>("PATCH", `/credentials/${name}`, input);
  }

  /**
   * Delete a credential.
   */
  async delete(
    name: string
  ): Promise<Result<{ success: boolean; message: string }>> {
    return this.request<{ success: boolean; message: string }>(
      "DELETE",
      `/credentials/${name}`
    );
  }
}

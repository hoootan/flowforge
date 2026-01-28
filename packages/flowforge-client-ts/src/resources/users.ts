/**
 * FlowForge TypeScript Client - Users Resource
 *
 * Note: The SDK uses API key authentication only (X-FlowForge-API-Key header).
 * User/password login is only available through the dashboard.
 */

import type {
  Result,
  User,
  UsersResponse,
  CreateUserInput,
  UpdateUserInput,
} from "../types";

type RequestFn = <T>(
  method: string,
  path: string,
  body?: unknown
) => Promise<Result<T>>;

/**
 * Users resource for user management (admin API key required).
 *
 * Note: This resource requires an admin-level API key.
 * User/password login is only available through the dashboard.
 */
export class UsersResource {
  constructor(private request: RequestFn) {}

  /**
   * List all users (admin only).
   *
   * @param options - Filter options
   * @returns List of users
   *
   * @example
   * ```ts
   * const { data } = await ff.users.list({ includeInactive: true });
   * console.log('Total users:', data?.total);
   * ```
   */
  async list(options?: {
    includeInactive?: boolean;
  }): Promise<Result<UsersResponse>> {
    const params = new URLSearchParams();
    if (options?.includeInactive) {
      params.set("include_inactive", "true");
    }
    const query = params.toString();
    return this.request<UsersResponse>(
      "GET",
      `/users${query ? `?${query}` : ""}`
    );
  }

  /**
   * Get a user by ID (admin only).
   *
   * @param userId - User ID
   * @returns User details
   */
  async get(userId: string): Promise<Result<User>> {
    return this.request<User>("GET", `/users/${userId}`);
  }

  /**
   * Create a new user (admin only).
   *
   * @param input - User details
   * @returns Created user
   *
   * @example
   * ```ts
   * const { data, error } = await ff.users.create({
   *   email: 'user@example.com',
   *   password: 'securepassword',
   *   name: 'John Doe',
   *   role: 'member'
   * });
   * ```
   */
  async create(input: CreateUserInput): Promise<Result<User>> {
    return this.request<User>("POST", "/users", input);
  }

  /**
   * Update a user (admin only).
   *
   * @param userId - User ID
   * @param input - Fields to update
   * @returns Updated user
   */
  async update(userId: string, input: UpdateUserInput): Promise<Result<User>> {
    return this.request<User>("PATCH", `/users/${userId}`, input);
  }

  /**
   * Delete a user (admin only).
   *
   * @param userId - User ID
   * @returns Success message
   */
  async delete(userId: string): Promise<Result<{ message: string }>> {
    return this.request<{ message: string }>("DELETE", `/users/${userId}`);
  }
}

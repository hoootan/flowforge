/**
 * FlowForge TypeScript Client - Functions Resource
 */

import { QueryBuilder, type RequestFn } from "../builder";
import type {
  FlowForgeFunction,
  FunctionFilters,
  CreateFunctionInput,
  UpdateFunctionInput,
  Result,
} from "../types";

export class FunctionsResource {
  constructor(private request: RequestFn) {}

  /**
   * Get a function by ID.
   *
   * @example
   * ```ts
   * const { data: fn } = await ff.functions.get('my-function');
   * console.log(fn.name, fn.is_active);
   * ```
   */
  async get(functionId: string): Promise<Result<FlowForgeFunction>> {
    return this.request<FlowForgeFunction>("GET", `/functions/${functionId}`);
  }

  /**
   * Start building a query to select functions.
   *
   * @example
   * ```ts
   * const { data: fns } = await ff.functions
   *   .select()
   *   .eq('is_active', true)
   *   .eq('trigger_type', 'event')
   *   .execute();
   * ```
   */
  select(): QueryBuilder<FlowForgeFunction, FunctionFilters> {
    return new QueryBuilder<FlowForgeFunction, FunctionFilters>(
      this.request,
      "/functions",
      "functions"
    );
  }

  /**
   * Create a new function.
   *
   * @example
   * ```ts
   * const { data: fn, error } = await ff.functions.create({
   *   id: 'order-processor',
   *   name: 'Order Processor',
   *   trigger_type: 'event',
   *   trigger_value: 'order/created',
   *   endpoint_url: 'http://localhost:3000/api/workflows/order',
   * });
   * ```
   */
  async create(input: CreateFunctionInput): Promise<Result<FlowForgeFunction>> {
    return this.request<FlowForgeFunction>("POST", "/functions", input);
  }

  /**
   * Update an existing function.
   *
   * @example
   * ```ts
   * const { error } = await ff.functions.update('my-function', {
   *   is_active: false
   * });
   * ```
   */
  async update(
    functionId: string,
    input: UpdateFunctionInput
  ): Promise<Result<FlowForgeFunction>> {
    return this.request<FlowForgeFunction>(
      "PATCH",
      `/functions/${functionId}`,
      input
    );
  }

  /**
   * Delete a function.
   *
   * @example
   * ```ts
   * const { error } = await ff.functions.delete('my-function');
   * if (error) console.error('Failed to delete:', error.message);
   * ```
   */
  async delete(
    functionId: string
  ): Promise<Result<{ success: boolean; message: string }>> {
    return this.request<{ success: boolean; message: string }>(
      "DELETE",
      `/functions/${functionId}`
    );
  }
}

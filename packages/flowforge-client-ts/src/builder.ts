/**
 * FlowForge TypeScript Client - Query Builder
 *
 * Generic, type-safe query builder with chainable methods.
 */

import type { Result, FlowForgeError } from "./types";

export type OrderDirection = "asc" | "desc";

export interface QueryParams {
  filters: Record<string, unknown>;
  orderBy?: string;
  orderDir?: OrderDirection;
  limitValue?: number;
  offsetValue?: number;
}

export type RequestFn = <T>(
  method: string,
  path: string,
  body?: unknown
) => Promise<Result<T>>;

/**
 * Generic query builder for type-safe filtering and pagination.
 *
 * @example
 * ```ts
 * const { data } = await builder
 *   .eq('status', 'completed')
 *   .order('created_at', 'desc')
 *   .limit(10)
 *   .execute();
 * ```
 */
export class QueryBuilder<T, Filters> {
  protected params: QueryParams = { filters: {} };

  constructor(
    protected request: RequestFn,
    protected basePath: string,
    protected responseKey: string
  ) {}

  /**
   * Filter by exact match.
   */
  eq<K extends keyof Filters>(field: K, value: Filters[K]): this {
    this.params.filters[field as string] = value;
    return this;
  }

  /**
   * Order results by a field.
   */
  order<K extends keyof T>(field: K, direction: OrderDirection = "asc"): this {
    this.params.orderBy = field as string;
    this.params.orderDir = direction;
    return this;
  }

  /**
   * Limit the number of results.
   */
  limit(n: number): this {
    this.params.limitValue = n;
    return this;
  }

  /**
   * Skip the first n results (for pagination).
   */
  offset(n: number): this {
    this.params.offsetValue = n;
    return this;
  }

  /**
   * Build query string from params.
   */
  protected buildQueryString(): string {
    const searchParams = new URLSearchParams();

    for (const [key, value] of Object.entries(this.params.filters)) {
      if (value !== undefined && value !== null) {
        searchParams.set(key, String(value));
      }
    }

    if (this.params.orderBy) {
      searchParams.set("order_by", this.params.orderBy);
      searchParams.set("order_dir", this.params.orderDir || "asc");
    }

    if (this.params.limitValue !== undefined) {
      searchParams.set("limit", String(this.params.limitValue));
    }

    if (this.params.offsetValue !== undefined) {
      searchParams.set("offset", String(this.params.offsetValue));
    }

    const query = searchParams.toString();
    return query ? `?${query}` : "";
  }

  /**
   * Execute the query and return multiple results.
   */
  async execute(): Promise<Result<T[]>> {
    const path = `${this.basePath}${this.buildQueryString()}`;
    const result = await this.request<Record<string, unknown>>("GET", path);

    if (result.error) {
      return { data: null, error: result.error };
    }

    // Extract items from response using the response key
    const items = (result.data[this.responseKey] as T[]) || [];
    return { data: items, error: null };
  }

  /**
   * Execute the query and return a single result.
   * Returns an error if no results found.
   */
  async single(): Promise<Result<T>> {
    const result = await this.limit(1).execute();

    if (result.error) {
      return { data: null, error: result.error };
    }

    if (result.data.length === 0) {
      const error = {
        message: "No results found",
        status: 404,
        name: "FlowForgeError",
      } as FlowForgeError;
      return { data: null, error };
    }

    return { data: result.data[0], error: null };
  }
}

/**
 * FlowForge TypeScript Client - Health Resource
 */

import type { RequestFn } from "../builder";
import type { HealthStatus, Stats, Result } from "../types";

export class HealthResource {
  constructor(private request: RequestFn) {}

  /**
   * Check if the server is healthy.
   *
   * @example
   * ```ts
   * const { data: healthy, error } = await ff.health.check();
   * if (healthy) console.log('Server is healthy');
   * else console.error('Server is unhealthy:', error?.message);
   * ```
   */
  async check(): Promise<Result<boolean>> {
    const result = await this.request<HealthStatus>("GET", "/health");

    if (result.error) {
      return { data: false, error: null };
    }

    return { data: result.data.status === "healthy", error: null };
  }

  /**
   * Get server statistics.
   *
   * @example
   * ```ts
   * const { data: stats } = await ff.health.stats();
   * console.log('Total runs:', stats.runs.total);
   * console.log('Active functions:', stats.functions.active);
   * ```
   */
  async stats(): Promise<Result<Stats>> {
    return this.request<Stats>("GET", "/stats");
  }
}

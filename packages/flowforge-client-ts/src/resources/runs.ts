/**
 * FlowForge TypeScript Client - Runs Resource
 */

import { QueryBuilder, type RequestFn } from "../builder";
import type { Run, RunWithSteps, RunFilters, Result, FlowForgeError } from "../types";

export class RunsResource {
  constructor(private request: RequestFn) {}

  /**
   * Get a run by ID, including its steps.
   *
   * @example
   * ```ts
   * const { data: run } = await ff.runs.get('run-id');
   * console.log(run.status, run.steps);
   * ```
   */
  async get(runId: string): Promise<Result<RunWithSteps>> {
    return this.request<RunWithSteps>("GET", `/runs/${runId}`);
  }

  /**
   * Start building a query to select runs.
   *
   * @example
   * ```ts
   * const { data: runs } = await ff.runs
   *   .select()
   *   .eq('status', 'completed')
   *   .order('created_at', 'desc')
   *   .limit(10)
   *   .execute();
   * ```
   */
  select(): QueryBuilder<Run, RunFilters> {
    return new QueryBuilder<Run, RunFilters>(this.request, "/runs", "runs");
  }

  /**
   * Cancel a running workflow.
   *
   * @example
   * ```ts
   * const { error } = await ff.runs.cancel('run-id');
   * if (error) console.error('Failed to cancel:', error.message);
   * ```
   */
  async cancel(
    runId: string
  ): Promise<Result<{ success: boolean; message: string }>> {
    return this.request<{ success: boolean; message: string }>(
      "POST",
      `/runs/${runId}/cancel`
    );
  }

  /**
   * Replay a completed or failed run.
   *
   * @example
   * ```ts
   * const { data: newRun } = await ff.runs.replay('run-id');
   * console.log('New run ID:', newRun.id);
   * ```
   */
  async replay(runId: string): Promise<Result<RunWithSteps>> {
    return this.request<RunWithSteps>("POST", `/runs/${runId}/replay`);
  }

  /**
   * Wait for a run to complete (polling).
   *
   * @example
   * ```ts
   * const { data: completedRun, error } = await ff.runs.waitFor('run-id', {
   *   timeout: 60000
   * });
   * if (error) console.error('Timeout or error:', error.message);
   * else console.log('Run completed with status:', completedRun.status);
   * ```
   */
  async waitFor(
    runId: string,
    options?: { timeout?: number; interval?: number }
  ): Promise<Result<RunWithSteps>> {
    const timeout = options?.timeout ?? 60000;
    const interval = options?.interval ?? 1000;
    const start = Date.now();

    while (Date.now() - start < timeout) {
      const result = await this.get(runId);

      if (result.error) {
        return result;
      }

      if (["completed", "failed", "cancelled"].includes(result.data.status)) {
        return result;
      }

      await new Promise((resolve) => setTimeout(resolve, interval));
    }

    const error = {
      message: "Timeout waiting for run to complete",
      status: 408,
      name: "FlowForgeError",
    } as FlowForgeError;

    return { data: null, error };
  }
}

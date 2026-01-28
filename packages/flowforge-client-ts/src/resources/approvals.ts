/**
 * FlowForge TypeScript Client - Approvals Resource
 *
 * Human-in-the-loop approval management for tool calls.
 */

import { QueryBuilder, type RequestFn } from "../builder";
import type { Approval, ApprovalFilters, Result } from "../types";

export class ApprovalsResource {
  constructor(private request: RequestFn) {}

  /**
   * Get an approval by ID.
   *
   * @example
   * ```ts
   * const { data: approval } = await ff.approvals.get('approval-id');
   * console.log(approval.tool_name, approval.status);
   * ```
   */
  async get(approvalId: string): Promise<Result<Approval>> {
    return this.request<Approval>("GET", `/approvals/${approvalId}`);
  }

  /**
   * Start building a query to select approvals.
   *
   * @example
   * ```ts
   * const { data: pending } = await ff.approvals
   *   .select()
   *   .eq('status', 'pending')
   *   .execute();
   * ```
   */
  select(): QueryBuilder<Approval, ApprovalFilters> {
    return new QueryBuilder<Approval, ApprovalFilters>(
      this.request,
      "/approvals",
      "approvals"
    );
  }

  /**
   * Approve a pending tool call.
   *
   * @example
   * ```ts
   * const { error } = await ff.approvals.approve('approval-id');
   * if (error) console.error('Failed to approve:', error.message);
   * ```
   *
   * @example With modified arguments
   * ```ts
   * const { error } = await ff.approvals.approve('approval-id', {
   *   modifiedArguments: { amount: 50 } // Override the original amount
   * });
   * ```
   */
  async approve(
    approvalId: string,
    options?: { modifiedArguments?: Record<string, unknown> }
  ): Promise<Result<{ success: boolean; message: string }>> {
    return this.request<{ success: boolean; message: string }>(
      "POST",
      `/approvals/${approvalId}/approve`,
      {
        modified_arguments: options?.modifiedArguments,
      }
    );
  }

  /**
   * Reject a pending tool call.
   *
   * @example
   * ```ts
   * const { error } = await ff.approvals.reject('approval-id', 'Too risky');
   * if (error) console.error('Failed to reject:', error.message);
   * ```
   */
  async reject(
    approvalId: string,
    reason: string
  ): Promise<Result<{ success: boolean; message: string }>> {
    return this.request<{ success: boolean; message: string }>(
      "POST",
      `/approvals/${approvalId}/reject`,
      { reason }
    );
  }
}

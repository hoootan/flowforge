/**
 * FlowForge TypeScript Client - Tools Resource
 */

import { QueryBuilder, type RequestFn } from "../builder";
import type {
  Tool,
  ToolFilters,
  CreateToolInput,
  UpdateToolInput,
  Result,
} from "../types";

export class ToolsResource {
  constructor(private request: RequestFn) {}

  /**
   * Get a tool by name.
   *
   * @example
   * ```ts
   * const { data: tool } = await ff.tools.get('send-email');
   * console.log(tool.description, tool.requires_approval);
   * ```
   */
  async get(toolName: string): Promise<Result<Tool>> {
    return this.request<Tool>("GET", `/tools/${toolName}`);
  }

  /**
   * Start building a query to select tools.
   *
   * @example
   * ```ts
   * const { data: tools } = await ff.tools
   *   .select()
   *   .eq('requires_approval', true)
   *   .eq('is_active', true)
   *   .execute();
   * ```
   */
  select(): QueryBuilder<Tool, ToolFilters> {
    return new QueryBuilder<Tool, ToolFilters>(this.request, "/tools", "tools");
  }

  /**
   * Create a new tool.
   *
   * @example
   * ```ts
   * const { data: tool, error } = await ff.tools.create({
   *   name: 'send-email',
   *   description: 'Send an email to a recipient',
   *   parameters: {
   *     type: 'object',
   *     properties: {
   *       to: { type: 'string', description: 'Recipient email' },
   *       subject: { type: 'string', description: 'Email subject' },
   *       body: { type: 'string', description: 'Email body' },
   *     },
   *     required: ['to', 'subject', 'body'],
   *   },
   *   requires_approval: true,
   * });
   * ```
   */
  async create(input: CreateToolInput): Promise<Result<Tool>> {
    return this.request<Tool>("POST", "/tools", input);
  }

  /**
   * Update an existing tool.
   *
   * @example
   * ```ts
   * const { error } = await ff.tools.update('send-email', {
   *   requires_approval: false
   * });
   * ```
   */
  async update(toolName: string, input: UpdateToolInput): Promise<Result<Tool>> {
    return this.request<Tool>("PATCH", `/tools/${toolName}`, input);
  }

  /**
   * Delete a tool.
   *
   * @example
   * ```ts
   * const { error } = await ff.tools.delete('my-tool');
   * if (error) console.error('Failed to delete:', error.message);
   * ```
   */
  async delete(
    toolName: string
  ): Promise<Result<{ success: boolean; message: string }>> {
    return this.request<{ success: boolean; message: string }>(
      "DELETE",
      `/tools/${toolName}`
    );
  }
}

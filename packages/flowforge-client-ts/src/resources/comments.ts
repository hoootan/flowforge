/**
 * FlowForge TypeScript Client - Comments Resource
 */

import type { RequestFn } from "../builder";
import type { Result } from "../types";

export interface Comment {
  id: string;
  task_id: string | null;
  run_id: string | null;
  author_type: "user" | "agent" | "system";
  author_user_id: string | null;
  author_agent_id: string | null;
  author: { id?: string; name: string; email?: string; avatar_url?: string | null; type: string } | null;
  content: string;
  comment_type: string;
  mentions: unknown[];
  reactions: Record<string, string[]>;
  created_at: string;
  updated_at: string;
}

export interface CreateCommentInput {
  task_id?: string;
  run_id?: string;
  content: string;
  comment_type?: string;
  author_user_id?: string;
  author_agent_id?: string;
}

export interface CommentListResponse {
  comments: Comment[];
  total: number;
}

export class CommentsResource {
  constructor(private request: RequestFn) {}

  async list(params: { task_id?: string; run_id?: string; limit?: number }): Promise<Result<CommentListResponse>> {
    const query = new URLSearchParams();
    if (params.task_id) query.set("task_id", params.task_id);
    if (params.run_id) query.set("run_id", params.run_id);
    if (params.limit) query.set("limit", String(params.limit));
    return this.request<CommentListResponse>("GET", `/comments?${query.toString()}`);
  }

  async create(data: CreateCommentInput): Promise<Result<Comment>> {
    return this.request<Comment>("POST", "/comments", data);
  }

  async addReaction(commentId: string, emoji: string, userId: string): Promise<Result<Comment>> {
    return this.request<Comment>("POST", `/comments/${commentId}/reactions`, { emoji, user_id: userId });
  }

  async delete(commentId: string): Promise<Result<{ success: boolean }>> {
    return this.request<{ success: boolean }>("DELETE", `/comments/${commentId}`);
  }
}

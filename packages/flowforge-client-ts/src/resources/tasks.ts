/**
 * FlowForge TypeScript Client - Tasks Resource
 */

import type { RequestFn } from "../builder";
import type { Result } from "../types";

export interface Task {
  id: string;
  identifier: string;
  title: string;
  description: string | null;
  status: "todo" | "in_progress" | "in_review" | "done" | "blocked" | "cancelled";
  priority: "urgent" | "high" | "medium" | "low" | "none";
  labels: string[];
  assignee_type: "user" | "agent" | null;
  assignee_user_id: string | null;
  assignee_agent_id: string | null;
  assignee_user: { id: string; name: string; email: string } | null;
  assignee_agent: { id: string; name: string; slug: string; avatar_url: string | null; status: string } | null;
  created_by_user_id: string | null;
  parent_task_id: string | null;
  function_id: string | null;
  run_id: string | null;
  sub_tasks_count: number;
  comments_count: number;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface CreateTaskInput {
  title: string;
  description?: string;
  status?: string;
  priority?: string;
  labels?: string[];
  assignee_user_id?: string;
  assignee_agent_id?: string;
  parent_task_id?: string;
  function_id?: string;
}

export interface TaskListResponse {
  tasks: Task[];
  total: number;
}

export interface TaskBoardResponse {
  columns: Record<string, Task[]>;
  total: number;
}

export class TasksResource {
  constructor(private request: RequestFn) {}

  async list(params?: {
    status?: string;
    priority?: string;
    assignee_user_id?: string;
    assignee_agent_id?: string;
    limit?: number;
    offset?: number;
  }): Promise<Result<TaskListResponse>> {
    const query = new URLSearchParams();
    if (params?.status) query.set("status", params.status);
    if (params?.priority) query.set("priority", params.priority);
    if (params?.assignee_user_id) query.set("assignee_user_id", params.assignee_user_id);
    if (params?.assignee_agent_id) query.set("assignee_agent_id", params.assignee_agent_id);
    if (params?.limit) query.set("limit", String(params.limit));
    if (params?.offset) query.set("offset", String(params.offset));
    const qs = query.toString();
    return this.request<TaskListResponse>("GET", `/tasks${qs ? `?${qs}` : ""}`);
  }

  async board(params?: {
    assignee_user_id?: string;
    assignee_agent_id?: string;
  }): Promise<Result<TaskBoardResponse>> {
    const query = new URLSearchParams();
    if (params?.assignee_user_id) query.set("assignee_user_id", params.assignee_user_id);
    if (params?.assignee_agent_id) query.set("assignee_agent_id", params.assignee_agent_id);
    const qs = query.toString();
    return this.request<TaskBoardResponse>("GET", `/tasks/board${qs ? `?${qs}` : ""}`);
  }

  async get(taskId: string): Promise<Result<Task>> {
    return this.request<Task>("GET", `/tasks/${taskId}`);
  }

  async create(data: CreateTaskInput): Promise<Result<Task>> {
    return this.request<Task>("POST", "/tasks", data);
  }

  async update(taskId: string, data: Partial<CreateTaskInput> & { run_id?: string }): Promise<Result<Task>> {
    return this.request<Task>("PATCH", `/tasks/${taskId}`, data);
  }

  async delete(taskId: string): Promise<Result<{ success: boolean }>> {
    return this.request<{ success: boolean }>("DELETE", `/tasks/${taskId}`);
  }
}

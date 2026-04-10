/**
 * FlowForge TypeScript Client - Notifications Resource
 */

import type { RequestFn } from "../builder";
import type { Result } from "../types";

export interface Notification {
  id: string;
  notification_type: string;
  title: string;
  body: string | null;
  resource_type: string | null;
  resource_id: string | null;
  data: Record<string, unknown>;
  is_read: boolean;
  is_archived: boolean;
  created_at: string;
}

export interface NotificationListResponse {
  notifications: Notification[];
  total: number;
  unread_count: number;
}

export class NotificationsResource {
  constructor(private request: RequestFn) {}

  async list(params?: { is_read?: boolean; is_archived?: boolean; limit?: number }): Promise<Result<NotificationListResponse>> {
    const query = new URLSearchParams();
    if (params?.is_read !== undefined) query.set("is_read", String(params.is_read));
    if (params?.is_archived !== undefined) query.set("is_archived", String(params.is_archived));
    if (params?.limit) query.set("limit", String(params.limit));
    const qs = query.toString();
    return this.request<NotificationListResponse>("GET", `/notifications${qs ? `?${qs}` : ""}`);
  }

  async markRead(notificationId: string): Promise<Result<{ success: boolean }>> {
    return this.request<{ success: boolean }>("POST", `/notifications/${notificationId}/read`);
  }

  async markAllRead(): Promise<Result<{ success: boolean }>> {
    return this.request<{ success: boolean }>("POST", "/notifications/read-all");
  }

  async archive(notificationId: string): Promise<Result<{ success: boolean }>> {
    return this.request<{ success: boolean }>("POST", `/notifications/${notificationId}/archive`);
  }
}

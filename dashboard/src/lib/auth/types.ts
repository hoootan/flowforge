/**
 * Auth types for FlowForge dashboard.
 */

export type UserRole = "admin" | "member" | "viewer";

export interface User {
  id: string;
  email: string;
  name: string;
  role: UserRole;
  is_active: boolean;
  last_login_at: string | null;
  created_at: string;
}

export interface UserWithPermissions extends User {
  tenant_id: string;
  permissions: {
    can_manage_users: boolean;
    can_create_resources: boolean;
    is_admin: boolean;
    is_member: boolean;
    is_viewer: boolean;
  };
  totp_enabled?: boolean;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  refresh_expires_in: number;
  expires_at: string;
  user: User;
}

export interface AuthState {
  user: UserWithPermissions | null;
  token: string | null;
  refreshToken: string | null;
  tokenExpiresAt: number | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}

export interface CreateUserRequest {
  email: string;
  password: string;
  name: string;
  role: UserRole;
}

export interface UpdateUserRequest {
  email?: string;
  name?: string;
  role?: UserRole;
  is_active?: boolean;
}

export interface ChangePasswordRequest {
  current_password: string;
  new_password: string;
}

export interface UsersResponse {
  users: User[];
  total: number;
}

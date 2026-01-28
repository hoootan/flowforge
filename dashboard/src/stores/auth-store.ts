"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";
import type {
  AuthState,
  LoginCredentials,
  LoginResponse,
  UserWithPermissions,
} from "@/lib/auth/types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

interface AuthStore extends AuthState {
  // Actions
  login: (credentials: LoginCredentials) => Promise<{ success: boolean; error?: string }>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
  setToken: (token: string | null) => void;
  setUser: (user: UserWithPermissions | null) => void;
  setLoading: (loading: boolean) => void;
}

export const useAuthStore = create<AuthStore>()(
  persist(
    (set, get) => ({
      // Initial state
      user: null,
      token: null,
      isAuthenticated: false,
      isLoading: true,

      // Actions
      login: async (credentials) => {
        set({ isLoading: true });

        try {
          const response = await fetch(`${API_BASE_URL}/users/login`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify(credentials),
          });

          if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            set({ isLoading: false });
            return {
              success: false,
              error: error.detail || `Login failed: ${response.status}`,
            };
          }

          const data: LoginResponse = await response.json();

          // Fetch full user data with permissions
          const userResponse = await fetch(`${API_BASE_URL}/users/me`, {
            headers: {
              Authorization: `Bearer ${data.access_token}`,
            },
          });

          if (!userResponse.ok) {
            set({ isLoading: false });
            return { success: false, error: "Failed to fetch user data" };
          }

          const userData: UserWithPermissions = await userResponse.json();

          // Set cookie for middleware
          document.cookie = `flowforge-auth-token=${data.access_token}; path=/; max-age=${data.expires_in}; SameSite=Lax`;

          set({
            token: data.access_token,
            user: userData,
            isAuthenticated: true,
            isLoading: false,
          });

          return { success: true };
        } catch (error) {
          set({ isLoading: false });
          return {
            success: false,
            error: error instanceof Error ? error.message : "Login failed",
          };
        }
      },

      logout: async () => {
        const { token } = get();

        // Call logout endpoint (optional, JWT is stateless)
        if (token) {
          try {
            await fetch(`${API_BASE_URL}/users/logout`, {
              method: "POST",
              headers: {
                Authorization: `Bearer ${token}`,
              },
            });
          } catch {
            // Ignore errors - we're logging out anyway
          }
        }

        // Clear the auth cookie
        document.cookie =
          "flowforge-auth-token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";

        set({
          user: null,
          token: null,
          isAuthenticated: false,
          isLoading: false,
        });
      },

      refreshUser: async () => {
        const { token } = get();

        if (!token) {
          set({ isLoading: false });
          return;
        }

        try {
          const response = await fetch(`${API_BASE_URL}/users/me`, {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          });

          if (!response.ok) {
            // Token is invalid, clear auth state
            set({
              user: null,
              token: null,
              isAuthenticated: false,
              isLoading: false,
            });
            return;
          }

          const userData: UserWithPermissions = await response.json();

          set({
            user: userData,
            isAuthenticated: true,
            isLoading: false,
          });
        } catch {
          set({
            user: null,
            token: null,
            isAuthenticated: false,
            isLoading: false,
          });
        }
      },

      setToken: (token) => set({ token }),
      setUser: (user) => set({ user }),
      setLoading: (loading) => set({ isLoading: loading }),
    }),
    {
      name: "flowforge-auth",
      partialize: (state) => ({
        token: state.token,
        // Don't persist user - refresh from server on reload
      }),
      onRehydrateStorage: () => {
        // After rehydration, mark as not loading (rehydration complete)
        return (state) => {
          if (state) {
            state.isLoading = false;
          }
        };
      },
    }
  )
);

// Helper hook to check permissions
export function usePermissions() {
  const user = useAuthStore((state) => state.user);

  return {
    canManageUsers: user?.permissions?.can_manage_users ?? false,
    canCreateResources: user?.permissions?.can_create_resources ?? false,
    isAdmin: user?.permissions?.is_admin ?? false,
    isMember: user?.permissions?.is_member ?? false,
    isViewer: user?.permissions?.is_viewer ?? false,
    role: user?.role ?? null,
  };
}

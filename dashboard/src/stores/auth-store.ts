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
  // Hydration tracking
  _hasHydrated: boolean;
  setHasHydrated: (hasHydrated: boolean) => void;

  // 2FA state
  requires2FA: boolean;
  tempToken: string | null;

  // Actions
  login: (credentials: LoginCredentials) => Promise<{ success: boolean; error?: string; requires2FA?: boolean }>;
  verify2FA: (code: string) => Promise<{ success: boolean; error?: string }>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
  setToken: (token: string | null) => void;
  setUser: (user: UserWithPermissions | null) => void;
  setLoading: (loading: boolean) => void;

  // 2FA management
  setup2FA: () => Promise<{ success: boolean; qrCode?: string; secret?: string; error?: string }>;
  confirm2FA: (code: string) => Promise<{ success: boolean; backupCodes?: string[]; error?: string }>;
  disable2FA: (password: string) => Promise<{ success: boolean; error?: string }>;
  getBackupCodes: (password: string) => Promise<{ success: boolean; codes?: string[]; error?: string }>;
  regenerateBackupCodes: (password: string) => Promise<{ success: boolean; codes?: string[]; error?: string }>;
}

export const useAuthStore = create<AuthStore>()(
  persist(
    (set, get) => ({
      // Initial state
      user: null,
      token: null,
      isAuthenticated: false,
      isLoading: true,

      // Hydration tracking
      _hasHydrated: false,
      setHasHydrated: (hasHydrated) => set({ _hasHydrated: hasHydrated }),

      // 2FA state
      requires2FA: false,
      tempToken: null,

      // Actions
      login: async (credentials) => {
        set({ isLoading: true, requires2FA: false, tempToken: null });

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

          const data = await response.json();

          // Check if 2FA is required
          if (data.requires_2fa) {
            set({
              requires2FA: true,
              tempToken: data.temp_token,
              isLoading: false,
            });
            return { success: true, requires2FA: true };
          }

          // No 2FA - complete login
          const loginData = data as LoginResponse;

          // Fetch full user data with permissions
          const userResponse = await fetch(`${API_BASE_URL}/users/me`, {
            headers: {
              Authorization: `Bearer ${loginData.access_token}`,
            },
          });

          if (!userResponse.ok) {
            set({ isLoading: false });
            return { success: false, error: "Failed to fetch user data" };
          }

          const userData: UserWithPermissions = await userResponse.json();

          // Set cookie for middleware
          document.cookie = `flowforge-auth-token=${loginData.access_token}; path=/; max-age=${loginData.expires_in}; SameSite=Lax`;

          set({
            token: loginData.access_token,
            user: userData,
            isAuthenticated: true,
            isLoading: false,
            requires2FA: false,
            tempToken: null,
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

      verify2FA: async (code) => {
        const { tempToken } = get();

        if (!tempToken) {
          return { success: false, error: "No pending 2FA verification" };
        }

        set({ isLoading: true });

        try {
          const response = await fetch(`${API_BASE_URL}/users/verify-2fa`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({ temp_token: tempToken, code }),
          });

          if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            set({ isLoading: false });
            return {
              success: false,
              error: error.detail || "Invalid verification code",
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
            requires2FA: false,
            tempToken: null,
          });

          return { success: true };
        } catch (error) {
          set({ isLoading: false });
          return {
            success: false,
            error: error instanceof Error ? error.message : "Verification failed",
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
          requires2FA: false,
          tempToken: null,
        });
      },

      refreshUser: async () => {
        const { token, user } = get();

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
            document.cookie =
              "flowforge-auth-token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";
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
          // On network error, keep cached user data if available
          // This prevents logout during temporary network issues
          if (user) {
            set({
              isAuthenticated: true,
              isLoading: false,
            });
          } else {
            set({
              user: null,
              token: null,
              isAuthenticated: false,
              isLoading: false,
            });
          }
        }
      },

      setToken: (token) => set({ token }),
      setUser: (user) => set({ user }),
      setLoading: (loading) => set({ isLoading: loading }),

      // 2FA management
      setup2FA: async () => {
        const { token } = get();

        if (!token) {
          return { success: false, error: "Not authenticated" };
        }

        try {
          const response = await fetch(`${API_BASE_URL}/users/2fa/setup`, {
            method: "POST",
            headers: {
              Authorization: `Bearer ${token}`,
              "Content-Type": "application/json",
            },
          });

          if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            return {
              success: false,
              error: error.detail || "Failed to setup 2FA",
            };
          }

          const data = await response.json();
          return {
            success: true,
            qrCode: data.qr_code,
            secret: data.secret,
          };
        } catch (error) {
          return {
            success: false,
            error: error instanceof Error ? error.message : "Failed to setup 2FA",
          };
        }
      },

      confirm2FA: async (code) => {
        const { token } = get();

        if (!token) {
          return { success: false, error: "Not authenticated" };
        }

        try {
          const response = await fetch(`${API_BASE_URL}/users/2fa/confirm`, {
            method: "POST",
            headers: {
              Authorization: `Bearer ${token}`,
              "Content-Type": "application/json",
            },
            body: JSON.stringify({ code }),
          });

          if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            return {
              success: false,
              error: error.detail || "Invalid verification code",
            };
          }

          const data = await response.json();

          // Update user state to reflect 2FA enabled
          const { user } = get();
          if (user) {
            set({
              user: { ...user, totp_enabled: true } as UserWithPermissions,
            });
          }

          return {
            success: true,
            backupCodes: data.backup_codes,
          };
        } catch (error) {
          return {
            success: false,
            error: error instanceof Error ? error.message : "Failed to confirm 2FA",
          };
        }
      },

      disable2FA: async (password) => {
        const { token } = get();

        if (!token) {
          return { success: false, error: "Not authenticated" };
        }

        try {
          const response = await fetch(`${API_BASE_URL}/users/2fa/disable`, {
            method: "POST",
            headers: {
              Authorization: `Bearer ${token}`,
              "Content-Type": "application/json",
            },
            body: JSON.stringify({ password }),
          });

          if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            return {
              success: false,
              error: error.detail || "Failed to disable 2FA",
            };
          }

          // Update user state to reflect 2FA disabled
          const { user } = get();
          if (user) {
            set({
              user: { ...user, totp_enabled: false } as UserWithPermissions,
            });
          }

          return { success: true };
        } catch (error) {
          return {
            success: false,
            error: error instanceof Error ? error.message : "Failed to disable 2FA",
          };
        }
      },

      getBackupCodes: async (password) => {
        const { token } = get();

        if (!token) {
          return { success: false, error: "Not authenticated" };
        }

        try {
          const response = await fetch(`${API_BASE_URL}/users/2fa/backup-codes`, {
            method: "POST",
            headers: {
              Authorization: `Bearer ${token}`,
              "Content-Type": "application/json",
            },
            body: JSON.stringify({ password }),
          });

          if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            return {
              success: false,
              error: error.detail || "Failed to get backup codes",
            };
          }

          const data = await response.json();
          return {
            success: true,
            codes: data.backup_codes,
          };
        } catch (error) {
          return {
            success: false,
            error: error instanceof Error ? error.message : "Failed to get backup codes",
          };
        }
      },

      regenerateBackupCodes: async (password) => {
        const { token } = get();

        if (!token) {
          return { success: false, error: "Not authenticated" };
        }

        try {
          const response = await fetch(`${API_BASE_URL}/users/2fa/regenerate-backup-codes`, {
            method: "POST",
            headers: {
              Authorization: `Bearer ${token}`,
              "Content-Type": "application/json",
            },
            body: JSON.stringify({ password }),
          });

          if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            return {
              success: false,
              error: error.detail || "Failed to regenerate backup codes",
            };
          }

          const data = await response.json();
          return {
            success: true,
            codes: data.backup_codes,
          };
        } catch (error) {
          return {
            success: false,
            error: error instanceof Error ? error.message : "Failed to regenerate backup codes",
          };
        }
      },
    }),
    {
      name: "flowforge-auth",
      partialize: (state) => ({
        token: state.token,
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
      onRehydrateStorage: () => {
        return (state, error) => {
          if (error) {
            console.error("Failed to rehydrate auth state:", error);
          }
          if (state) {
            // Use setState to properly trigger re-renders
            useAuthStore.setState({
              _hasHydrated: true,
              isLoading: false,
              // If we have a token and user, keep authenticated state
              isAuthenticated: !!(state.token && state.user),
            });
          }
        };
      },
    }
  )
);

// Hook to wait for hydration
export function useHasHydrated() {
  return useAuthStore((state) => state._hasHydrated);
}

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

'use client';

/**
 * Legacy compat shim — old code may import { useThemeConfig } / ActiveThemeProvider.
 * Replaced by the shell store (src/stores/shell-store.ts).
 */
import { ReactNode } from 'react';
import { useShellStore } from '@/stores/shell-store';

export function ActiveThemeProvider({ children }: { children: ReactNode; initialTheme?: string }) {
  return <>{children}</>;
}

export function useThemeConfig() {
  const { theme, setTheme } = useShellStore();
  return {
    activeTheme: theme,
    setActiveTheme: (t: string) => setTheme(t === 'light' ? 'light' : 'dark')
  };
}

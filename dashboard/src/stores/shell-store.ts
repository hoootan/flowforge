'use client';

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';

export type ThemeMode = 'dark' | 'light';
export type DensityMode = 'tight' | 'comfortable' | 'spacious';
export type SidebarMode = 'full' | 'compact';

interface ShellState {
  theme: ThemeMode;
  density: DensityMode;
  sidebar: SidebarMode;
  setTheme: (t: ThemeMode) => void;
  toggleTheme: () => void;
  setDensity: (d: DensityMode) => void;
  setSidebar: (s: SidebarMode) => void;
  toggleSidebar: () => void;
}

export const useShellStore = create<ShellState>()(
  persist(
    (set, get) => ({
      theme: 'dark',
      density: 'tight',
      sidebar: 'full',
      setTheme: (theme) => set({ theme }),
      toggleTheme: () => set({ theme: get().theme === 'dark' ? 'light' : 'dark' }),
      setDensity: (density) => set({ density }),
      setSidebar: (sidebar) => set({ sidebar }),
      toggleSidebar: () => set({ sidebar: get().sidebar === 'full' ? 'compact' : 'full' })
    }),
    {
      name: 'ff.shell',
      storage: createJSONStorage(() => (typeof window !== 'undefined' ? localStorage : undefined as never))
    }
  )
);

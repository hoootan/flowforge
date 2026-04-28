'use client';

import { useEffect } from 'react';
import { useShellStore } from '@/stores/shell-store';

/**
 * Applies theme/density/sidebar attributes to <html>/<body>.
 * The pre-hydration script in root layout sets the initial attributes
 * synchronously to avoid flash; this component keeps them in sync after.
 */
export function ShellEffects() {
  const { theme, density, sidebar } = useShellStore();

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  useEffect(() => {
    document.body.setAttribute('data-density', density);
  }, [density]);

  useEffect(() => {
    document.body.setAttribute('data-sidebar', sidebar);
  }, [sidebar]);

  return null;
}

'use client';

import { useMemo } from 'react';
import type { NavItem } from '@/types';

/**
 * Simple hook to filter navigation items
 * No RBAC needed for FlowForge - returns items as-is
 */
export function useFilteredNavItems(items: NavItem[]) {
  return useMemo(() => items, [items]);
}

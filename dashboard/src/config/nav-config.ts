import { NavItem } from '@/types';

export interface NavGroup {
  label: string;
  items: NavItem[];
}

/**
 * FlowForge Navigation — grouped by purpose (matches Paper design)
 */
export const navGroups: NavGroup[] = [
  {
    label: 'Monitor',
    items: [
      {
        title: 'Overview',
        url: '/',
        icon: 'dashboard',
        isActive: false,
        shortcut: ['d', 'd'],
        items: []
      },
      {
        title: 'Runs',
        url: '/runs',
        icon: 'activity',
        isActive: false,
        shortcut: ['r', 'r'],
        items: []
      },
      {
        title: 'Events',
        url: '/events',
        icon: 'zap',
        isActive: false,
        shortcut: ['e', 'e'],
        items: []
      },
    ]
  },
  {
    label: 'Build',
    items: [
      {
        title: 'Functions',
        url: '/functions',
        icon: 'box',
        isActive: false,
        shortcut: ['f', 'f'],
        items: []
      },
      {
        title: 'Tools',
        url: '/tools',
        icon: 'wrench',
        isActive: false,
        shortcut: ['t', 't'],
        items: []
      },
    ]
  },
  {
    label: 'Manage',
    items: [
      {
        title: 'Approvals',
        url: '/approvals',
        icon: 'check',
        isActive: false,
        shortcut: ['a', 'a'],
        items: []
      },
      {
        title: 'Settings',
        url: '/settings',
        icon: 'settings',
        isActive: false,
        items: []
      }
    ]
  }
];

/**
 * Flat nav items — backward compatible export
 */
export const navItems: NavItem[] = navGroups.flatMap((group) => group.items);

import { NavItem } from '@/types';

/**
 * FlowForge Navigation Configuration
 */
export const navItems: NavItem[] = [
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
  {
    title: 'Events',
    url: '/events',
    icon: 'zap',
    isActive: false,
    shortcut: ['e', 'e'],
    items: []
  },
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
];

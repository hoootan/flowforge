'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import * as React from 'react';
import {
  Activity,
  Bot,
  Box,
  Check,
  DollarSign,
  KanbanSquare,
  LayoutDashboard,
  LogOut,
  Settings,
  Sparkles,
  Wrench,
  Zap
} from 'lucide-react';
import { useAuthStore } from '@/stores/auth-store';
import { api } from '@/lib/api';
import { FlowForgeLogo } from '@/components/flowforge-logo';

type NavItem = {
  title: string;
  url: string;
  icon: React.ComponentType<{ className?: string }>;
  badgeKey?: 'approvals';
  exact?: boolean;
};

type NavGroup = { label: string; items: NavItem[] };

const NAV: NavGroup[] = [
  {
    label: 'Platform',
    items: [
      { title: 'Overview', url: '/', icon: LayoutDashboard, exact: true },
      { title: 'Runs', url: '/runs', icon: Activity },
      { title: 'Events', url: '/events', icon: Zap },
      { title: 'Costs', url: '/costs', icon: DollarSign }
    ]
  },
  {
    label: 'Build',
    items: [
      { title: 'Functions', url: '/functions', icon: Box },
      { title: 'Tools', url: '/tools', icon: Wrench },
      { title: 'Skills', url: '/skills', icon: Sparkles }
    ]
  },
  {
    label: 'Team',
    items: [
      { title: 'Agents', url: '/agents', icon: Bot },
      { title: 'Tasks', url: '/tasks', icon: KanbanSquare },
      { title: 'Approvals', url: '/approvals', icon: Check, badgeKey: 'approvals' }
    ]
  },
  {
    label: 'Admin',
    items: [{ title: 'Settings', url: '/settings', icon: Settings }]
  }
];

function isActive(pathname: string, item: NavItem): boolean {
  if (item.exact) return pathname === item.url;
  return pathname === item.url || pathname.startsWith(item.url + '/');
}

export default function AppSidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const [pendingApprovals, setPendingApprovals] = React.useState(0);
  const { user, logout, token, isAuthenticated, refreshUser, refreshAccessToken } = useAuthStore();

  React.useEffect(() => {
    if (token && !user) {
      refreshUser();
    }
  }, [token, user, refreshUser]);

  React.useEffect(() => {
    api.setTokenProvider(() => token);
    api.setRefreshHandler(refreshAccessToken);
    api.setAuthFailureHandler(() => {
      logout();
      router.push('/login');
    });
  }, [token, refreshAccessToken, logout, router]);

  React.useEffect(() => {
    if (!isAuthenticated) return;
    let cancelled = false;
    const fetchApprovals = async () => {
      try {
        const response = await api.getApprovals({ pending_only: true });
        if (!cancelled) setPendingApprovals(response.total ?? 0);
      } catch {
        // silent
      }
    };
    fetchApprovals();
    const id = setInterval(fetchApprovals, 30000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [isAuthenticated]);

  const initials = user?.name
    ? user.name.split(' ').map((s) => s[0]).slice(0, 2).join('').toUpperCase()
    : user?.email?.slice(0, 2).toUpperCase() ?? '–';

  return (
    <aside className="ff-side">
      <div className="ff-side-brand">
        <FlowForgeLogo style={{ width: 20, height: 20 }} />
        <div className="ff-side-brand-text">
          <div className="ff-side-brand-name">FlowForge</div>
          <div className="ff-side-brand-sub">v0.8 · ORCH</div>
        </div>
      </div>

      <nav style={{ flex: 1, overflow: 'auto', minHeight: 0 }}>
        {NAV.map((group) => (
          <div key={group.label} className="ff-side-section">
            <div className="ff-side-label">{group.label}</div>
            {group.items.map((item) => {
              const Icon = item.icon;
              const active = isActive(pathname ?? '', item);
              const showBadge = item.badgeKey === 'approvals' && pendingApprovals > 0;
              return (
                <Link
                  key={item.url}
                  href={item.url}
                  className={`ff-side-link${active ? ' is-active' : ''}`}
                  prefetch={false}
                >
                  <Icon />
                  <span className="ff-side-link-text">{item.title}</span>
                  {showBadge && <span className="ff-side-link-badge">{pendingApprovals}</span>}
                </Link>
              );
            })}
          </div>
        ))}
      </nav>

      <div className="ff-side-foot">
        <div className="ff-side-foot-av" aria-hidden>{initials}</div>
        <div className="ff-side-foot-text" style={{ minWidth: 0, flex: 1 }}>
          <div className="ff-side-foot-name" style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {user?.name ?? 'Signed out'}
          </div>
          <div className="ff-side-foot-email" style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {user?.email ?? ''}
          </div>
        </div>
        {isAuthenticated && (
          <button
            type="button"
            onClick={() => {
              logout();
              router.push('/login');
            }}
            className="btn btn-ghost btn-icon btn-sm ff-side-foot-text"
            aria-label="Sign out"
            title="Sign out"
          >
            <LogOut />
          </button>
        )}
      </div>
    </aside>
  );
}

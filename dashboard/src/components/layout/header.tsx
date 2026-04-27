'use client';

import * as React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Moon, Sun, Search, Command as CommandIcon, PanelLeft } from 'lucide-react';
import { api } from '@/lib/api';
import { useShellStore } from '@/stores/shell-store';
import { NotificationBell } from '@/components/notifications/NotificationBell';
import { useKBar } from 'kbar';

function useHealth() {
  const [status, setStatus] = React.useState<'checking' | 'connected' | 'disconnected'>('checking');
  React.useEffect(() => {
    let cancelled = false;
    const check = async () => {
      try {
        const ok = await api.checkHealth();
        if (!cancelled) setStatus(ok ? 'connected' : 'disconnected');
      } catch {
        if (!cancelled) setStatus('disconnected');
      }
    };
    check();
    const id = setInterval(check, 10000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);
  return status;
}

function HealthPill() {
  const status = useHealth();
  const label = status === 'connected' ? 'Healthy' : status === 'checking' ? '...' : 'Offline';
  return (
    <span className={`health-pill${status === 'disconnected' ? ' is-down' : ''}`}>
      <span className="health-dot" />
      {label}
    </span>
  );
}

function ThemeToggle() {
  const { theme, setTheme } = useShellStore();
  return (
    <div className="theme-toggle" role="group" aria-label="Theme">
      <button
        type="button"
        className={theme === 'light' ? 'is-on' : ''}
        onClick={() => setTheme('light')}
        aria-pressed={theme === 'light'}
        aria-label="Light theme"
      >
        <Sun />
      </button>
      <button
        type="button"
        className={theme === 'dark' ? 'is-on' : ''}
        onClick={() => setTheme('dark')}
        aria-pressed={theme === 'dark'}
        aria-label="Dark theme"
      >
        <Moon />
      </button>
    </div>
  );
}

function DensityToggle() {
  const { density, setDensity } = useShellStore();
  return (
    <div className="density-toggle" role="group" aria-label="Density">
      {(['tight', 'comfortable', 'spacious'] as const).map((d) => (
        <button
          key={d}
          type="button"
          className={density === d ? 'is-on' : ''}
          onClick={() => setDensity(d)}
          aria-pressed={density === d}
          title={`${d} density`}
        >
          {d[0]}
        </button>
      ))}
    </div>
  );
}

function Crumbs() {
  const pathname = usePathname() ?? '/';
  const segments = pathname.split('/').filter(Boolean);
  const fmt = (s: string) =>
    s.split('-').map((w) => w[0].toUpperCase() + w.slice(1)).join(' ');

  return (
    <nav className="ff-crumbs" aria-label="Breadcrumb">
      <Link href="/" className={segments.length === 0 ? 'is-current' : ''}>
        {segments.length === 0 ? <b>Overview</b> : <span>Overview</span>}
      </Link>
      {segments.map((seg, i) => {
        const href = '/' + segments.slice(0, i + 1).join('/');
        const last = i === segments.length - 1;
        return (
          <React.Fragment key={href}>
            <span className="ff-crumbs-sep">/</span>
            {last ? (
              <b>{fmt(seg)}</b>
            ) : (
              <Link href={href}>{fmt(seg)}</Link>
            )}
          </React.Fragment>
        );
      })}
    </nav>
  );
}

function SearchTrigger() {
  const { query } = useKBar();
  return (
    <div
      className="ff-top-search"
      onClick={() => query.toggle()}
      role="button"
      tabIndex={0}
      aria-label="Open command palette"
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          query.toggle();
        }
      }}
    >
      <div className="ff-top-search-inner">
        <Search />
        <input
          type="text"
          placeholder="Search runs, functions, agents…"
          readOnly
          tabIndex={-1}
        />
        <kbd>⌘K</kbd>
      </div>
    </div>
  );
}

export default function Header() {
  const toggleSidebar = useShellStore((s) => s.toggleSidebar);
  return (
    <header className="ff-top">
      <button
        type="button"
        className="ff-top-btn is-icon"
        onClick={toggleSidebar}
        aria-label="Toggle sidebar"
        title="Toggle sidebar"
      >
        <PanelLeft />
      </button>
      <Crumbs />
      <SearchTrigger />
      <DensityToggle />
      <ThemeToggle />
      <HealthPill />
      <NotificationBell />
    </header>
  );
}

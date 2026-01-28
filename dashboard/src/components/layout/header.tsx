'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { SidebarTrigger } from '../ui/sidebar';
import { Separator } from '../ui/separator';
import { Button } from '../ui/button';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger
} from '../ui/tooltip';
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator
} from '../ui/breadcrumb';
import { ModeToggle } from './ThemeToggle/theme-toggle';
import { Circle, RefreshCw, Search, Command } from 'lucide-react';
import { api } from '@/lib/api';

function ServerStatus() {
  const [status, setStatus] = useState<'checking' | 'connected' | 'disconnected'>(
    'checking'
  );

  useEffect(() => {
    async function checkHealth() {
      const healthy = await api.checkHealth();
      setStatus(healthy ? 'connected' : 'disconnected');
    }

    checkHealth();
    const interval = setInterval(checkHealth, 10000);
    return () => clearInterval(interval);
  }, []);

  const statusConfig = {
    checking: { color: 'text-yellow-500', label: 'Checking server...' },
    connected: { color: 'text-green-500', label: 'Server connected' },
    disconnected: { color: 'text-red-500', label: 'Server disconnected' }
  };

  const config = statusConfig[status];

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <div className='flex items-center gap-2 rounded-md border bg-muted/50 px-3 py-1.5'>
            <Circle className={`h-2.5 w-2.5 fill-current ${config.color}`} />
            <span className='text-xs font-medium'>
              {status === 'connected'
                ? 'Healthy'
                : status === 'disconnected'
                  ? 'Offline'
                  : '...'}
            </span>
          </div>
        </TooltipTrigger>
        <TooltipContent>
          <p>{config.label}</p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

function Breadcrumbs() {
  const pathname = usePathname();
  const segments = pathname.split('/').filter(Boolean);

  if (segments.length === 0) {
    return (
      <Breadcrumb>
        <BreadcrumbList>
          <BreadcrumbItem>
            <BreadcrumbPage>Overview</BreadcrumbPage>
          </BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>
    );
  }

  const formatSegment = (segment: string) => {
    return segment
      .split('-')
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  return (
    <Breadcrumb>
      <BreadcrumbList>
        <BreadcrumbItem>
          <BreadcrumbLink asChild>
            <Link href='/'>Overview</Link>
          </BreadcrumbLink>
        </BreadcrumbItem>
        {segments.map((segment, index) => {
          const href = '/' + segments.slice(0, index + 1).join('/');
          const isLast = index === segments.length - 1;

          return (
            <BreadcrumbItem key={segment}>
              <BreadcrumbSeparator />
              {isLast ? (
                <BreadcrumbPage>{formatSegment(segment)}</BreadcrumbPage>
              ) : (
                <BreadcrumbLink asChild>
                  <Link href={href}>{formatSegment(segment)}</Link>
                </BreadcrumbLink>
              )}
            </BreadcrumbItem>
          );
        })}
      </BreadcrumbList>
    </Breadcrumb>
  );
}

export default function Header() {
  return (
    <header className='flex h-14 shrink-0 items-center justify-between gap-2 border-b bg-background px-4 transition-[width,height] ease-linear group-has-data-[collapsible=icon]/sidebar-wrapper:h-12'>
      <div className='flex items-center gap-2'>
        <SidebarTrigger className='-ml-1' />
        <Separator orientation='vertical' className='mr-2 h-4' />
        <Breadcrumbs />
      </div>

      <div className='flex items-center gap-3'>
        {/* Search placeholder */}
        <button className='relative hidden h-9 w-64 items-center justify-start rounded-md border border-input bg-background px-3 text-sm text-muted-foreground shadow-sm transition-colors hover:bg-accent hover:text-accent-foreground md:flex lg:w-80'>
          <Search className='mr-2 h-4 w-4' />
          <span>Search...</span>
          <kbd className='pointer-events-none absolute right-2 top-1/2 hidden h-5 -translate-y-1/2 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium opacity-100 sm:flex'>
            <Command className='h-3 w-3' />K
          </kbd>
        </button>

        <ServerStatus />
        <ModeToggle />

        <Button variant='ghost' size='icon' title='Refresh data'>
          <RefreshCw className='h-4 w-4' />
        </Button>
      </div>
    </header>
  );
}

'use client';

import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger
} from '@/components/ui/collapsible';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger
} from '@/components/ui/dropdown-menu';
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuBadge,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarMenuSub,
  SidebarMenuSubButton,
  SidebarMenuSubItem,
  SidebarRail,
  useSidebar
} from '@/components/ui/sidebar';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import { navGroups } from '@/config/nav-config';
import { useAuthStore } from '@/stores/auth-store';
import {
  ChevronRight,
  ChevronsUpDown,
  Layers,
  LogOut,
  Settings,
  User,
  Shield,
  Eye
} from 'lucide-react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import * as React from 'react';
import { Icons } from '../icons';
import { api } from '@/lib/api';

const roleConfig = {
  admin: {
    label: 'Admin',
    icon: Shield,
    color: 'text-amber-500'
  },
  member: {
    label: 'Member',
    icon: User,
    color: 'text-blue-500'
  },
  viewer: {
    label: 'Viewer',
    icon: Eye,
    color: 'text-slate-500'
  }
};

export default function AppSidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { state } = useSidebar();
  const [pendingApprovals, setPendingApprovals] = React.useState(0);

  const { user, logout, token, isAuthenticated, isLoading, refreshUser, refreshAccessToken } = useAuthStore();


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
    const fetchApprovals = async () => {
      if (!isAuthenticated) return;
      try {
        const response = await api.getApprovals({ pending_only: true });
        setPendingApprovals(response.total);
      } catch {
        // Silently fail
      }
    };

    fetchApprovals();
    const interval = setInterval(fetchApprovals, 30000);
    return () => clearInterval(interval);
  }, [isAuthenticated]);

  const handleLogout = async () => {
    await logout();
    router.push('/login');
  };

  const role = user?.role ? roleConfig[user.role as keyof typeof roleConfig] : null;
  const RoleIcon = role?.icon || User;

  const initials = user?.name
    ? user.name
        .split(' ')
        .map((n) => n[0])
        .join('')
        .toUpperCase()
        .slice(0, 2)
    : 'FF';

  return (
    <Sidebar collapsible='icon'>
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton
              size='lg'
              asChild
              className='data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground'
            >
              <Link href='/'>
                <div className='flex aspect-square size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground'>
                  <Layers className='size-4' />
                </div>
                <div className='grid flex-1 text-left text-sm leading-tight'>
                  <span className='truncate font-semibold'>FlowForge</span>
                  <span className='truncate text-xs text-muted-foreground'>
                    Workflow Platform
                  </span>
                </div>
              </Link>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>
      <SidebarContent className='overflow-x-hidden'>
        {navGroups.map((group) => (
          <SidebarGroup key={group.label}>
            <SidebarGroupLabel className='text-[11px] font-semibold uppercase tracking-wider text-muted-foreground/60'>
              {group.label}
            </SidebarGroupLabel>
            <SidebarMenu>
              {group.items.map((item) => {
                const Icon = item.icon ? Icons[item.icon] : Icons.logo;
                const isActive =
                  pathname === item.url ||
                  (item.url !== '/' && pathname.startsWith(item.url));
                const showBadge = item.title === 'Approvals' && pendingApprovals > 0;

                return item?.items && item?.items?.length > 0 ? (
                  <Collapsible
                    key={item.title}
                    asChild
                    defaultOpen={item.isActive}
                    className='group/collapsible'
                  >
                    <SidebarMenuItem>
                      <CollapsibleTrigger asChild>
                        <SidebarMenuButton tooltip={item.title} isActive={isActive}>
                          {item.icon && <Icon />}
                          <span>{item.title}</span>
                          <ChevronRight className='ml-auto transition-transform duration-200 group-data-[state=open]/collapsible:rotate-90' />
                        </SidebarMenuButton>
                      </CollapsibleTrigger>
                      <CollapsibleContent>
                        <SidebarMenuSub>
                          {item.items?.map((subItem) => (
                            <SidebarMenuSubItem key={subItem.title}>
                              <SidebarMenuSubButton
                                asChild
                                isActive={pathname === subItem.url}
                              >
                                <Link href={subItem.url}>
                                  <span>{subItem.title}</span>
                                </Link>
                              </SidebarMenuSubButton>
                            </SidebarMenuSubItem>
                          ))}
                        </SidebarMenuSub>
                      </CollapsibleContent>
                    </SidebarMenuItem>
                  </Collapsible>
                ) : (
                  <SidebarMenuItem key={item.title}>
                    <SidebarMenuButton asChild tooltip={item.title} isActive={isActive}>
                      <Link href={item.url}>
                        <Icon />
                        <span>{item.title}</span>
                      </Link>
                    </SidebarMenuButton>
                    {showBadge && (
                      <SidebarMenuBadge className='bg-destructive text-destructive-foreground text-[10px] min-w-5 h-5 rounded-full flex items-center justify-center'>
                        {pendingApprovals > 99 ? '99+' : pendingApprovals}
                      </SidebarMenuBadge>
                    )}
                  </SidebarMenuItem>
                );
              })}
            </SidebarMenu>
          </SidebarGroup>
        ))}
      </SidebarContent>
      <SidebarFooter>
        <SidebarMenu>
          <SidebarMenuItem>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <SidebarMenuButton
                  size='lg'
                  className='data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground'
                >
                  <Avatar className='size-8 rounded-lg'>
                    <AvatarImage src='' alt={user?.name || 'User'} />
                    <AvatarFallback className='rounded-lg bg-primary/10 text-primary text-xs font-semibold'>{initials}</AvatarFallback>
                  </Avatar>
                  <div className='grid flex-1 text-left text-sm leading-tight'>
                    <span className='truncate font-semibold'>
                      {isLoading ? 'Loading...' : user?.name || 'Guest'}
                    </span>
                    <span className='truncate text-xs text-muted-foreground'>
                      {user?.email || 'Not logged in'}
                    </span>
                  </div>
                  <ChevronsUpDown className='ml-auto size-4' />
                </SidebarMenuButton>
              </DropdownMenuTrigger>
              <DropdownMenuContent
                className='w-[--radix-dropdown-menu-trigger-width] min-w-56 rounded-lg'
                side={state === 'collapsed' ? 'right' : 'top'}
                align='end'
                sideOffset={4}
              >
                <DropdownMenuLabel className='p-0 font-normal'>
                  <div className='flex items-center gap-2 px-1 py-1.5 text-left text-sm'>
                    <Avatar className='size-8 rounded-lg'>
                      <AvatarImage src='' alt={user?.name || 'User'} />
                      <AvatarFallback className='rounded-lg bg-primary/10 text-primary text-xs font-semibold'>{initials}</AvatarFallback>
                    </Avatar>
                    <div className='grid flex-1 text-left text-sm leading-tight'>
                      <span className='truncate font-semibold'>
                        {user?.name || 'Guest'}
                      </span>
                      <span className='truncate text-xs text-muted-foreground'>
                        {user?.email || 'Not logged in'}
                      </span>
                    </div>
                  </div>
                </DropdownMenuLabel>
                {role && (
                  <>
                    <DropdownMenuSeparator />
                    <div className='px-2 py-1.5'>
                      <Badge
                        variant='secondary'
                        className={`gap-1 text-xs ${role.color}`}
                      >
                        <RoleIcon className='h-3 w-3' />
                        {role.label}
                      </Badge>
                    </div>
                  </>
                )}
                <DropdownMenuSeparator />
                <DropdownMenuGroup>
                  <DropdownMenuItem onClick={() => router.push('/settings')}>
                    <Settings className='mr-2 size-4' />
                    Settings
                  </DropdownMenuItem>
                </DropdownMenuGroup>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={handleLogout}>
                  <LogOut className='mr-2 size-4' />
                  Log out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  );
}

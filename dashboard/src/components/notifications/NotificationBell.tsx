'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { api, type NotificationType } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import { Bell, Check, CheckCheck, Archive, Bot, AlertTriangle, MessageSquare, Zap } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

const typeIcons: Record<string, React.ReactNode> = {
  approval_required: <AlertTriangle className="h-4 w-4 text-yellow-500" />,
  task_assigned: <Zap className="h-4 w-4 text-blue-500" />,
  task_completed: <Check className="h-4 w-4 text-green-500" />,
  mention: <MessageSquare className="h-4 w-4 text-purple-500" />,
  agent_blocked: <Bot className="h-4 w-4 text-red-500" />,
  run_failed: <AlertTriangle className="h-4 w-4 text-red-500" />,
  comment: <MessageSquare className="h-4 w-4 text-blue-500" />,
};

export function NotificationBell() {
  const [notifications, setNotifications] = useState<NotificationType[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [open, setOpen] = useState(false);

  const fetchNotifications = useCallback(async () => {
    const data = await api.getNotifications({ limit: 20 });
    setNotifications(data.notifications);
    setUnreadCount(data.unread_count);
  }, []);

  useEffect(() => {
    fetchNotifications();
    const interval = setInterval(fetchNotifications, 30000);
    return () => clearInterval(interval);
  }, [fetchNotifications]);

  const handleMarkRead = async (id: string) => {
    await api.markNotificationRead(id);
    fetchNotifications();
  };

  const handleMarkAllRead = async () => {
    await api.markAllNotificationsRead();
    fetchNotifications();
  };

  const handleArchive = async (id: string) => {
    await api.archiveNotification(id);
    fetchNotifications();
  };

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button variant="ghost" size="icon" className="relative">
          <Bell className="h-4 w-4" />
          {unreadCount > 0 && (
            <Badge
              className="absolute -top-1 -right-1 h-5 w-5 flex items-center justify-center p-0 text-xs"
              variant="destructive"
            >
              {unreadCount > 9 ? '9+' : unreadCount}
            </Badge>
          )}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[360px] p-0" align="end" sideOffset={8}>
        <div className="flex items-center justify-between px-4 py-3 border-b">
          <h4 className="font-semibold text-sm">Notifications</h4>
          {unreadCount > 0 && (
            <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={handleMarkAllRead}>
              <CheckCheck className="h-3 w-3 mr-1" />
              Mark all read
            </Button>
          )}
        </div>
        <div className="max-h-[420px] overflow-y-auto overscroll-contain scrollbar-none">
          {notifications.length === 0 ? (
            <div className="py-8 text-center text-sm text-muted-foreground">
              No notifications
            </div>
          ) : (
            <div className="divide-y">
              {notifications.map(notif => (
                <div
                  key={notif.id}
                  className={`px-4 py-3 hover:bg-muted/50 transition-colors ${
                    !notif.is_read ? 'bg-primary/5' : ''
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <span className="mt-0.5 shrink-0">
                      {typeIcons[notif.notification_type] || <Bell className="h-4 w-4" />}
                    </span>
                    <div className="flex-1 min-w-0">
                      <p className={`text-sm leading-snug ${!notif.is_read ? 'font-medium' : ''}`}>
                        {notif.title}
                      </p>
                      {notif.body && (
                        <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2">
                          {notif.body}
                        </p>
                      )}
                      <p className="text-xs text-muted-foreground mt-1">
                        {notif.created_at
                          ? formatDistanceToNow(new Date(notif.created_at), { addSuffix: true })
                          : ''}
                      </p>
                    </div>
                    <div className="flex items-center gap-0.5 shrink-0">
                      {!notif.is_read && (
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-7 w-7"
                          onClick={() => handleMarkRead(notif.id)}
                        >
                          <Check className="h-3 w-3" />
                        </Button>
                      )}
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7"
                        onClick={() => handleArchive(notif.id)}
                      >
                        <Archive className="h-3 w-3" />
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </PopoverContent>
    </Popover>
  );
}

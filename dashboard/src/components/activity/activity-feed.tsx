"use client";

import * as React from "react";
import { Bot, User } from "lucide-react";
import { cn } from "@/lib/utils";

interface ActivityItem {
  id: string;
  actor: {
    name: string;
    type: "human" | "agent";
    avatar?: string;
  };
  content: string;
  timestamp: string;
}

interface ActivityFeedProps extends React.ComponentProps<"div"> {
  items: ActivityItem[];
}

function formatRelativeTime(timestamp: string): string {
  const now = Date.now();
  const t = new Date(timestamp).getTime();
  const diff = now - t;
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

function ActivityFeed({ items, className, ...props }: ActivityFeedProps) {
  return (
    <div
      data-slot="activity-feed"
      className={cn("flex flex-col gap-4", className)}
      {...props}
    >
      {items.map((item) => (
        <div key={item.id} className="flex gap-3">
          {/* Avatar */}
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-border bg-muted">
            {item.actor.type === "agent" ? (
              <Bot className="h-4 w-4 text-muted-foreground" />
            ) : (
              <User className="h-4 w-4 text-muted-foreground" />
            )}
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-foreground">
                {item.actor.name}
              </span>
              <span className="text-xs text-muted-foreground">
                {formatRelativeTime(item.timestamp)}
              </span>
            </div>
            <div className="mt-1 rounded-lg border border-border bg-secondary p-3">
              <p className="text-sm text-foreground whitespace-pre-wrap">
                {item.content}
              </p>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

export { ActivityFeed };
export type { ActivityItem };

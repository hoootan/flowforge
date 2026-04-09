"use client";

import * as React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusDot } from "@/components/ui/status-dot";
import { cn } from "@/lib/utils";

interface RuntimeStat {
  label: string;
  value: string | number;
}

interface RuntimeCardProps extends React.ComponentProps<typeof Card> {
  name: string;
  status: "online" | "offline" | "warning" | "error";
  metadata?: string;
  stats?: RuntimeStat[];
}

function RuntimeCard({
  name,
  status,
  metadata,
  stats,
  className,
  ...props
}: RuntimeCardProps) {
  return (
    <Card className={cn("transition-colors duration-200", className)} {...props}>
      <CardHeader className="pb-3">
        <div className="flex items-center gap-3">
          <StatusDot status={status} size="default" />
          <div className="flex-1 min-w-0">
            <CardTitle className="text-sm font-medium truncate">
              {name}
            </CardTitle>
            {metadata && (
              <p className="text-xs text-muted-foreground mt-0.5">
                {metadata}
              </p>
            )}
          </div>
          <span className="text-xs text-muted-foreground capitalize">
            {status}
          </span>
        </div>
      </CardHeader>
      {stats && stats.length > 0 && (
        <CardContent className="pt-0">
          <div className="grid grid-cols-2 gap-3">
            {stats.map((stat) => (
              <div key={stat.label} className="rounded-lg bg-muted p-2.5">
                <p className="text-xs text-muted-foreground">{stat.label}</p>
                <p className="text-sm font-medium tabular-nums mt-0.5">
                  {typeof stat.value === "number"
                    ? stat.value.toLocaleString()
                    : stat.value}
                </p>
              </div>
            ))}
          </div>
        </CardContent>
      )}
    </Card>
  );
}

export { RuntimeCard };

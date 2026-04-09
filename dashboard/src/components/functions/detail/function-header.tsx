"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ArrowLeft, Bot, Server, Pencil, Send, Play } from "lucide-react";
import Link from "next/link";
import { formatDistanceToNow } from "date-fns";
import type { Function as FunctionType } from "@/lib/api";

interface FunctionHeaderProps {
  func: FunctionType;
}

export function FunctionHeader({ func }: FunctionHeaderProps) {
  const Icon = func.is_inline ? Bot : Server;

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Link href="/functions">
          <Button variant="ghost" size="icon" className="h-7 w-7">
            <ArrowLeft className="h-4 w-4" />
          </Button>
        </Link>
        <Link href="/functions" className="hover:text-foreground transition-colors">Functions</Link>
        <span>/</span>
        <span className="text-foreground">{func.function_id}</span>
      </div>

      <div className="flex items-start justify-between">
        <div className="flex items-center gap-4">
          <div className="h-12 w-12 rounded-xl bg-primary/10 flex items-center justify-center">
            <Icon className="h-6 w-6 text-primary" />
          </div>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold tracking-tight">{func.name || func.function_id}</h1>
              <Badge variant={func.is_active ? "default" : "destructive"} className="text-xs">
                {func.is_active ? "Active" : "Inactive"}
              </Badge>
              <Badge variant="outline" className="text-xs">
                {func.is_inline ? "Serverless" : "Worker"}
              </Badge>
            </div>
            <div className="flex items-center gap-2 mt-1 text-sm text-muted-foreground">
              <span className="font-mono text-xs">{func.trigger_type}: {func.trigger_value}</span>
              <span className="text-border">|</span>
              <span>Created {formatDistanceToNow(new Date(func.created_at), { addSuffix: true })}</span>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Link href={`/functions/new?edit=${encodeURIComponent(func.function_id)}`}>
            <Button variant="outline" size="sm"><Pencil className="mr-2 h-4 w-4" /> Edit</Button>
          </Link>
          <Button variant="outline" size="sm"><Send className="mr-2 h-4 w-4" /> Send Event</Button>
          <Button size="sm"><Play className="mr-2 h-4 w-4" /> Trigger Run</Button>
        </div>
      </div>
    </div>
  );
}

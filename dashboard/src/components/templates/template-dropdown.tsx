"use client";

import { ReactNode } from "react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuLabel,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Sparkles, ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";

export interface Template<T> {
  id: string;
  name: string;
  description: string;
  icon?: ReactNode;
  tags?: string[];
  data: T;
}

interface TemplateDropdownProps<T> {
  templates: Template<T>[];
  onSelect: (template: Template<T>) => void;
  label?: string;
  className?: string;
  disabled?: boolean;
}

export function TemplateDropdown<T>({
  templates,
  onSelect,
  label = "Use Template",
  className,
  disabled = false,
}: TemplateDropdownProps<T>) {
  if (templates.length === 0) return null;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="outline"
          size="sm"
          disabled={disabled}
          className={cn("gap-2", className)}
        >
          <Sparkles className="h-4 w-4 text-amber-500" />
          {label}
          <ChevronDown className="h-3 w-3 opacity-50" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-72">
        <DropdownMenuLabel className="flex items-center gap-2">
          <Sparkles className="h-3.5 w-3.5 text-amber-500" />
          Quick Start Templates
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        {templates.map((template) => (
          <DropdownMenuItem
            key={template.id}
            onClick={() => onSelect(template)}
            className="flex flex-col items-start gap-1 py-2.5 cursor-pointer"
          >
            <div className="flex items-center gap-2 w-full">
              {template.icon}
              <span className="font-medium text-sm">{template.name}</span>
            </div>
            <p className="text-xs text-muted-foreground line-clamp-2 w-full">
              {template.description}
            </p>
            {template.tags && template.tags.length > 0 && (
              <div className="flex gap-1 mt-1 flex-wrap">
                {template.tags.slice(0, 3).map((tag) => (
                  <Badge key={tag} variant="secondary" className="text-[10px]">
                    {tag}
                  </Badge>
                ))}
              </div>
            )}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

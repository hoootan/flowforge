"use client";

import { ReactNode } from "react";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";

interface FormFieldProps {
  label: string;
  required?: boolean;
  description?: string;
  error?: string;
  children: ReactNode;
  className?: string;
  htmlFor?: string;
}

export function FormField({
  label,
  required = false,
  description,
  error,
  children,
  className,
  htmlFor,
}: FormFieldProps) {
  return (
    <div className={cn("space-y-2", className)}>
      <Label htmlFor={htmlFor} className="flex items-center gap-1">
        {label}
        {required && <span className="text-red-500">*</span>}
      </Label>
      {children}
      {description && !error && (
        <p className="text-sm text-muted-foreground">{description}</p>
      )}
      {error && <p className="text-sm text-red-500">{error}</p>}
    </div>
  );
}

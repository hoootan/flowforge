"use client";

import { useState, useCallback } from "react";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface JSONEditorProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  className?: string;
  rows?: number;
  disabled?: boolean;
}

export function JSONEditor({
  value,
  onChange,
  placeholder = '{\n  "key": "value"\n}',
  className,
  rows = 8,
  disabled = false,
}: JSONEditorProps) {
  const [error, setError] = useState<string | null>(null);

  const validateJSON = useCallback((text: string): boolean => {
    if (!text.trim()) {
      setError(null);
      return true;
    }
    try {
      JSON.parse(text);
      setError(null);
      return true;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Invalid JSON");
      return false;
    }
  }, []);

  const handleBlur = useCallback(() => {
    validateJSON(value);
  }, [value, validateJSON]);

  const handleFormat = useCallback(() => {
    if (!value.trim()) return;
    try {
      const parsed = JSON.parse(value);
      onChange(JSON.stringify(parsed, null, 2));
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Invalid JSON");
    }
  }, [value, onChange]);

  return (
    <div className="space-y-2">
      <div className="relative">
        <Textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onBlur={handleBlur}
          placeholder={placeholder}
          rows={rows}
          disabled={disabled}
          className={cn(
            "font-mono text-sm",
            error && "border-red-500 focus-visible:ring-red-500",
            className
          )}
        />
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={handleFormat}
          disabled={disabled || !value.trim()}
          className="absolute right-2 top-2 h-7 px-2 text-xs"
        >
          Format
        </Button>
      </div>
      {error && (
        <p className="text-sm text-red-500">{error}</p>
      )}
    </div>
  );
}

export function isValidJSON(text: string): boolean {
  if (!text.trim()) return true;
  try {
    JSON.parse(text);
    return true;
  } catch {
    return false;
  }
}

export function parseJSON<T = Record<string, unknown>>(text: string): T | null {
  if (!text.trim()) return null;
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

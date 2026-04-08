"use client";

import { useMemo, useState } from "react";
import { Copy, ChevronDown, ChevronUp } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { cn } from "@/lib/utils";
import { redactSensitiveFields } from "@/lib/redact";

interface CollapsibleJsonProps {
  value: unknown;
  className?: string;
  maxHeightClassName?: string;
  collapseThreshold?: number;
  collapsedLines?: number;
  /** Set to false to skip sensitive field redaction (e.g. for non-user-data) */
  redact?: boolean;
}

const DEFAULT_COLLAPSE_THRESHOLD = 1200;
const DEFAULT_COLLAPSED_LINES = 12;

export function CollapsibleJson({
  value,
  className,
  maxHeightClassName = "max-h-64",
  collapseThreshold = DEFAULT_COLLAPSE_THRESHOLD,
  collapsedLines = DEFAULT_COLLAPSED_LINES,
  redact = true,
}: CollapsibleJsonProps) {
  const jsonString = useMemo(() => {
    if (value === null || value === undefined) return "";
    if (typeof value === "string") return value;
    try {
      const displayValue = redact ? redactSensitiveFields(value) : value;
      return JSON.stringify(displayValue, null, 2);
    } catch (error) {
      return String(value);
    }
  }, [value, redact]);

  const lines = useMemo(() => jsonString.split("\n").length, [jsonString]);
  const shouldCollapse = jsonString.length > collapseThreshold || lines > collapsedLines;
  const [open, setOpen] = useState(!shouldCollapse);

  const preview = useMemo(() => {
    if (!shouldCollapse) return jsonString;
    const previewLines = jsonString.split("\n").slice(0, collapsedLines).join("\n");
    return lines > collapsedLines ? `${previewLines}\n…` : previewLines;
  }, [collapsedLines, jsonString, lines, shouldCollapse]);

  const preClassName = cn(
    "rounded-lg border bg-muted/50 p-3 text-xs whitespace-pre-wrap break-words overflow-auto",
    maxHeightClassName,
    className
  );

  const handleCopy = async () => {
    await navigator.clipboard.writeText(jsonString);
    toast.success("Copied to clipboard");
  };

  if (!shouldCollapse) {
    return (
      <div className="space-y-2">
        <pre className={preClassName}>{jsonString}</pre>
        <div className="flex justify-end">
          <Button variant="ghost" size="icon" onClick={handleCopy} aria-label="Copy JSON">
            <Copy className="h-4 w-4" />
          </Button>
        </div>
      </div>
    );
  }

  return (
    <Collapsible open={open} onOpenChange={setOpen} className="space-y-2">
      {!open && <pre className={preClassName}>{preview}</pre>}
      <CollapsibleContent>
        <pre className={preClassName}>{jsonString}</pre>
      </CollapsibleContent>
      <div className="flex items-center justify-between">
        <CollapsibleTrigger asChild>
          <Button variant="ghost" size="sm" className="gap-1">
            {open ? "Show less" : `Show more (${Math.max(lines - collapsedLines, 0)} lines)`}
            {open ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </Button>
        </CollapsibleTrigger>
        <Button variant="ghost" size="icon" onClick={handleCopy} aria-label="Copy JSON">
          <Copy className="h-4 w-4" />
        </Button>
      </div>
    </Collapsible>
  );
}

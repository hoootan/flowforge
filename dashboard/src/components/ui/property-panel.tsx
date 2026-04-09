import * as React from "react";
import { cn } from "@/lib/utils";

interface PropertyPanelProps extends React.ComponentProps<"div"> {
  items: { label: string; value: React.ReactNode }[];
}

function PropertyPanel({ items, className, ...props }: PropertyPanelProps) {
  return (
    <div
      data-slot="property-panel"
      className={cn("flex flex-col divide-y divide-border", className)}
      {...props}
    >
      {items.map((item) => (
        <div key={item.label} className="flex items-center justify-between py-3 first:pt-0 last:pb-0">
          <span className="text-xs text-muted-foreground uppercase tracking-wider">
            {item.label}
          </span>
          <span className="text-sm text-foreground">{item.value}</span>
        </div>
      ))}
    </div>
  );
}

export { PropertyPanel };

import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const statusDotVariants = cva("inline-block shrink-0 rounded-full", {
  variants: {
    status: {
      online: "bg-emerald-500",
      offline: "bg-zinc-600",
      warning: "bg-amber-500",
      error: "bg-red-500",
      idle: "bg-zinc-400",
    },
    size: {
      sm: "h-1.5 w-1.5",
      default: "h-2 w-2",
      lg: "h-2.5 w-2.5",
    },
    pulse: {
      true: "animate-pulse",
      false: "",
    },
  },
  defaultVariants: {
    status: "offline",
    size: "default",
    pulse: false,
  },
});

interface StatusDotProps
  extends React.ComponentProps<"span">,
    VariantProps<typeof statusDotVariants> {}

function StatusDot({
  className,
  status,
  size,
  pulse,
  ...props
}: StatusDotProps) {
  return (
    <span
      data-slot="status-dot"
      className={cn(
        statusDotVariants({ status, size, pulse: pulse ?? status === "online" }),
        className
      )}
      {...props}
    />
  );
}

export { StatusDot, statusDotVariants };

"use client"

import * as React from "react"
import { LucideIcon, TrendingDown, TrendingUp } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { cn } from "@/lib/utils"

interface StatCardProps {
  title: string
  value: string | number
  description?: string
  trend?: {
    value: number
    isPositive: boolean
  }
  icon?: LucideIcon | React.ReactNode
  iconColor?: string
  className?: string
}

// Check if the icon is a component (LucideIcon) vs a rendered element
function isIconComponent(icon: unknown): icon is LucideIcon {
  // LucideIcon components are objects with $$typeof and render properties (forwardRef)
  // or functions (regular components)
  if (typeof icon === "function") return true
  if (
    typeof icon === "object" &&
    icon !== null &&
    "$$typeof" in icon &&
    "render" in icon
  ) {
    return true
  }
  return false
}

export function StatCard({
  title,
  value,
  description,
  trend,
  icon,
  iconColor,
  className,
}: StatCardProps) {
  const renderIcon = () => {
    if (!icon) return null

    // If it's already a valid React element, render it directly
    if (React.isValidElement(icon)) {
      return icon
    }

    // If it's a component reference (LucideIcon), instantiate it
    if (isIconComponent(icon)) {
      const Icon = icon as LucideIcon
      return <Icon className={cn("h-4 w-4", iconColor || "text-muted-foreground")} />
    }

    // Fallback for other ReactNode types
    return <span className={iconColor || "text-muted-foreground"}>{icon}</span>
  }

  return (
    <Card className={cn("transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md", className)}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          {title}
        </CardTitle>
        {renderIcon()}
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold tabular-nums">
          {typeof value === "number" ? value.toLocaleString() : value}
        </div>
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          {trend && (
            <span
              className={cn(
                "flex items-center gap-1 font-medium",
                trend.isPositive ? "text-emerald-500" : "text-red-500"
              )}
            >
              {trend.isPositive ? (
                <TrendingUp className="h-3 w-3" />
              ) : (
                <TrendingDown className="h-3 w-3" />
              )}
              {trend.value > 0 ? "+" : ""}{trend.value}%
            </span>
          )}
          {description && <span>{description}</span>}
        </div>
      </CardContent>
    </Card>
  )
}

"use client"

import * as React from "react"
import { cn } from "@/lib/utils"

interface PageTransitionProps {
  children: React.ReactNode
  className?: string
}

export function PageTransition({ children, className }: PageTransitionProps) {
  return (
    <div
      className={cn(
        "animate-fade-in",
        className
      )}
    >
      {children}
    </div>
  )
}

interface StaggeredListProps {
  children: React.ReactNode
  className?: string
}

export function StaggeredList({ children, className }: StaggeredListProps) {
  return (
    <div className={cn("stagger-children", className)}>
      {children}
    </div>
  )
}

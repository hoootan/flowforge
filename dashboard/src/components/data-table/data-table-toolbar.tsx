"use client"

import type { Table } from "@tanstack/react-table"
import { Search, X } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { cn } from "@/lib/utils"

interface DataTableToolbarProps<TData> extends React.ComponentProps<"div"> {
  table: Table<TData>
  searchColumn?: string
  searchPlaceholder?: string
}

export function DataTableToolbar<TData>({
  table,
  searchColumn,
  searchPlaceholder = "Search...",
  className,
  children,
  ...props
}: DataTableToolbarProps<TData>) {
  const isFiltered = table.getState().columnFilters.length > 0

  return (
    <div
      className={cn(
        "flex flex-wrap items-center justify-between gap-2",
        className
      )}
      {...props}
    >
      <div className="flex flex-1 flex-wrap items-center gap-2">
        {searchColumn && (
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder={searchPlaceholder}
              value={
                (table.getColumn(searchColumn)?.getFilterValue() as string) ??
                ""
              }
              onChange={(event) =>
                table.getColumn(searchColumn)?.setFilterValue(event.target.value)
              }
              className="h-9 w-[200px] pl-8 lg:w-[280px]"
            />
          </div>
        )}
        {children}
        {isFiltered && (
          <Button
            variant="ghost"
            onClick={() => table.resetColumnFilters()}
            className="h-9 px-2 lg:px-3"
          >
            Reset
            <X className="ml-2 h-4 w-4" />
          </Button>
        )}
      </div>
    </div>
  )
}

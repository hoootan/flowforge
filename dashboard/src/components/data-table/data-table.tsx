"use client"

import { type Table as TanstackTable, flexRender } from "@tanstack/react-table"
import type * as React from "react"

import { DataTablePagination } from "@/components/data-table/data-table-pagination"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { ScrollArea, ScrollBar } from "@/components/ui/scroll-area"
import { cn } from "@/lib/utils"

interface DataTableProps<TData> extends React.ComponentProps<"div"> {
  table: TanstackTable<TData>
  actionBar?: React.ReactNode
  onRowClick?: (row: TData) => void
  totalRows?: number // For server-side pagination
}

export function DataTable<TData>({
  table,
  actionBar,
  onRowClick,
  totalRows,
  children,
  className,
}: DataTableProps<TData>) {
  return (
    <div className={cn("flex flex-col space-y-4", className)}>
      {children}
      <div className="rounded-lg border">
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <TableHead key={header.id} colSpan={header.colSpan}>
                    {header.isPlaceholder
                      ? null
                      : flexRender(
                          header.column.columnDef.header,
                          header.getContext()
                        )}
                  </TableHead>
                ))}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {table.getRowModel().rows?.length ? (
              table.getRowModel().rows.map((row) => (
                <TableRow
                  key={row.id}
                  data-state={row.getIsSelected() && "selected"}
                  onClick={() => onRowClick?.(row.original)}
                  className={onRowClick ? "cursor-pointer hover:bg-muted/50" : ""}
                >
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id}>
                      {flexRender(
                        cell.column.columnDef.cell,
                        cell.getContext()
                      )}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell
                  colSpan={table.getAllColumns().length}
                  className="h-24 text-center"
                >
                  No results.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
      <DataTablePagination table={table} totalRows={totalRows} />
      {actionBar &&
        table.getFilteredSelectedRowModel().rows.length > 0 &&
        actionBar}
    </div>
  )
}

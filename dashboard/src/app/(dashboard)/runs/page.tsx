"use client"

import { useEffect, useState, useCallback, useMemo } from "react"
import { useRouter } from "next/navigation"
import {
  ColumnDef,
  ColumnFiltersState,
  SortingState,
  VisibilityState,
  PaginationState,
  getCoreRowModel,
  getFilteredRowModel,
  getSortedRowModel,
  useReactTable,
} from "@tanstack/react-table"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  CheckCircle,
  Clock,
  XCircle,
  Pause,
  RefreshCw,
  PlayCircle,
  StopCircle,
  MoreHorizontal,
} from "lucide-react"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { toast } from "sonner"
import { api, Run } from "@/lib/api"
import {
  DataTable,
  DataTableColumnHeader,
  DataTableFacetedFilter,
  DataTableToolbar,
  DataTableSkeleton,
  type FilterOption,
} from "@/components/data-table"
import { NoDataState } from "@/components/empty-state"

function getStatusIcon(status: string) {
  switch (status) {
    case "completed":
      return <CheckCircle className="h-4 w-4 text-emerald-500" />
    case "running":
      return <PlayCircle className="h-4 w-4 text-primary animate-pulse" />
    case "failed":
      return <XCircle className="h-4 w-4 text-destructive" />
    case "paused":
      return <Pause className="h-4 w-4 text-amber-500" />
    default:
      return <Clock className="h-4 w-4 text-muted-foreground" />
  }
}

function getStatusBadge(status: string) {
  const config: Record<
    string,
    { variant: "default" | "secondary" | "destructive" | "outline"; className?: string }
  > = {
    completed: { variant: "outline", className: "border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-800 dark:bg-emerald-950 dark:text-emerald-400" },
    running: { variant: "outline", className: "border-primary/20 bg-primary/10 text-primary" },
    failed: { variant: "outline", className: "border-red-200 bg-red-50 text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-400" },
    pending: { variant: "outline", className: "border-muted text-muted-foreground" },
    paused: { variant: "outline", className: "border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-400" },
  }

  const { variant, className } = config[status] || { variant: "outline" as const }

  return (
    <Badge variant={variant} className={className}>
      {status}
    </Badge>
  )
}

function formatDuration(startedAt: string | null, endedAt: string | null): string {
  if (!startedAt) return "-"
  const start = new Date(startedAt).getTime()
  const end = endedAt ? new Date(endedAt).getTime() : Date.now()
  const ms = end - start
  if (ms < 1000) return `${ms}ms`
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
  return `${(ms / 60000).toFixed(1)}m`
}

function formatTimestamp(iso: string | null): string {
  if (!iso) return "-"
  const date = new Date(iso)
  return date.toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  })
}

const statusOptions: FilterOption[] = [
  { label: "Running", value: "running", icon: PlayCircle },
  { label: "Completed", value: "completed", icon: CheckCircle },
  { label: "Failed", value: "failed", icon: XCircle },
  { label: "Paused", value: "paused", icon: Pause },
  { label: "Pending", value: "pending", icon: Clock },
]

const PAGE_SIZE = 20

export default function RunsPage() {
  const router = useRouter()
  const [runs, setRuns] = useState<Run[]>([])
  const [totalRows, setTotalRows] = useState(0)
  const [initialLoading, setInitialLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [pagination, setPagination] = useState<PaginationState>({
    pageIndex: 0,
    pageSize: PAGE_SIZE,
  })
  const [sorting, setSorting] = useState<SortingState>([])
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([])
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({})
  const [rowSelection, setRowSelection] = useState({})

  const fetchRuns = useCallback(async (page: number, pageSize: number, isInitial = false) => {
    if (isInitial) {
      setInitialLoading(true)
    } else {
      setRefreshing(true)
    }
    const response = await api.getRuns({
      page: page + 1, // API uses 1-based indexing
      page_size: pageSize
    })
    setRuns(response.runs || [])
    setTotalRows(response.total || 0)
    setInitialLoading(false)
    setRefreshing(false)
  }, [])

  const handleCancelRun = useCallback(async (runId: string, e: React.MouseEvent) => {
    e.stopPropagation() // Prevent row click
    const result = await api.cancelRun(runId)
    if (result?.success) {
      toast.success("Run cancelled successfully")
      fetchRuns(pagination.pageIndex, pagination.pageSize, false)
    } else {
      toast.error("Failed to cancel run")
    }
  }, [fetchRuns, pagination.pageIndex, pagination.pageSize])

  useEffect(() => {
    fetchRuns(pagination.pageIndex, pagination.pageSize, runs.length === 0)
  }, [fetchRuns, pagination.pageIndex, pagination.pageSize])

  const columns: ColumnDef<Run>[] = useMemo(
    () => [
      {
        accessorKey: "status",
        header: ({ column }) => (
          <DataTableColumnHeader column={column} title="Status" />
        ),
        cell: ({ row }) => {
          const status = row.getValue("status") as string
          return (
            <div className="flex items-center gap-2">
              {getStatusIcon(status)}
              {getStatusBadge(status)}
            </div>
          )
        },
        filterFn: (row, id, value) => {
          return value.includes(row.getValue(id))
        },
      },
      {
        accessorKey: "function_id",
        header: ({ column }) => (
          <DataTableColumnHeader column={column} title="Function" />
        ),
        cell: ({ row }) => (
          <div className="font-medium">{row.getValue("function_id")}</div>
        ),
      },
      {
        accessorKey: "id",
        header: ({ column }) => (
          <DataTableColumnHeader column={column} title="Run ID" />
        ),
        cell: ({ row }) => (
          <div className="font-mono text-xs text-muted-foreground">
            {(row.getValue("id") as string).slice(0, 8)}...
          </div>
        ),
      },
      {
        accessorKey: "trigger_type",
        header: ({ column }) => (
          <DataTableColumnHeader column={column} title="Trigger" />
        ),
        cell: ({ row }) => (
          <Badge variant="outline" className="font-mono text-xs">
            {row.getValue("trigger_type")}
          </Badge>
        ),
      },
      {
        id: "duration",
        header: ({ column }) => (
          <DataTableColumnHeader column={column} title="Duration" />
        ),
        cell: ({ row }) => (
          <div className="font-mono text-sm">
            {formatDuration(row.original.started_at, row.original.ended_at)}
          </div>
        ),
      },
      {
        accessorKey: "started_at",
        header: ({ column }) => (
          <DataTableColumnHeader column={column} title="Started" />
        ),
        cell: ({ row }) => (
          <div className="text-muted-foreground">
            {formatTimestamp(row.getValue("started_at"))}
          </div>
        ),
      },
      {
        id: "actions",
        cell: ({ row }) => {
          const run = row.original
          const canCancel = run.status === "running" || run.status === "pending" || run.status === "paused"

          return (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8"
                  onClick={(e) => e.stopPropagation()}
                >
                  <MoreHorizontal className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                {canCancel && (
                  <DropdownMenuItem
                    onClick={(e) => handleCancelRun(run.id, e as unknown as React.MouseEvent)}
                    className="text-destructive focus:text-destructive"
                  >
                    <StopCircle className="mr-2 h-4 w-4" />
                    Cancel Run
                  </DropdownMenuItem>
                )}
                <DropdownMenuItem
                  onClick={(e) => {
                    e.stopPropagation()
                    router.push(`/runs/${run.id}`)
                  }}
                >
                  View Details
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          )
        },
      },
    ],
    [handleCancelRun, router]
  )

  const pageCount = Math.ceil(totalRows / pagination.pageSize)

  const table = useReactTable({
    data: runs,
    columns,
    pageCount,
    manualPagination: true,
    onPaginationChange: setPagination,
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    onColumnVisibilityChange: setColumnVisibility,
    onRowSelectionChange: setRowSelection,
    state: {
      pagination,
      sorting,
      columnFilters,
      columnVisibility,
      rowSelection,
    },
  })

  if (initialLoading) {
    return (
      <div className="space-y-6 animate-fade-in">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Runs</h1>
            <p className="text-muted-foreground">
              View and manage all function executions.
            </p>
          </div>
        </div>
        <DataTableSkeleton columnCount={6} rowCount={10} />
      </div>
    )
  }

  return (
    <div className="flex h-full flex-col space-y-6 animate-fade-in">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Runs</h1>
          <p className="text-muted-foreground">
            View and manage all function executions.
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => fetchRuns(pagination.pageIndex, pagination.pageSize, false)}
          disabled={refreshing}
        >
          <RefreshCw className={`mr-2 h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      </div>

      {runs.length === 0 ? (
        <NoDataState resource="runs" />
      ) : (
        <div className={`transition-opacity duration-200 ${refreshing ? "opacity-60" : "opacity-100"}`}>
        <DataTable
          table={table}
          totalRows={totalRows}
          onRowClick={(run) => router.push(`/runs/${run.id}`)}
        >
          <DataTableToolbar
            table={table}
            searchColumn="function_id"
            searchPlaceholder="Search functions..."
          >
            {table.getColumn("status") && (
              <DataTableFacetedFilter
                column={table.getColumn("status")}
                title="Status"
                options={statusOptions}
              />
            )}
          </DataTableToolbar>
        </DataTable>
        </div>
      )}
    </div>
  )
}

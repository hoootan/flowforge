"use client"

import { useEffect, useState, useCallback, useMemo } from "react"
import { useRouter } from "next/navigation"
import { useViewMode } from "@/hooks/use-view-mode"
import Link from "next/link"
import {
  ColumnDef,
  ColumnFiltersState,
  SortingState,
  VisibilityState,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useReactTable,
} from "@tanstack/react-table"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import {
  Box,
  Calendar,
  Zap,
  Webhook,
  RefreshCw,
  Cloud,
  Server,
  Plus,
  LayoutGrid,
  List,
  CheckCircle,
  XCircle,
  Clock,
  PlayCircle,
  MessageSquare,
  Wrench,
} from "lucide-react"
import { api, Function } from "@/lib/api"
import {
  DataTable,
  DataTableColumnHeader,
  DataTableFacetedFilter,
  DataTableToolbar,
  DataTableSkeleton,
  type FilterOption,
} from "@/components/data-table"
import { NoDataState } from "@/components/empty-state"
import { FunctionActions } from "@/components/functions/function-actions"
import { toast } from "sonner"
import { StatCard } from "@/components/charts"

function getTriggerIcon(type: string) {
  switch (type) {
    case "event":
      return <Zap className="h-4 w-4" />
    case "cron":
      return <Calendar className="h-4 w-4" />
    case "webhook":
      return <Webhook className="h-4 w-4" />
    default:
      return <Box className="h-4 w-4" />
  }
}

function getTriggerBadgeClass(type: string) {
  switch (type) {
    case "event":
      return "bg-amber-500/10 text-amber-600 border-amber-500/20"
    case "cron":
      return "bg-purple-500/10 text-purple-600 border-purple-500/20"
    case "webhook":
      return "bg-cyan-500/10 text-cyan-600 border-cyan-500/20"
    default:
      return ""
  }
}

function formatTimestamp(iso: string | null): string {
  if (!iso) return "—"
  const date = new Date(iso)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  return `${diffDays}d ago`
}

function truncateText(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text
  return text.slice(0, maxLength) + "..."
}

const triggerOptions: FilterOption[] = [
  { label: "Event", value: "event", icon: Zap },
  { label: "Cron", value: "cron", icon: Calendar },
  { label: "Webhook", value: "webhook", icon: Webhook },
]

const modeOptions: FilterOption[] = [
  { label: "Serverless", value: "true", icon: Cloud },
  { label: "Worker", value: "false", icon: Server },
]

const statusOptions: FilterOption[] = [
  { label: "Active", value: "true", icon: CheckCircle },
  { label: "Inactive", value: "false", icon: Clock },
]

// Function Card component for grid view
function FunctionCard({
  fn,
  onRefresh,
  onSuccess,
  onError,
}: {
  fn: Function
  onRefresh: () => void
  onSuccess: (message: string) => void
  onError: (message: string) => void
}) {
  const router = useRouter()
  return (
    <Card
      className="group relative overflow-hidden transition-all hover:shadow-md hover:-translate-y-0.5 flex flex-col h-full cursor-pointer"
      onClick={(e) => {
        // Don't navigate if clicking on actions dropdown or its children
        const target = e.target as HTMLElement
        if (target.closest('[data-slot="dropdown-menu-trigger"]') || target.closest('[role="menu"]') || target.closest('[role="dialog"]')) return
        router.push(`/functions/${encodeURIComponent(fn.function_id)}`)
      }}
    >
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-3">
            <div
              className={`flex h-10 w-10 items-center justify-center rounded-lg ${
                fn.is_inline ? "bg-blue-500/10" : "bg-purple-500/10"
              }`}
            >
              {fn.is_inline ? (
                <Cloud className="h-5 w-5 text-blue-600" />
              ) : (
                <Server className="h-5 w-5 text-purple-600" />
              )}
            </div>
            <div className="min-w-0 flex-1">
              <CardTitle className="text-base truncate">{fn.name}</CardTitle>
              <CardDescription className="font-mono text-xs truncate">
                {fn.function_id}
              </CardDescription>
            </div>
          </div>
          <FunctionActions
            func={fn}
            onRefresh={onRefresh}
            onSuccess={onSuccess}
            onError={onError}
          />
        </div>
      </CardHeader>
      <CardContent className="space-y-4 flex-1">
        {/* Trigger */}
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5 text-muted-foreground">
            {getTriggerIcon(fn.trigger_type)}
            <span className="text-xs font-medium uppercase">{fn.trigger_type}</span>
          </div>
          <Badge variant="outline" className={`font-mono text-xs ${getTriggerBadgeClass(fn.trigger_type)}`}>
            {fn.trigger_value}
          </Badge>
        </div>

        {/* Status badges */}
        <div className="flex flex-wrap gap-2">
          <Badge
            variant={fn.is_active ? "default" : "secondary"}
            className={fn.is_active ? "bg-emerald-500/10 text-emerald-600 border-emerald-500/20" : ""}
          >
            {fn.is_active ? "Active" : "Inactive"}
          </Badge>
          <Badge variant="outline" className="capitalize">
            {fn.is_inline ? "Serverless" : "Worker"}
          </Badge>
        </div>

        {/* System prompt preview (for inline functions) */}
        {fn.is_inline && fn.system_prompt && (
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <div className="flex items-start gap-2 rounded-md bg-muted/50 p-2 cursor-help">
                  <MessageSquare className="h-4 w-4 text-muted-foreground shrink-0 mt-0.5" />
                  <p className="text-xs text-muted-foreground line-clamp-2">
                    {fn.system_prompt}
                  </p>
                </div>
              </TooltipTrigger>
              <TooltipContent side="bottom" className="max-w-sm">
                <p className="text-xs whitespace-pre-wrap">{fn.system_prompt}</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        )}

        {/* Tools (for inline functions) */}
        {fn.is_inline && fn.tools_config && fn.tools_config.length > 0 && (
          <div className="flex items-center gap-2">
            <Wrench className="h-4 w-4 text-muted-foreground shrink-0" />
            <div className="flex flex-wrap gap-1">
              {fn.tools_config.map((tool) => (
                <Badge key={tool} variant="outline" className="font-mono text-xs">
                  {tool}
                </Badge>
              ))}
            </div>
          </div>
        )}

        {/* Endpoint URL (for worker functions) */}
        {!fn.is_inline && fn.endpoint_url && (
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Server className="h-4 w-4 shrink-0" />
            <span className="font-mono truncate">{fn.endpoint_url}</span>
          </div>
        )}
      </CardContent>
      {/* Footer - always at bottom */}
      <div className="px-6 pb-4">
        <div className="flex items-center justify-between text-xs text-muted-foreground border-t pt-3">
          <span>Created {formatTimestamp(fn.created_at)}</span>
        </div>
      </div>
    </Card>
  )
}

export default function FunctionsPage() {
  const [functions, setFunctions] = useState<Function[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [viewMode, setViewMode] = useViewMode<"grid" | "list">("functions", "grid")
  const [sorting, setSorting] = useState<SortingState>([])
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([])
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({})
  const [rowSelection, setRowSelection] = useState({})

  const fetchFunctions = useCallback(async () => {
    setLoading(true)
    const response = await api.getFunctions()
    setFunctions(response.functions)
    setTotal(response.total)
    setLoading(false)
  }, [])

  useEffect(() => {
    fetchFunctions()
  }, [fetchFunctions])

  const activeCount = functions.filter((f) => f.is_active).length
  const inlineCount = functions.filter((f) => f.is_inline).length
  const workerCount = functions.filter((f) => !f.is_inline).length

  const handleSuccess = (message: string) => {
    toast.success(message)
  }

  const handleError = (message: string) => {
    toast.error(message)
  }

  // Define columns for table view
  const columns: ColumnDef<Function>[] = useMemo(
    () => [
      {
        accessorKey: "name",
        header: ({ column }) => (
          <DataTableColumnHeader column={column} title="Function" />
        ),
        cell: ({ row }) => {
          const fn = row.original
          return (
            <div className="flex items-center gap-3">
              <div
                className={`flex h-8 w-8 items-center justify-center rounded-lg ${
                  fn.is_inline ? "bg-blue-500/10" : "bg-purple-500/10"
                }`}
              >
                {fn.is_inline ? (
                  <Cloud className="h-4 w-4 text-blue-600" />
                ) : (
                  <Server className="h-4 w-4 text-purple-600" />
                )}
              </div>
              <div>
                <p className="font-medium">{fn.name}</p>
                <p className="font-mono text-xs text-muted-foreground">
                  {fn.function_id}
                </p>
              </div>
            </div>
          )
        },
      },
      {
        accessorKey: "trigger_type",
        header: ({ column }) => (
          <DataTableColumnHeader column={column} title="Trigger" />
        ),
        cell: ({ row }) => {
          const fn = row.original
          return (
            <div className="flex items-center gap-2">
              {getTriggerIcon(fn.trigger_type)}
              <Badge
                variant="outline"
                className={`font-mono text-xs ${getTriggerBadgeClass(fn.trigger_type)}`}
              >
                {fn.trigger_value}
              </Badge>
            </div>
          )
        },
        filterFn: (row, id, value) => {
          return value.includes(row.getValue(id))
        },
      },
      {
        accessorKey: "is_inline",
        header: ({ column }) => (
          <DataTableColumnHeader column={column} title="Mode" />
        ),
        cell: ({ row }) => {
          const isInline = row.getValue("is_inline") as boolean
          return (
            <Badge variant={isInline ? "default" : "secondary"} className="capitalize">
              {isInline ? "Serverless" : "Worker"}
            </Badge>
          )
        },
        filterFn: (row, id, value) => {
          const isInline = row.getValue(id) as boolean
          return value.includes(String(isInline))
        },
      },
      {
        accessorKey: "is_active",
        header: ({ column }) => (
          <DataTableColumnHeader column={column} title="Status" />
        ),
        cell: ({ row }) => {
          const isActive = row.getValue("is_active") as boolean
          return (
            <Badge
              variant={isActive ? "default" : "secondary"}
              className={
                isActive
                  ? "bg-emerald-500/10 text-emerald-600 border-emerald-500/20"
                  : ""
              }
            >
              {isActive ? "Active" : "Inactive"}
            </Badge>
          )
        },
        filterFn: (row, id, value) => {
          const isActive = row.getValue(id) as boolean
          return value.includes(String(isActive))
        },
      },
      {
        id: "tools_endpoint",
        header: ({ column }) => (
          <DataTableColumnHeader column={column} title="Endpoint / Tools" />
        ),
        cell: ({ row }) => {
          const fn = row.original
          if (fn.is_inline) {
            return (
              <div className="flex flex-wrap gap-1">
                {fn.tools_config?.map((tool) => (
                  <Badge key={tool} variant="outline" className="font-mono text-xs">
                    {tool}
                  </Badge>
                ))}
              </div>
            )
          }
          return (
            <span className="font-mono text-xs text-muted-foreground truncate block max-w-48">
              {fn.endpoint_url}
            </span>
          )
        },
      },
      {
        accessorKey: "created_at",
        header: ({ column }) => (
          <DataTableColumnHeader column={column} title="Created" />
        ),
        cell: ({ row }) => (
          <div className="text-muted-foreground">
            {formatTimestamp(row.getValue("created_at"))}
          </div>
        ),
      },
      {
        id: "actions",
        cell: ({ row }) => (
          <FunctionActions
            func={row.original}
            onRefresh={fetchFunctions}
            onSuccess={handleSuccess}
            onError={handleError}
          />
        ),
      },
    ],
    [fetchFunctions]
  )

  const table = useReactTable({
    data: functions,
    columns,
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    getCoreRowModel: getCoreRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    onColumnVisibilityChange: setColumnVisibility,
    onRowSelectionChange: setRowSelection,
    state: {
      sorting,
      columnFilters,
      columnVisibility,
      rowSelection,
    },
  })

  if (loading) {
    return (
      <div className="space-y-6 animate-fade-in">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Functions</h1>
            <p className="text-muted-foreground">
              Manage your registered workflow functions.
            </p>
          </div>
        </div>
        <div className="grid gap-4 md:grid-cols-4">
          {[...Array(4)].map((_, i) => (
            <Card key={i} className="animate-pulse">
              <CardHeader className="pb-2">
                <div className="h-4 w-24 bg-muted rounded" />
              </CardHeader>
              <CardContent>
                <div className="h-8 w-12 bg-muted rounded" />
              </CardContent>
            </Card>
          ))}
        </div>
        <DataTableSkeleton columnCount={7} rowCount={5} />
      </div>
    )
  }

  return (
    <div className="flex h-full flex-col space-y-6 animate-fade-in">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Functions</h1>
          <p className="text-muted-foreground">
            Manage your registered workflow functions.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={fetchFunctions} disabled={loading}>
            <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
          <Link href="/functions/new">
            <Button size="sm">
              <Plus className="mr-2 h-4 w-4" />
              Create Function
            </Button>
          </Link>
        </div>
      </div>

      {/* Stats Overview */}
      <div className="grid gap-4 md:grid-cols-4">
        <StatCard
          title="Total Functions"
          value={total}
          icon={Box}
        />
        <StatCard
          title="Active"
          value={activeCount}
          icon={CheckCircle}
          iconColor="text-emerald-500"
        />
        <StatCard
          title="Serverless (Inline)"
          value={inlineCount}
          icon={Cloud}
          iconColor="text-blue-500"
        />
        <StatCard
          title="Worker Mode"
          value={workerCount}
          icon={Server}
          iconColor="text-purple-500"
        />
      </div>

      {functions.length === 0 ? (
        <Card>
          <NoDataState resource="functions" />
        </Card>
      ) : (
        <>
          {/* View Toggle and Filters */}
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              {viewMode === "list" && (
                <>
                  {table.getColumn("trigger_type") && (
                    <DataTableFacetedFilter
                      column={table.getColumn("trigger_type")}
                      title="Trigger"
                      options={triggerOptions}
                    />
                  )}
                  {table.getColumn("is_inline") && (
                    <DataTableFacetedFilter
                      column={table.getColumn("is_inline")}
                      title="Mode"
                      options={modeOptions}
                    />
                  )}
                  {table.getColumn("is_active") && (
                    <DataTableFacetedFilter
                      column={table.getColumn("is_active")}
                      title="Status"
                      options={statusOptions}
                    />
                  )}
                </>
              )}
            </div>
            <Tabs value={viewMode} onValueChange={(v) => setViewMode(v as "grid" | "list")}>
              <TabsList>
                <TabsTrigger value="grid" className="gap-1.5">
                  <LayoutGrid className="h-4 w-4" />
                  <span className="hidden sm:inline">Cards</span>
                </TabsTrigger>
                <TabsTrigger value="list" className="gap-1.5">
                  <List className="h-4 w-4" />
                  <span className="hidden sm:inline">Table</span>
                </TabsTrigger>
              </TabsList>
            </Tabs>
          </div>

          {/* Grid View */}
          {viewMode === "grid" && (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {functions.map((fn) => (
                <FunctionCard
                  key={fn.id}
                  fn={fn}
                  onRefresh={fetchFunctions}
                  onSuccess={handleSuccess}
                  onError={handleError}
                />
              ))}
            </div>
          )}

          {/* List View */}
          {viewMode === "list" && (
            <DataTable table={table} className="flex-1">
              <DataTableToolbar
                table={table}
                searchColumn="name"
                searchPlaceholder="Search functions..."
              />
            </DataTable>
          )}
        </>
      )}
    </div>
  )
}

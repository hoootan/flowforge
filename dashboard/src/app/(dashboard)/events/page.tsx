"use client"

import { useEffect, useState, useCallback, useMemo } from "react"
import { useViewMode } from "@/hooks/use-view-mode"
import { redactSensitiveFields } from "@/lib/redact"
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
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
  Zap,
  RefreshCw,
  Eye,
  CheckCircle,
  Clock,
  Plus,
  MoreHorizontal,
  RotateCcw,
  Activity,
  Inbox,
  CheckCheck,
  LayoutGrid,
  List,
  Radio,
} from "lucide-react"
import { api, Event } from "@/lib/api"
import {
  DataTable,
  DataTableColumnHeader,
  DataTableFacetedFilter,
  DataTableToolbar,
  DataTableSkeleton,
  type FilterOption,
} from "@/components/data-table"
import { NoDataState } from "@/components/empty-state"
import { SendEventDialog } from "@/components/events/send-event-dialog"
import { toast } from "sonner"
import { StatCard } from "@/components/charts"

function formatTimestamp(iso: string): string {
  const date = new Date(iso)
  return date.toLocaleString()
}

function formatRelativeTime(iso: string): string {
  const date = new Date(iso)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)

  if (diffMins < 1) return "just now"
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  return date.toLocaleDateString()
}

const statusOptions: FilterOption[] = [
  { label: "Processed", value: "true", icon: CheckCircle },
  { label: "Pending", value: "false", icon: Clock },
]

// Event Card for timeline view
function EventCard({
  event,
  onResend,
}: {
  event: Event
  onResend: (event: Event) => void
}) {
  const [detailsOpen, setDetailsOpen] = useState(false)

  return (
    <div className="relative pl-6 pb-6 last:pb-0">
      {/* Timeline line */}
      <div className="absolute left-[11px] top-[28px] bottom-0 w-px bg-border last:hidden" />

      {/* Timeline dot */}
      <div
        className={`absolute left-0 top-[6px] h-6 w-6 rounded-full border-2 bg-background flex items-center justify-center ${
          event.processed
            ? "border-emerald-500"
            : "border-amber-500"
        }`}
      >
        {event.processed ? (
          <CheckCircle className="h-3 w-3 text-emerald-500" />
        ) : (
          <Clock className="h-3 w-3 text-amber-500" />
        )}
      </div>

      {/* Event content */}
      <Card className="ml-4 transition-all hover:shadow-md hover:-translate-y-0.5">
        <CardContent className="p-4">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <Zap className="h-4 w-4 text-amber-500 shrink-0" />
                <span className="font-medium truncate">{event.name}</span>
                <Badge
                  variant={event.processed ? "default" : "secondary"}
                  className={`shrink-0 ${
                    event.processed
                      ? "bg-emerald-500/10 text-emerald-600 border-emerald-500/20"
                      : "bg-amber-500/10 text-amber-600 border-amber-500/20"
                  }`}
                >
                  {event.processed ? "Processed" : "Pending"}
                </Badge>
              </div>
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <code className="bg-muted px-1.5 py-0.5 rounded">
                  {event.event_id.slice(0, 8)}
                </code>
                <span>&bull;</span>
                <span>{formatRelativeTime(event.received_at)}</span>
              </div>
            </div>

            <div className="flex items-center gap-1">
              <Dialog open={detailsOpen} onOpenChange={setDetailsOpen}>
                <DialogTrigger asChild>
                  <Button variant="ghost" size="icon" className="h-8 w-8">
                    <Eye className="h-4 w-4" />
                  </Button>
                </DialogTrigger>
                <DialogContent className="max-w-2xl overflow-hidden">
                  <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                      <Zap className="h-5 w-5 text-amber-500" />
                      {event.name}
                    </DialogTitle>
                    <DialogDescription className="font-mono text-xs">
                      {event.event_id}
                    </DialogDescription>
                  </DialogHeader>
                  <div className="space-y-4 pt-2">
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div className="space-y-1">
                        <p className="text-muted-foreground">Received</p>
                        <p className="font-medium">{formatTimestamp(event.received_at)}</p>
                      </div>
                      <div className="space-y-1">
                        <p className="text-muted-foreground">Timestamp</p>
                        <p className="font-medium">{formatTimestamp(event.timestamp)}</p>
                      </div>
                      <div className="space-y-1">
                        <p className="text-muted-foreground">Status</p>
                        <Badge
                          variant={event.processed ? "default" : "secondary"}
                          className={event.processed ? "bg-emerald-500/10 text-emerald-600" : ""}
                        >
                          {event.processed ? "Processed" : "Pending"}
                        </Badge>
                      </div>
                      {event.user_id && (
                        <div className="space-y-1">
                          <p className="text-muted-foreground">User ID</p>
                          <code className="text-xs bg-muted px-1.5 py-0.5 rounded">{event.user_id}</code>
                        </div>
                      )}
                    </div>
                    <div className="space-y-2">
                      <p className="text-sm font-medium">Event Data</p>
                      <pre className="rounded-lg border bg-muted/50 p-4 text-xs overflow-auto max-h-64 font-mono whitespace-pre-wrap break-all">
                        {JSON.stringify(redactSensitiveFields(event.data), null, 2)}
                      </pre>
                    </div>
                  </div>
                </DialogContent>
              </Dialog>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" size="icon" className="h-8 w-8">
                    <MoreHorizontal className="h-4 w-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem onClick={() => onResend(event)}>
                    <RotateCcw className="mr-2 h-4 w-4" />
                    Re-send Event
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>

          {/* Data preview */}
          {Object.keys(event.data).length > 0 && (
            <div className="mt-3 pt-3 border-t">
              <p className="text-xs text-muted-foreground mb-1">Data preview</p>
              <code className="text-xs text-muted-foreground line-clamp-1">
                {JSON.stringify(event.data).slice(0, 100)}
                {JSON.stringify(event.data).length > 100 && "..."}
              </code>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

const PAGE_SIZE = 20

export default function EventsPage() {
  const [events, setEvents] = useState<Event[]>([])
  const [total, setTotal] = useState(0)
  const [initialLoading, setInitialLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [sendOpen, setSendOpen] = useState(false)
  const [resendEvent, setResendEvent] = useState<Event | null>(null)
  const [viewMode, setViewMode] = useViewMode<"table" | "timeline">("events", "table")
  const [liveMode, setLiveMode] = useState(false)
  const [pagination, setPagination] = useState<PaginationState>({
    pageIndex: 0,
    pageSize: PAGE_SIZE,
  })
  const [sorting, setSorting] = useState<SortingState>([])
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([])
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({})
  const [rowSelection, setRowSelection] = useState({})

  const fetchEvents = useCallback(async (page: number, pageSize: number, isInitial = false) => {
    if (isInitial) {
      setInitialLoading(true)
    } else {
      setRefreshing(true)
    }
    const response = await api.getEvents({
      page: page + 1, // API uses 1-based indexing
      page_size: pageSize
    })
    setEvents(response.events)
    setTotal(response.total)
    setInitialLoading(false)
    setRefreshing(false)
  }, [])

  useEffect(() => {
    fetchEvents(pagination.pageIndex, pagination.pageSize, events.length === 0)
  }, [fetchEvents, pagination.pageIndex, pagination.pageSize])

  // Live mode polling
  useEffect(() => {
    if (!liveMode) return
    const interval = setInterval(() => fetchEvents(pagination.pageIndex, pagination.pageSize, false), 3000)
    return () => clearInterval(interval)
  }, [liveMode, fetchEvents, pagination.pageIndex, pagination.pageSize])

  const processedCount = events.filter((e) => e.processed).length
  const pendingCount = events.length - processedCount

  const handleSuccess = () => {
    toast.success("Event sent successfully")
    fetchEvents(pagination.pageIndex, pagination.pageSize, false)
  }

  const handleError = (message: string) => {
    toast.error(message)
  }

  const handleResend = (event: Event) => {
    setResendEvent(event)
    setSendOpen(true)
  }

  // Define columns for table view
  const columns: ColumnDef<Event>[] = useMemo(
    () => [
      {
        accessorKey: "processed",
        header: ({ column }) => (
          <DataTableColumnHeader column={column} title="Status" />
        ),
        cell: ({ row }) => {
          const processed = row.getValue("processed") as boolean
          return (
            <Badge
              variant={processed ? "default" : "secondary"}
              className={`gap-1.5 ${
                processed
                  ? "bg-emerald-500/10 text-emerald-600 border-emerald-500/20"
                  : "bg-amber-500/10 text-amber-600 border-amber-500/20"
              }`}
            >
              {processed ? (
                <CheckCircle className="h-3 w-3" />
              ) : (
                <Clock className="h-3 w-3" />
              )}
              {processed ? "Processed" : "Pending"}
            </Badge>
          )
        },
        filterFn: (row, id, value) => {
          const processed = row.getValue(id) as boolean
          return value.includes(String(processed))
        },
      },
      {
        accessorKey: "name",
        header: ({ column }) => (
          <DataTableColumnHeader column={column} title="Event Name" />
        ),
        cell: ({ row }) => (
          <div className="flex items-center gap-2">
            <Zap className="h-4 w-4 text-amber-500 shrink-0" />
            <span className="font-medium truncate max-w-[200px]">
              {row.getValue("name")}
            </span>
          </div>
        ),
      },
      {
        accessorKey: "event_id",
        header: ({ column }) => (
          <DataTableColumnHeader column={column} title="Event ID" />
        ),
        cell: ({ row }) => (
          <code className="text-xs text-muted-foreground bg-muted px-1.5 py-0.5 rounded">
            {(row.getValue("event_id") as string).slice(0, 8)}
          </code>
        ),
      },
      {
        accessorKey: "received_at",
        header: ({ column }) => (
          <DataTableColumnHeader column={column} title="Received" />
        ),
        cell: ({ row }) => (
          <span className="text-sm text-muted-foreground">
            {formatRelativeTime(row.getValue("received_at"))}
          </span>
        ),
      },
      {
        id: "actions",
        cell: ({ row }) => {
          const event = row.original
          return (
            <div className="flex items-center gap-1">
              <Dialog>
                <DialogTrigger asChild>
                  <Button variant="ghost" size="icon" className="h-8 w-8">
                    <Eye className="h-4 w-4" />
                  </Button>
                </DialogTrigger>
                <DialogContent className="max-w-2xl overflow-hidden">
                  <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                      <Zap className="h-5 w-5 text-amber-500" />
                      {event.name}
                    </DialogTitle>
                    <DialogDescription className="font-mono text-xs">
                      {event.event_id}
                    </DialogDescription>
                  </DialogHeader>
                  <div className="space-y-4 pt-2">
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div className="space-y-1">
                        <p className="text-muted-foreground">Received</p>
                        <p className="font-medium">{formatTimestamp(event.received_at)}</p>
                      </div>
                      <div className="space-y-1">
                        <p className="text-muted-foreground">Timestamp</p>
                        <p className="font-medium">{formatTimestamp(event.timestamp)}</p>
                      </div>
                      <div className="space-y-1">
                        <p className="text-muted-foreground">Status</p>
                        <Badge
                          variant={event.processed ? "default" : "secondary"}
                          className={event.processed ? "bg-emerald-500/10 text-emerald-600" : ""}
                        >
                          {event.processed ? "Processed" : "Pending"}
                        </Badge>
                      </div>
                      {event.user_id && (
                        <div className="space-y-1">
                          <p className="text-muted-foreground">User ID</p>
                          <code className="text-xs bg-muted px-1.5 py-0.5 rounded">{event.user_id}</code>
                        </div>
                      )}
                    </div>
                    <div className="space-y-2">
                      <p className="text-sm font-medium">Event Data</p>
                      <pre className="rounded-lg border bg-muted/50 p-4 text-xs overflow-auto max-h-64 font-mono whitespace-pre-wrap break-all">
                        {JSON.stringify(redactSensitiveFields(event.data), null, 2)}
                      </pre>
                    </div>
                  </div>
                </DialogContent>
              </Dialog>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" size="icon" className="h-8 w-8">
                    <MoreHorizontal className="h-4 w-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem onClick={() => handleResend(event)}>
                    <RotateCcw className="mr-2 h-4 w-4" />
                    Re-send Event
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          )
        },
      },
    ],
    []
  )

  const pageCount = Math.ceil(total / pagination.pageSize)

  const table = useReactTable({
    data: events,
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
            <h1 className="text-2xl font-bold tracking-tight">Events</h1>
            <p className="text-muted-foreground">
              View ingested events and their triggered functions.
            </p>
          </div>
        </div>
        <div className="grid gap-4 md:grid-cols-3">
          {[...Array(3)].map((_, i) => (
            <Card key={i} className="animate-pulse">
              <CardContent className="p-4">
                <div className="h-12 bg-muted rounded" />
              </CardContent>
            </Card>
          ))}
        </div>
        <DataTableSkeleton columnCount={5} rowCount={10} />
      </div>
    )
  }

  return (
    <div className="flex h-full flex-col space-y-6 animate-fade-in">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Events</h1>
          <p className="text-muted-foreground">
            View ingested events and their triggered functions.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => fetchEvents(pagination.pageIndex, pagination.pageSize, false)}
            disabled={refreshing}
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${refreshing ? "animate-spin" : ""}`} />
            Refresh
          </Button>
          <Button size="sm" onClick={() => { setResendEvent(null); setSendOpen(true); }}>
            <Plus className="h-4 w-4 mr-2" />
            Send Event
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-3">
        <StatCard
          title="Total Events"
          value={total}
          icon={Activity}
        />
        <StatCard
          title="Processed"
          value={processedCount}
          icon={CheckCheck}
          iconColor="text-emerald-500"
        />
        <StatCard
          title="Pending"
          value={pendingCount}
          icon={Inbox}
          iconColor="text-amber-500"
        />
      </div>

      {events.length === 0 ? (
        <Card>
          <NoDataState resource="events" />
        </Card>
      ) : (
        <>
          {/* View Toggle, Live Mode, and Filters */}
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              {viewMode === "table" && (
                <>
                  {table.getColumn("processed") && (
                    <DataTableFacetedFilter
                      column={table.getColumn("processed")}
                      title="Status"
                      options={statusOptions}
                    />
                  )}
                </>
              )}

              {/* Live mode toggle */}
              <div className="flex items-center gap-2">
                <Switch
                  id="live-mode"
                  checked={liveMode}
                  onCheckedChange={setLiveMode}
                />
                <Label
                  htmlFor="live-mode"
                  className={`flex items-center gap-1.5 text-sm cursor-pointer ${
                    liveMode ? "text-emerald-600" : "text-muted-foreground"
                  }`}
                >
                  <Radio className={`h-3 w-3 ${liveMode ? "animate-pulse" : ""}`} />
                  Live
                </Label>
              </div>
            </div>

            <Tabs value={viewMode} onValueChange={(v) => setViewMode(v as "table" | "timeline")}>
              <TabsList>
                <TabsTrigger value="table" className="gap-1.5">
                  <List className="h-4 w-4" />
                  <span className="hidden sm:inline">Table</span>
                </TabsTrigger>
                <TabsTrigger value="timeline" className="gap-1.5">
                  <LayoutGrid className="h-4 w-4" />
                  <span className="hidden sm:inline">Timeline</span>
                </TabsTrigger>
              </TabsList>
            </Tabs>
          </div>

          {/* Table View */}
          {viewMode === "table" && (
            <div className={`transition-opacity duration-200 ${refreshing ? "opacity-60" : "opacity-100"}`}>
              <DataTable table={table} totalRows={total}>
                <DataTableToolbar
                  table={table}
                  searchColumn="name"
                  searchPlaceholder="Search events..."
                />
              </DataTable>
            </div>
          )}

          {/* Timeline View */}
          {viewMode === "timeline" && (
            <div className={`max-w-3xl transition-opacity duration-200 ${refreshing ? "opacity-60" : "opacity-100"}`}>
              {events.map((event) => (
                <EventCard
                  key={event.id}
                  event={event}
                  onResend={handleResend}
                />
              ))}
            </div>
          )}
        </>
      )}

      {/* Send Event Dialog */}
      <SendEventDialog
        open={sendOpen}
        onOpenChange={setSendOpen}
        onSuccess={handleSuccess}
        onError={handleError}
        prefillEvent={resendEvent}
      />
    </div>
  )
}

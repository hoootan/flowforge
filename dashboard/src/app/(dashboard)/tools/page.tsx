"use client"

import { useEffect, useState, useCallback, useMemo } from "react"
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
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion"
import {
  Wrench,
  Shield,
  RefreshCw,
  Package,
  Code,
  Plus,
  CheckCircle,
  Clock,
  Settings2,
  AlertTriangle,
  LayoutGrid,
  List,
} from "lucide-react"
import { api, Tool } from "@/lib/api"
import {
  DataTable,
  DataTableColumnHeader,
  DataTableFacetedFilter,
  DataTableToolbar,
  DataTableSkeleton,
  type FilterOption,
} from "@/components/data-table"
import { NoDataState } from "@/components/empty-state"
import { ToolActions } from "@/components/tools/tool-actions"
import { toast } from "sonner"
import { StatCard } from "@/components/charts"

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

function getParameterPreview(parameters: Record<string, unknown>): string[] {
  if (!parameters || typeof parameters !== "object") return []
  const props = (parameters as { properties?: Record<string, unknown> }).properties
  if (!props) return []
  return Object.keys(props).slice(0, 4)
}

const typeOptions: FilterOption[] = [
  { label: "Built-in", value: "true", icon: Package },
  { label: "Custom", value: "false", icon: Code },
]

const approvalOptions: FilterOption[] = [
  { label: "Required", value: "true", icon: Shield },
  { label: "Not Required", value: "false", icon: CheckCircle },
]

const statusOptions: FilterOption[] = [
  { label: "Active", value: "true", icon: CheckCircle },
  { label: "Inactive", value: "false", icon: Clock },
]

// Tool Card component for grid view
function ToolCard({
  tool,
  onRefresh,
  onSuccess,
  onError,
}: {
  tool: Tool
  onRefresh: () => void
  onSuccess: (message: string) => void
  onError: (message: string) => void
}) {
  const params = getParameterPreview(tool.parameters)

  return (
    <Card className="group relative overflow-hidden transition-all hover:shadow-md hover:-translate-y-0.5">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-3">
            <div
              className={`flex h-10 w-10 items-center justify-center rounded-lg ${
                tool.is_builtin ? "bg-blue-500/10" : "bg-purple-500/10"
              }`}
            >
              {tool.is_builtin ? (
                <Package className="h-5 w-5 text-blue-600" />
              ) : (
                <Code className="h-5 w-5 text-purple-600" />
              )}
            </div>
            <div className="min-w-0 flex-1">
              <CardTitle className="text-base font-mono truncate">{tool.name}</CardTitle>
              <CardDescription className="capitalize">
                {tool.is_builtin ? "Built-in" : "Custom"} tool
              </CardDescription>
            </div>
          </div>
          <ToolActions
            tool={tool}
            onRefresh={onRefresh}
            onSuccess={onSuccess}
            onError={onError}
          />
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Description */}
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <p className="text-sm text-muted-foreground line-clamp-2 cursor-help">
                {tool.description}
              </p>
            </TooltipTrigger>
            <TooltipContent side="bottom" className="max-w-sm">
              <p className="text-xs">{tool.description}</p>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>

        {/* Status badges */}
        <div className="flex flex-wrap gap-2">
          <Badge
            variant={tool.is_active ? "default" : "secondary"}
            className={tool.is_active ? "bg-emerald-500/10 text-emerald-600 border-emerald-500/20" : ""}
          >
            {tool.is_active ? "Active" : "Inactive"}
          </Badge>
          {tool.requires_approval && (
            <Badge variant="outline" className="bg-orange-500/10 text-orange-600 border-orange-500/20">
              <Shield className="mr-1 h-3 w-3" />
              Approval Required
            </Badge>
          )}
        </div>

        {/* Parameters preview */}
        {params.length > 0 && (
          <div className="flex items-start gap-2">
            <Settings2 className="h-4 w-4 text-muted-foreground shrink-0 mt-0.5" />
            <div className="flex flex-wrap gap-1">
              {params.map((param) => (
                <Badge key={param} variant="outline" className="font-mono text-xs">
                  {param}
                </Badge>
              ))}
              {Object.keys((tool.parameters as { properties?: Record<string, unknown> }).properties || {}).length > 4 && (
                <Badge variant="outline" className="text-xs">
                  +{Object.keys((tool.parameters as { properties?: Record<string, unknown> }).properties || {}).length - 4}
                </Badge>
              )}
            </div>
          </div>
        )}

        {/* Approval timeout */}
        {tool.requires_approval && tool.approval_timeout && (
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Clock className="h-4 w-4" />
            <span>Timeout: {tool.approval_timeout}</span>
          </div>
        )}

        {/* Created timestamp */}
        <div className="flex items-center justify-between text-xs text-muted-foreground border-t pt-3">
          <span>Created {formatTimestamp(tool.created_at)}</span>
        </div>
      </CardContent>
    </Card>
  )
}

export default function ToolsPage() {
  const [tools, setTools] = useState<Tool[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [viewMode, setViewMode] = useViewMode<"grid" | "list">("tools", "grid")
  const [groupBy, setGroupBy] = useState<"all" | "type">("type")
  const [sorting, setSorting] = useState<SortingState>([])
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([])
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({})
  const [rowSelection, setRowSelection] = useState({})

  const fetchTools = useCallback(async () => {
    setLoading(true)
    const response = await api.getTools()
    setTools(response.tools)
    setTotal(response.total)
    setLoading(false)
  }, [])

  useEffect(() => {
    fetchTools()
  }, [fetchTools])

  const builtinTools = useMemo(() => tools.filter((t) => t.is_builtin), [tools])
  const customTools = useMemo(() => tools.filter((t) => !t.is_builtin), [tools])
  const approvalCount = tools.filter((t) => t.requires_approval).length

  const handleSuccess = (message: string) => {
    toast.success(message)
  }

  const handleError = (message: string) => {
    toast.error(message)
  }

  // Define columns for table view
  const columns: ColumnDef<Tool>[] = useMemo(
    () => [
      {
        accessorKey: "name",
        header: ({ column }) => (
          <DataTableColumnHeader column={column} title="Tool" />
        ),
        cell: ({ row }) => {
          const tool = row.original
          return (
            <div className="flex items-center gap-3">
              <div
                className={`flex h-8 w-8 items-center justify-center rounded-lg ${
                  tool.is_builtin ? "bg-blue-500/10" : "bg-purple-500/10"
                }`}
              >
                {tool.is_builtin ? (
                  <Package className="h-4 w-4 text-blue-600" />
                ) : (
                  <Code className="h-4 w-4 text-purple-600" />
                )}
              </div>
              <p className="font-medium font-mono">{tool.name}</p>
            </div>
          )
        },
      },
      {
        accessorKey: "description",
        header: ({ column }) => (
          <DataTableColumnHeader column={column} title="Description" />
        ),
        cell: ({ row }) => (
          <p className="text-sm text-muted-foreground truncate max-w-md">
            {row.getValue("description")}
          </p>
        ),
      },
      {
        accessorKey: "is_builtin",
        header: ({ column }) => (
          <DataTableColumnHeader column={column} title="Type" />
        ),
        cell: ({ row }) => {
          const isBuiltin = row.getValue("is_builtin") as boolean
          return (
            <Badge variant={isBuiltin ? "default" : "secondary"} className="capitalize">
              {isBuiltin ? "Built-in" : "Custom"}
            </Badge>
          )
        },
        filterFn: (row, id, value) => {
          const isBuiltin = row.getValue(id) as boolean
          return value.includes(String(isBuiltin))
        },
      },
      {
        accessorKey: "requires_approval",
        header: ({ column }) => (
          <DataTableColumnHeader column={column} title="Approval" />
        ),
        cell: ({ row }) => {
          const tool = row.original
          if (tool.requires_approval) {
            return (
              <div className="flex items-center gap-1 text-orange-600">
                <Shield className="h-4 w-4" />
                <span className="text-xs">{tool.approval_timeout || "1h"}</span>
              </div>
            )
          }
          return <span className="text-muted-foreground text-xs">No</span>
        },
        filterFn: (row, id, value) => {
          const requiresApproval = row.getValue(id) as boolean
          return value.includes(String(requiresApproval))
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
          <ToolActions
            tool={row.original}
            onRefresh={fetchTools}
            onSuccess={handleSuccess}
            onError={handleError}
          />
        ),
      },
    ],
    [fetchTools]
  )

  const table = useReactTable({
    data: tools,
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
            <h1 className="text-2xl font-bold tracking-tight">Tools</h1>
            <p className="text-muted-foreground">
              Manage tools available for inline agent functions.
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
          <h1 className="text-2xl font-bold tracking-tight">Tools</h1>
          <p className="text-muted-foreground">
            Manage tools available for inline agent functions.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={fetchTools} disabled={loading}>
            <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
          <Link href="/tools/new">
            <Button size="sm">
              <Plus className="mr-2 h-4 w-4" />
              Create Tool
            </Button>
          </Link>
        </div>
      </div>

      {/* Stats Overview */}
      <div className="grid gap-4 md:grid-cols-4">
        <StatCard
          title="Total Tools"
          value={total}
          icon={Wrench}
        />
        <StatCard
          title="Built-in"
          value={builtinTools.length}
          icon={Package}
          iconColor="text-blue-500"
        />
        <StatCard
          title="Custom"
          value={customTools.length}
          icon={Code}
          iconColor="text-purple-500"
        />
        <StatCard
          title="Requires Approval"
          value={approvalCount}
          icon={Shield}
          iconColor="text-orange-500"
        />
      </div>

      {tools.length === 0 ? (
        <Card>
          <NoDataState resource="tools" />
        </Card>
      ) : (
        <>
          {/* View Toggle and Filters */}
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              {viewMode === "list" && (
                <>
                  {table.getColumn("is_builtin") && (
                    <DataTableFacetedFilter
                      column={table.getColumn("is_builtin")}
                      title="Type"
                      options={typeOptions}
                    />
                  )}
                  {table.getColumn("requires_approval") && (
                    <DataTableFacetedFilter
                      column={table.getColumn("requires_approval")}
                      title="Approval"
                      options={approvalOptions}
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
              {viewMode === "grid" && (
                <Tabs value={groupBy} onValueChange={(v) => setGroupBy(v as "all" | "type")}>
                  <TabsList>
                    <TabsTrigger value="type">By Type</TabsTrigger>
                    <TabsTrigger value="all">All</TabsTrigger>
                  </TabsList>
                </Tabs>
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
            <>
              {groupBy === "type" ? (
                <Accordion type="multiple" defaultValue={["builtin", "custom"]} className="space-y-4 pb-2">
                  {/* Built-in Tools */}
                  <AccordionItem value="builtin" className="border rounded-lg">
                    <AccordionTrigger className="px-4 hover:no-underline">
                      <div className="flex items-center gap-3">
                        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-500/10">
                          <Package className="h-4 w-4 text-blue-600" />
                        </div>
                        <div className="text-left">
                          <p className="font-medium">Built-in Tools</p>
                          <p className="text-xs text-muted-foreground">
                            {builtinTools.length} tool{builtinTools.length !== 1 ? "s" : ""}
                          </p>
                        </div>
                      </div>
                    </AccordionTrigger>
                    <AccordionContent className="px-4 pb-6 pt-2">
                      {builtinTools.length === 0 ? (
                        <p className="text-sm text-muted-foreground py-4 text-center">
                          No built-in tools available
                        </p>
                      ) : (
                        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 p-1">
                          {builtinTools.map((tool) => (
                            <ToolCard
                              key={tool.id}
                              tool={tool}
                              onRefresh={fetchTools}
                              onSuccess={handleSuccess}
                              onError={handleError}
                            />
                          ))}
                        </div>
                      )}
                    </AccordionContent>
                  </AccordionItem>

                  {/* Custom Tools */}
                  <AccordionItem value="custom" className="border rounded-lg">
                    <AccordionTrigger className="px-4 hover:no-underline">
                      <div className="flex items-center gap-3">
                        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-purple-500/10">
                          <Code className="h-4 w-4 text-purple-600" />
                        </div>
                        <div className="text-left">
                          <p className="font-medium">Custom Tools</p>
                          <p className="text-xs text-muted-foreground">
                            {customTools.length} tool{customTools.length !== 1 ? "s" : ""}
                          </p>
                        </div>
                      </div>
                    </AccordionTrigger>
                    <AccordionContent className="px-4 pb-6 pt-2">
                      {customTools.length === 0 ? (
                        <div className="py-8 text-center">
                          <Code className="mx-auto mb-2 h-8 w-8 text-muted-foreground opacity-50" />
                          <p className="text-sm font-medium">No custom tools yet</p>
                          <p className="text-xs text-muted-foreground mb-4">
                            Create custom tools to extend your agent&apos;s capabilities
                          </p>
                          <Link href="/tools/new">
                            <Button size="sm">
                              <Plus className="mr-2 h-4 w-4" />
                              Create Tool
                            </Button>
                          </Link>
                        </div>
                      ) : (
                        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 p-1">
                          {customTools.map((tool) => (
                            <ToolCard
                              key={tool.id}
                              tool={tool}
                              onRefresh={fetchTools}
                              onSuccess={handleSuccess}
                              onError={handleError}
                            />
                          ))}
                        </div>
                      )}
                    </AccordionContent>
                  </AccordionItem>
                </Accordion>
              ) : (
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                  {tools.map((tool) => (
                    <ToolCard
                      key={tool.id}
                      tool={tool}
                      onRefresh={fetchTools}
                      onSuccess={handleSuccess}
                      onError={handleError}
                    />
                  ))}
                </div>
              )}
            </>
          )}

          {/* List View */}
          {viewMode === "list" && (
            <DataTable table={table} className="flex-1">
              <DataTableToolbar
                table={table}
                searchColumn="name"
                searchPlaceholder="Search tools..."
              />
            </DataTable>
          )}
        </>
      )}
    </div>
  )
}

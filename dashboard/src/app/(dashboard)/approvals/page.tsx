"use client"

import { useEffect, useState, useCallback } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Checkbox } from "@/components/ui/checkbox"
import { Switch } from "@/components/ui/switch"
import { Skeleton } from "@/components/ui/skeleton"
import { ScrollArea } from "@/components/ui/scroll-area"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"
import {
  CheckCircle,
  XCircle,
  Clock,
  AlertTriangle,
  AlertCircle,
  RefreshCw,
  Radio,
  Timer,
  ChevronRight,
  Keyboard,
} from "lucide-react"
import { useApprovals, useApproveToolCall, useRejectToolCall } from "@/lib/hooks/useAgent"
import { toast } from "sonner"
import type { PendingApproval } from "@/lib/api"
import { StatCard } from "@/components/charts"

function formatTime(isoString: string): string {
  const date = new Date(isoString)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)

  if (diffMins < 1) return "Just now"
  if (diffMins < 60) return `${diffMins}m ago`
  const diffHours = Math.floor(diffMins / 60)
  if (diffHours < 24) return `${diffHours}h ago`
  const diffDays = Math.floor(diffHours / 24)
  return `${diffDays}d ago`
}

function getTimeRemaining(timeoutAt: string): { text: string; urgent: boolean; expired: boolean } {
  const timeout = new Date(timeoutAt)
  const now = new Date()
  const diffMs = timeout.getTime() - now.getTime()

  if (diffMs <= 0) {
    return { text: "Expired", urgent: true, expired: true }
  }

  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)

  if (diffMins < 10) {
    return { text: `${diffMins}m left`, urgent: true, expired: false }
  }
  if (diffMins < 60) {
    return { text: `${diffMins}m left`, urgent: false, expired: false }
  }
  return { text: `${diffHours}h left`, urgent: false, expired: false }
}

function LoadingSkeleton() {
  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <Skeleton className="h-8 w-48 mb-2" />
          <Skeleton className="h-4 w-64" />
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
      <div className="space-y-4">
        {[...Array(3)].map((_, i) => (
          <Skeleton key={i} className="h-48 w-full" />
        ))}
      </div>
    </div>
  )
}

// Enhanced approval card with urgency indicator
function ApprovalCard({
  approval,
  isSelected,
  onSelect,
  onApprove,
  onReject,
  onViewDetails,
}: {
  approval: PendingApproval
  isSelected: boolean
  onSelect: (id: string, selected: boolean) => void
  onApprove: (id: string) => Promise<void>
  onReject: (id: string, reason: string) => Promise<void>
  onViewDetails: (approval: PendingApproval) => void
}) {
  const [showRejectDialog, setShowRejectDialog] = useState(false)
  const [rejectionReason, setRejectionReason] = useState("")
  const [isProcessing, setIsProcessing] = useState(false)
  const [showConversation, setShowConversation] = useState(false)

  const timeRemaining = getTimeRemaining(approval.timeout_at)
  const recentMessages = (approval.agent_conversation || []).slice(-3)

  const handleApprove = async () => {
    setIsProcessing(true)
    try {
      await onApprove(approval.id)
      toast.success("Tool call approved")
    } catch (error) {
      toast.error("Failed to approve tool call")
    } finally {
      setIsProcessing(false)
    }
  }

  const handleReject = async () => {
    if (!rejectionReason.trim()) return
    setIsProcessing(true)
    try {
      await onReject(approval.id, rejectionReason)
      setShowRejectDialog(false)
      setRejectionReason("")
      toast.success("Tool call rejected")
    } catch (error) {
      toast.error("Failed to reject tool call")
    } finally {
      setIsProcessing(false)
    }
  }

  return (
    <>
      <Card
        className={`overflow-hidden transition-all hover:shadow-md ${
          timeRemaining.urgent
            ? "border-l-4 border-l-red-500"
            : "border-l-4 border-l-amber-500"
        } ${isSelected ? "ring-2 ring-primary" : ""}`}
      >
        <CardHeader className="pb-3">
          <div className="flex items-start justify-between gap-2">
            <div className="flex items-center gap-3">
              <Checkbox
                checked={isSelected}
                onCheckedChange={(checked) => onSelect(approval.id, checked as boolean)}
              />
              <div className="flex items-center gap-2 min-w-0">
                <AlertTriangle
                  className={`h-5 w-5 shrink-0 ${
                    timeRemaining.urgent ? "text-red-600" : "text-amber-600"
                  }`}
                />
                <CardTitle className="text-base truncate">{approval.tool_name}</CardTitle>
              </div>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              {/* Urgency countdown */}
              <Badge
                variant="outline"
                className={`gap-1 ${
                  timeRemaining.expired
                    ? "bg-red-500/10 text-red-600 border-red-500/20"
                    : timeRemaining.urgent
                      ? "bg-red-500/10 text-red-600 border-red-500/20 animate-pulse"
                      : "bg-amber-500/10 text-amber-600 border-amber-500/20"
                }`}
              >
                <Timer className="h-3 w-3" />
                {timeRemaining.text}
              </Badge>
              <Badge variant="outline" className="gap-1">
                <Clock className="h-3 w-3" />
                {formatTime(approval.created_at)}
              </Badge>
            </div>
          </div>
          <CardDescription className="text-xs truncate ml-9">
            Run: {approval.run_id.slice(0, 8)}... • {approval.function_id}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4 overflow-hidden">
          {/* Tool Arguments */}
          <div>
            <span className="text-sm font-medium">Tool Arguments</span>
            <pre className="mt-2 rounded-lg border bg-muted/50 p-3 text-xs overflow-auto max-h-32 whitespace-pre-wrap break-all">
              {JSON.stringify(approval.arguments, null, 2)}
            </pre>
          </div>

          {/* Conversation Preview */}
          {recentMessages.length > 0 && (
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium">Recent Context</span>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowConversation(!showConversation)}
                >
                  {showConversation ? "Hide" : "Show"}
                </Button>
              </div>
              {showConversation && (
                <div className="rounded-lg border bg-muted/50 p-3 space-y-2 max-h-48 overflow-auto">
                  {recentMessages.map((msg, idx) => (
                    <div key={idx} className="text-xs break-words">
                      <span className="font-medium capitalize">{msg.role}:</span>{" "}
                      <span className="text-muted-foreground break-all">
                        {typeof msg.content === "string"
                          ? msg.content.slice(0, 150) + (msg.content.length > 150 ? "..." : "")
                          : JSON.stringify(msg.content).slice(0, 150)}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex gap-2 pt-2">
            <Button
              size="sm"
              onClick={handleApprove}
              disabled={isProcessing || timeRemaining.expired}
              className="flex-1"
            >
              <CheckCircle className="mr-2 h-4 w-4" />
              Approve
            </Button>
            <Button
              size="sm"
              variant="destructive"
              onClick={() => setShowRejectDialog(true)}
              disabled={isProcessing || timeRemaining.expired}
              className="flex-1"
            >
              <XCircle className="mr-2 h-4 w-4" />
              Reject
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={() => onViewDetails(approval)}
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Rejection Dialog */}
      <Dialog open={showRejectDialog} onOpenChange={setShowRejectDialog}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <XCircle className="h-5 w-5 text-red-600" />
              Reject Tool Call
            </DialogTitle>
            <DialogDescription>
              Provide a reason for rejecting this tool call. This will be shown to the agent.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Tool</Label>
              <div className="rounded-md border bg-muted/50 px-3 py-2 text-sm font-medium">
                {approval.tool_name}
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="reason">Rejection Reason</Label>
              <Input
                id="reason"
                placeholder="e.g., Insufficient permissions, incorrect parameters..."
                value={rejectionReason}
                onChange={(e) => setRejectionReason(e.target.value)}
                disabled={isProcessing}
              />
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setShowRejectDialog(false)}
              disabled={isProcessing}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleReject}
              disabled={!rejectionReason.trim() || isProcessing}
            >
              <XCircle className="mr-2 h-4 w-4" />
              Reject
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}

export default function ApprovalsPage() {
  const { approvals, loading, error, refetch } = useApprovals(true)
  const { approve } = useApproveToolCall()
  const { reject } = useRejectToolCall()
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [liveMode, setLiveMode] = useState(true)
  const [detailsApproval, setDetailsApproval] = useState<PendingApproval | null>(null)
  const [batchRejectOpen, setBatchRejectOpen] = useState(false)
  const [batchReason, setBatchReason] = useState("")
  const [isProcessingBatch, setIsProcessingBatch] = useState(false)

  // Live mode polling
  useEffect(() => {
    if (!liveMode) return
    const interval = setInterval(refetch, 5000)
    return () => clearInterval(interval)
  }, [liveMode, refetch])

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Only process if not in an input/textarea
      if ((e.target as HTMLElement).tagName === "INPUT" || (e.target as HTMLElement).tagName === "TEXTAREA") {
        return
      }

      if (e.key === "a" || e.key === "A") {
        // Approve all selected
        if (selectedIds.size > 0) {
          handleBatchApprove()
        }
      } else if (e.key === "r" || e.key === "R") {
        // Open reject dialog for selected
        if (selectedIds.size > 0) {
          setBatchRejectOpen(true)
        }
      } else if (e.key === "Escape") {
        setSelectedIds(new Set())
        setDetailsApproval(null)
      }
    }

    window.addEventListener("keydown", handleKeyDown)
    return () => window.removeEventListener("keydown", handleKeyDown)
  }, [selectedIds])

  const handleApprove = async (id: string) => {
    await approve(id)
    refetch()
  }

  const handleReject = async (id: string, reason: string) => {
    await reject(id, reason)
    refetch()
  }

  const handleSelect = (id: string, selected: boolean) => {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (selected) {
        next.add(id)
      } else {
        next.delete(id)
      }
      return next
    })
  }

  const handleSelectAll = (selected: boolean) => {
    if (selected) {
      setSelectedIds(new Set(approvals.map((a) => a.id)))
    } else {
      setSelectedIds(new Set())
    }
  }

  const handleBatchApprove = async () => {
    setIsProcessingBatch(true)
    try {
      await Promise.all(Array.from(selectedIds).map((id) => approve(id)))
      toast.success(`Approved ${selectedIds.size} tool call${selectedIds.size > 1 ? "s" : ""}`)
      setSelectedIds(new Set())
      refetch()
    } catch (error) {
      toast.error("Failed to approve some tool calls")
    } finally {
      setIsProcessingBatch(false)
    }
  }

  const handleBatchReject = async () => {
    if (!batchReason.trim()) return
    setIsProcessingBatch(true)
    try {
      await Promise.all(Array.from(selectedIds).map((id) => reject(id, batchReason)))
      toast.success(`Rejected ${selectedIds.size} tool call${selectedIds.size > 1 ? "s" : ""}`)
      setSelectedIds(new Set())
      setBatchRejectOpen(false)
      setBatchReason("")
      refetch()
    } catch (error) {
      toast.error("Failed to reject some tool calls")
    } finally {
      setIsProcessingBatch(false)
    }
  }

  // Count urgent approvals
  const urgentCount = approvals.filter((a) => {
    const remaining = getTimeRemaining(a.timeout_at)
    return remaining.urgent && !remaining.expired
  }).length

  if (loading) {
    return <LoadingSkeleton />
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <AlertCircle className="h-12 w-12 text-red-500 mb-4" />
        <p className="text-sm font-medium text-red-600">Failed to load approvals</p>
        <p className="text-sm text-muted-foreground">{error}</p>
        <Button variant="outline" size="sm" onClick={refetch} className="mt-4">
          <RefreshCw className="mr-2 h-4 w-4" />
          Retry
        </Button>
      </div>
    )
  }

  return (
    <div className="flex h-full flex-col space-y-6 animate-fade-in">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Approvals</h1>
          <p className="text-muted-foreground">
            Review and approve or reject pending tool calls from AI agents.
          </p>
        </div>
        <div className="flex items-center gap-4">
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
          <Button variant="outline" size="sm" onClick={refetch}>
            <RefreshCw className="mr-2 h-4 w-4" />
            Refresh
          </Button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid gap-4 md:grid-cols-3">
        <StatCard
          title="Pending Approvals"
          value={approvals.length}
          icon={AlertTriangle}
          iconColor="text-amber-500"
        />
        <StatCard
          title="Urgent"
          value={urgentCount}
          icon={Timer}
          iconColor="text-red-500"
        />
        <Card className="transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Keyboard Shortcuts
            </CardTitle>
            <Keyboard className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="flex gap-4 text-xs text-muted-foreground">
              <div className="flex items-center gap-1">
                <kbd className="px-1.5 py-0.5 bg-muted rounded text-xs font-mono">A</kbd>
                <span>Approve</span>
              </div>
              <div className="flex items-center gap-1">
                <kbd className="px-1.5 py-0.5 bg-muted rounded text-xs font-mono">R</kbd>
                <span>Reject</span>
              </div>
              <div className="flex items-center gap-1">
                <kbd className="px-1.5 py-0.5 bg-muted rounded text-xs font-mono">Esc</kbd>
                <span>Clear</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Batch Actions */}
      {selectedIds.size > 0 && (
        <Card className="border-primary/50 bg-primary/5">
          <CardContent className="flex items-center justify-between py-3">
            <div className="flex items-center gap-2">
              <Checkbox
                checked={selectedIds.size === approvals.length}
                onCheckedChange={handleSelectAll}
              />
              <span className="text-sm font-medium">
                {selectedIds.size} selected
              </span>
            </div>
            <div className="flex items-center gap-2">
              <Button
                size="sm"
                onClick={handleBatchApprove}
                disabled={isProcessingBatch}
              >
                <CheckCircle className="mr-2 h-4 w-4" />
                Approve All
              </Button>
              <Button
                size="sm"
                variant="destructive"
                onClick={() => setBatchRejectOpen(true)}
                disabled={isProcessingBatch}
              >
                <XCircle className="mr-2 h-4 w-4" />
                Reject All
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Approvals List */}
      {approvals.length === 0 ? (
        <Card>
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <CheckCircle className="h-12 w-12 text-emerald-500 mb-4" />
            <p className="text-lg font-medium">All clear!</p>
            <p className="text-sm text-muted-foreground">
              No pending approvals at this time.
            </p>
          </div>
        </Card>
      ) : (
        <ScrollArea className="flex-1">
          <div className="space-y-4 pr-4">
            {approvals.map((approval) => (
              <ApprovalCard
                key={approval.id}
                approval={approval}
                isSelected={selectedIds.has(approval.id)}
                onSelect={handleSelect}
                onApprove={handleApprove}
                onReject={handleReject}
                onViewDetails={setDetailsApproval}
              />
            ))}
          </div>
        </ScrollArea>
      )}

      {/* Details Side Panel */}
      <Sheet open={!!detailsApproval} onOpenChange={() => setDetailsApproval(null)}>
        <SheetContent className="w-[500px] sm:max-w-[500px]">
          {detailsApproval && (
            <>
              <SheetHeader>
                <SheetTitle className="flex items-center gap-2">
                  <AlertTriangle className="h-5 w-5 text-amber-600" />
                  {detailsApproval.tool_name}
                </SheetTitle>
                <SheetDescription>
                  Full details for this approval request
                </SheetDescription>
              </SheetHeader>
              <div className="mt-6 space-y-6">
                <div className="space-y-2">
                  <Label className="text-muted-foreground">Run ID</Label>
                  <code className="block text-sm bg-muted px-3 py-2 rounded-md font-mono">
                    {detailsApproval.run_id}
                  </code>
                </div>
                <div className="space-y-2">
                  <Label className="text-muted-foreground">Function</Label>
                  <code className="block text-sm bg-muted px-3 py-2 rounded-md font-mono">
                    {detailsApproval.function_id}
                  </code>
                </div>
                <div className="space-y-2">
                  <Label className="text-muted-foreground">Tool Call ID</Label>
                  <code className="block text-sm bg-muted px-3 py-2 rounded-md font-mono">
                    {detailsApproval.tool_call_id}
                  </code>
                </div>
                <div className="space-y-2">
                  <Label className="text-muted-foreground">Created</Label>
                  <p className="text-sm">{new Date(detailsApproval.created_at).toLocaleString()}</p>
                </div>
                <div className="space-y-2">
                  <Label className="text-muted-foreground">Timeout</Label>
                  <p className="text-sm">{new Date(detailsApproval.timeout_at).toLocaleString()}</p>
                </div>
                <div className="space-y-2">
                  <Label className="text-muted-foreground">Arguments</Label>
                  <pre className="rounded-lg border bg-muted/50 p-4 text-xs overflow-auto max-h-64 font-mono">
                    {JSON.stringify(detailsApproval.arguments, null, 2)}
                  </pre>
                </div>
                {detailsApproval.agent_conversation.length > 0 && (
                  <div className="space-y-2">
                    <Label className="text-muted-foreground">Full Conversation</Label>
                    <ScrollArea className="h-64 rounded-lg border">
                      <div className="p-4 space-y-3">
                        {detailsApproval.agent_conversation.map((msg, idx) => (
                          <div key={idx} className="text-sm">
                            <span className="font-medium capitalize">{msg.role}:</span>
                            <p className="text-muted-foreground mt-1 break-words">
                              {typeof msg.content === "string"
                                ? msg.content
                                : JSON.stringify(msg.content, null, 2)}
                            </p>
                          </div>
                        ))}
                      </div>
                    </ScrollArea>
                  </div>
                )}
              </div>
            </>
          )}
        </SheetContent>
      </Sheet>

      {/* Batch Reject Dialog */}
      <Dialog open={batchRejectOpen} onOpenChange={setBatchRejectOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <XCircle className="h-5 w-5 text-red-600" />
              Reject {selectedIds.size} Tool Call{selectedIds.size > 1 ? "s" : ""}
            </DialogTitle>
            <DialogDescription>
              Provide a reason for rejecting these tool calls. This will be shown to the agent.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="batch-reason">Rejection Reason</Label>
              <Input
                id="batch-reason"
                placeholder="e.g., Insufficient permissions, incorrect parameters..."
                value={batchReason}
                onChange={(e) => setBatchReason(e.target.value)}
                disabled={isProcessingBatch}
              />
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setBatchRejectOpen(false)}
              disabled={isProcessingBatch}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleBatchReject}
              disabled={!batchReason.trim() || isProcessingBatch}
            >
              <XCircle className="mr-2 h-4 w-4" />
              Reject All
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

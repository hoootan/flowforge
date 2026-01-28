"use client";

import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { CheckCircle, XCircle, Clock, AlertTriangle } from "lucide-react";
import { ScrollArea } from "@/components/ui/scroll-area";

interface PendingApproval {
  id: string;
  tool_call_id: string;
  tool_name: string;
  arguments: Record<string, any>;
  run_id: string;
  function_id: string;
  agent_conversation: any[];
  created_at: string;
}

interface ApprovalInboxProps {
  approvals: PendingApproval[];
  onApprove: (id: string) => Promise<void>;
  onReject: (id: string, reason: string) => Promise<void>;
}

function formatTime(isoString: string): string {
  const date = new Date(isoString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);

  if (diffMins < 1) return "Just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  const diffDays = Math.floor(diffHours / 24);
  return `${diffDays}d ago`;
}

function ApprovalCard({
  approval,
  onApprove,
  onReject,
}: {
  approval: PendingApproval;
  onApprove: (id: string) => Promise<void>;
  onReject: (id: string, reason: string) => Promise<void>;
}) {
  const [showApproveDialog, setShowApproveDialog] = useState(false);
  const [showRejectDialog, setShowRejectDialog] = useState(false);
  const [rejectionReason, setRejectionReason] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const [showConversation, setShowConversation] = useState(false);

  const handleApprove = async () => {
    setIsProcessing(true);
    try {
      await onApprove(approval.id);
      setShowApproveDialog(false);
    } catch (error) {
      console.error("Failed to approve:", error);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleReject = async () => {
    if (!rejectionReason.trim()) return;
    setIsProcessing(true);
    try {
      await onReject(approval.id, rejectionReason);
      setShowRejectDialog(false);
      setRejectionReason("");
    } catch (error) {
      console.error("Failed to reject:", error);
    } finally {
      setIsProcessing(false);
    }
  };

  // Get last few messages for context (may be empty if not provided by server)
  const recentMessages = (approval.agent_conversation || []).slice(-3);

  return (
    <>
      <Card className="border-l-4 border-l-yellow-500 overflow-hidden">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2 min-w-0">
              <AlertTriangle className="h-5 w-5 text-yellow-600 shrink-0" />
              <CardTitle className="text-base truncate">{approval.tool_name}</CardTitle>
            </div>
            <Badge variant="outline" className="gap-1 shrink-0">
              <Clock className="h-3 w-3" />
              {formatTime(approval.created_at)}
            </Badge>
          </div>
          <CardDescription className="text-xs truncate">
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
              onClick={() => setShowApproveDialog(true)}
              disabled={isProcessing}
              className="flex-1"
            >
              <CheckCircle className="mr-2 h-4 w-4" />
              Approve
            </Button>
            <Button
              size="sm"
              variant="destructive"
              onClick={() => setShowRejectDialog(true)}
              disabled={isProcessing}
              className="flex-1"
            >
              <XCircle className="mr-2 h-4 w-4" />
              Reject
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Approval Dialog */}
      <Dialog open={showApproveDialog} onOpenChange={setShowApproveDialog}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <CheckCircle className="h-5 w-5 text-green-600" />
              Approve Tool Call
            </DialogTitle>
            <DialogDescription>
              Confirm that you want to execute this tool call.
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
              <Label>Arguments</Label>
              <pre className="rounded-md border bg-muted/50 p-3 text-xs overflow-auto max-h-40 whitespace-pre-wrap break-all">
                {JSON.stringify(approval.arguments, null, 2)}
              </pre>
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setShowApproveDialog(false)}
              disabled={isProcessing}
            >
              Cancel
            </Button>
            <Button
              onClick={handleApprove}
              disabled={isProcessing}
            >
              <CheckCircle className="mr-2 h-4 w-4" />
              Approve
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

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
  );
}

export function ApprovalInbox({ approvals, onApprove, onReject }: ApprovalInboxProps) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Pending Approvals</CardTitle>
            <CardDescription>
              Tool calls requiring human approval before execution
            </CardDescription>
          </div>
          {approvals.length > 0 && (
            <Badge variant="secondary" className="text-base px-3 py-1">
              {approvals.length}
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {approvals.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <CheckCircle className="h-12 w-12 text-green-500 mb-4" />
            <p className="text-sm font-medium">All clear!</p>
            <p className="text-sm text-muted-foreground">
              No pending approvals at this time.
            </p>
          </div>
        ) : (
          <ScrollArea className="h-[600px]">
            <div className="space-y-4 pr-4">
              {approvals.map((approval) => (
                <ApprovalCard
                  key={approval.id}
                  approval={approval}
                  onApprove={onApprove}
                  onReject={onReject}
                />
              ))}
            </div>
          </ScrollArea>
        )}
      </CardContent>
    </Card>
  );
}

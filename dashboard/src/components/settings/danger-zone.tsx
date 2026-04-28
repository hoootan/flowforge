"use client";

import { useEffect, useState } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Shield, PauseCircle, UserCog, Trash2, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";

/**
 * Workspace danger zone.
 *
 * Three irreversible-ish actions, each behind a typed confirmation:
 * - Pause all functions (reversible: just flips Function.is_active)
 * - Transfer ownership (this admin becomes member)
 * - Delete workspace (soft-delete; routes return 410 afterwards)
 */
export function DangerZone() {
  const { user } = useAuthStore();
  const [tenantSlug, setTenantSlug] = useState<string>("");

  // Fetch workspace slug for the typed-confirmation dialog
  useEffect(() => {
    let cancelled = false;
    api.getTenantInfo().then((info) => {
      if (!cancelled && info) setTenantSlug(info.slug);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  // Pause-all dialog
  const [pauseOpen, setPauseOpen] = useState(false);
  const [pausing, setPausing] = useState(false);

  // Transfer dialog
  const [transferOpen, setTransferOpen] = useState(false);
  const [transferring, setTransferring] = useState(false);
  const [users, setUsers] = useState<{ id: string; email: string }[]>([]);
  const [targetUserId, setTargetUserId] = useState<string>("");

  // Delete dialog
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [confirmSlug, setConfirmSlug] = useState("");

  useEffect(() => {
    // Lazy-load workspace users for the transfer-target dropdown
    if (transferOpen && users.length === 0) {
      api.getUsers().then((res) => {
        if (res?.users) {
          setUsers(
            res.users
              .filter((u) => u.id !== user?.id) // exclude self
              .map((u) => ({ id: u.id, email: u.email }))
          );
        }
      });
    }
  }, [transferOpen, users.length, user?.id]);

  async function handlePauseAll() {
    setPausing(true);
    try {
      const result = await api.pauseAllFunctions();
      if (result) {
        toast.success(
          result.paused_count > 0
            ? `Paused ${result.paused_count} function${result.paused_count === 1 ? "" : "s"}.`
            : "Already paused — nothing changed."
        );
        setPauseOpen(false);
      } else {
        toast.error("Failed to pause functions.");
      }
    } finally {
      setPausing(false);
    }
  }

  async function handleTransfer() {
    if (!targetUserId) {
      toast.error("Pick a user to transfer ownership to.");
      return;
    }
    setTransferring(true);
    try {
      const result = await api.transferOwnership(targetUserId);
      if (result) {
        toast.success(`Ownership transferred to ${result.new_owner_email}.`);
        setTransferOpen(false);
        setTargetUserId("");
        // The current user is now a member; refresh state on next nav
      } else {
        toast.error("Failed to transfer ownership.");
      }
    } finally {
      setTransferring(false);
    }
  }

  async function handleDelete() {
    if (confirmSlug.trim() !== tenantSlug) {
      toast.error("Slug doesn't match — type the workspace slug exactly.");
      return;
    }
    setDeleting(true);
    try {
      const result = await api.deleteWorkspace(confirmSlug.trim());
      if (result) {
        toast.success("Workspace deleted. Signing you out…");
        setDeleteOpen(false);
        // Force a hard nav so the auth store is cleared and the user lands on /login
        setTimeout(() => {
          window.location.href = "/login";
        }, 1000);
      } else {
        toast.error("Failed to delete workspace.");
      }
    } finally {
      setDeleting(false);
    }
  }

  return (
    <Card className="border-destructive/50">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-destructive">
          <Shield className="h-5 w-5" />
          Danger Zone
        </CardTitle>
        <CardDescription>
          Irreversible workspace actions. Proceed with caution.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Pause all */}
        <div className="flex items-center justify-between rounded-lg border p-4">
          <div>
            <h4 className="font-medium flex items-center gap-2">
              <PauseCircle className="h-4 w-4" />
              Pause all functions
            </h4>
            <p className="text-sm text-muted-foreground">
              Sets every function in this workspace to inactive. New events
              still arrive, but no runs are triggered until you re-enable.
            </p>
          </div>
          <Button variant="outline" onClick={() => setPauseOpen(true)}>
            Pause all
          </Button>
        </div>

        {/* Transfer ownership */}
        <div className="flex items-center justify-between rounded-lg border p-4">
          <div>
            <h4 className="font-medium flex items-center gap-2">
              <UserCog className="h-4 w-4" />
              Transfer ownership
            </h4>
            <p className="text-sm text-muted-foreground">
              Promote another workspace member to admin. You will be demoted
              to member.
            </p>
          </div>
          <Button variant="outline" onClick={() => setTransferOpen(true)}>
            Transfer…
          </Button>
        </div>

        {/* Delete */}
        <div className="flex items-center justify-between rounded-lg border border-destructive/50 p-4">
          <div>
            <h4 className="font-medium flex items-center gap-2 text-destructive">
              <Trash2 className="h-4 w-4" />
              Delete workspace
            </h4>
            <p className="text-sm text-muted-foreground">
              Soft-deletes this workspace. All routes immediately return 410.
              Recoverable until the retention window expires.
            </p>
          </div>
          <Button variant="destructive" onClick={() => setDeleteOpen(true)}>
            Delete…
          </Button>
        </div>
      </CardContent>

      {/* Pause confirmation */}
      <Dialog open={pauseOpen} onOpenChange={setPauseOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Pause all functions?</DialogTitle>
            <DialogDescription>
              Every function in <code>{tenantSlug || "this workspace"}</code>{" "}
              will be set to inactive. You can re-enable them individually
              from the Functions page.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setPauseOpen(false)} disabled={pausing}>
              Cancel
            </Button>
            <Button onClick={handlePauseAll} disabled={pausing}>
              {pausing ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Pausing…
                </>
              ) : (
                "Pause all"
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Transfer confirmation */}
      <Dialog open={transferOpen} onOpenChange={setTransferOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Transfer workspace ownership</DialogTitle>
            <DialogDescription>
              Pick the user to promote to admin. You will be demoted to
              member immediately.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-2 py-2">
            <Label htmlFor="transfer-target">New owner</Label>
            <Select value={targetUserId} onValueChange={setTargetUserId}>
              <SelectTrigger id="transfer-target">
                <SelectValue placeholder="Choose a user…" />
              </SelectTrigger>
              <SelectContent>
                {users.length === 0 ? (
                  <SelectItem value="__empty__" disabled>
                    No other users in this workspace
                  </SelectItem>
                ) : (
                  users.map((u) => (
                    <SelectItem key={u.id} value={u.id}>
                      {u.email}
                    </SelectItem>
                  ))
                )}
              </SelectContent>
            </Select>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setTransferOpen(false)} disabled={transferring}>
              Cancel
            </Button>
            <Button
              onClick={handleTransfer}
              disabled={transferring || !targetUserId || targetUserId === "__empty__"}
            >
              {transferring ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Transferring…
                </>
              ) : (
                "Transfer"
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete confirmation */}
      <Dialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="text-destructive">
              Delete workspace?
            </DialogTitle>
            <DialogDescription>
              This soft-deletes <code>{tenantSlug}</code>. All API routes
              immediately reject auth from this workspace with HTTP 410. To
              confirm, retype the workspace slug below.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-2 py-2">
            <Label htmlFor="confirm-slug">
              Type <code>{tenantSlug}</code> to confirm
            </Label>
            <Input
              id="confirm-slug"
              value={confirmSlug}
              onChange={(e) => setConfirmSlug(e.target.value)}
              placeholder={tenantSlug}
              autoComplete="off"
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteOpen(false)} disabled={deleting}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDelete}
              disabled={deleting || confirmSlug.trim() !== tenantSlug}
            >
              {deleting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Deleting…
                </>
              ) : (
                "Delete workspace"
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  );
}

"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import { usePermissions } from "@/stores/auth-store";
import { UsersList } from "@/components/settings/users-list";
import { UserDialog } from "@/components/settings/user-dialog";
import { ApiKeysTab } from "@/components/settings/api-keys-tab";
import { AIProvidersTab } from "@/components/settings/ai-providers-tab";
import { SecurityTab } from "@/components/settings/security-tab";
import { ModelPricingTab } from "@/components/settings/model-pricing-tab";
import { AuditLogTab } from "@/components/settings/audit-log-tab";
import { CredentialsTab } from "@/components/settings/credentials-tab";
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
import { Loader2 } from "lucide-react";
import {
  api,
  DEFAULT_CONCURRENCY_SETTINGS,
  DEFAULT_NOTIFICATION_SETTINGS,
  type ConcurrencySettings,
  type NotificationSettings,
  type User,
} from "@/lib/api";

interface GeneralData {
  workspaceName: string;
  workspaceSlug: string;
  defaultEnv: string;
  timezone: string;
}

const GENERAL_DEFAULTS: GeneralData = {
  workspaceName: "flowforge",
  workspaceSlug: "flowforge",
  defaultEnv: "production",
  timezone: "UTC",
};

const GENERAL_STORAGE_KEY = "flowforge-settings-v2";

type NavId =
  | "general"
  | "members"
  | "billing"
  | "audit"
  | "concurrency"
  | "api-keys"
  | "providers"
  | "secrets"
  | "notifications"
  | "danger";

const NAV: { group: string; items: { id: NavId; label: string; adminOnly?: boolean }[] }[] = [
  {
    group: "Workspace",
    items: [
      { id: "general", label: "General" },
      { id: "members", label: "Members & access", adminOnly: true },
      { id: "billing", label: "Billing & usage" },
      { id: "audit", label: "Audit log", adminOnly: true },
    ],
  },
  {
    group: "Runtime",
    items: [{ id: "concurrency", label: "Concurrency & limits" }],
  },
  {
    group: "Integrations",
    items: [
      { id: "api-keys", label: "API keys" },
      { id: "providers", label: "Model providers" },
      { id: "secrets", label: "Secrets" },
    ],
  },
  {
    group: "Notifications",
    items: [
      { id: "notifications", label: "Alerts" },
      { id: "danger", label: "Danger zone" },
    ],
  },
];

export default function SettingsPage() {
  const { isAdmin } = usePermissions();
  const [active, setActive] = useState<NavId>("general");

  // General — workspace identity (localStorage until backend ships)
  const [general, setGeneral] = useState<GeneralData>(GENERAL_DEFAULTS);

  // Concurrency — server-backed (PATCH /tenant/concurrency)
  const [conc, setConc] = useState<ConcurrencySettings>(DEFAULT_CONCURRENCY_SETTINGS);
  const [concSaving, setConcSaving] = useState(false);

  // Notifications — server-backed (PATCH /tenant/notifications, admin-only)
  const [notif, setNotif] = useState<NotificationSettings>(DEFAULT_NOTIFICATION_SETTINGS);
  const [notifLoaded, setNotifLoaded] = useState(false);
  const [notifSaving, setNotifSaving] = useState(false);
  const [testingChannel, setTestingChannel] = useState<"slack" | "pagerduty" | null>(null);

  // Members
  const [userDialogOpen, setUserDialogOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [usersKey, setUsersKey] = useState(0);

  // Danger zone — pause / transfer / delete
  const [tenantSlug, setTenantSlug] = useState<string>("");
  const [pauseOpen, setPauseOpen] = useState(false);
  const [pausing, setPausing] = useState(false);
  const [transferOpen, setTransferOpen] = useState(false);
  const [transferring, setTransferring] = useState(false);
  const [transferUsers, setTransferUsers] = useState<{ id: string; email: string }[]>([]);
  const [targetUserId, setTargetUserId] = useState<string>("");
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [confirmSlug, setConfirmSlug] = useState("");

  // ---- bootstrapping fetches ------------------------------------------------

  useEffect(() => {
    try {
      const raw = localStorage.getItem(GENERAL_STORAGE_KEY);
      if (raw) setGeneral({ ...GENERAL_DEFAULTS, ...JSON.parse(raw) });
    } catch {
      /* noop */
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    api.getConcurrencySettings().then((s) => {
      if (!cancelled) setConc(s);
    });
    api.getNotificationSettings().then((s) => {
      if (!cancelled) {
        setNotif(s);
        setNotifLoaded(true);
      }
    });
    api.getTenantInfo().then((info) => {
      if (!cancelled && info) setTenantSlug(info.slug);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  // Lazy-load workspace user list when transfer dialog opens
  useEffect(() => {
    if (!transferOpen || transferUsers.length > 0) return;
    api.getUsers().then((res) => {
      if (res?.users) {
        setTransferUsers(res.users.map((u) => ({ id: u.id, email: u.email })));
      }
    });
  }, [transferOpen, transferUsers.length]);

  // ---- mutations ------------------------------------------------------------

  function updateGeneral<K extends keyof GeneralData>(k: K, v: GeneralData[K]) {
    setGeneral((prev) => {
      const next = { ...prev, [k]: v };
      try {
        localStorage.setItem(GENERAL_STORAGE_KEY, JSON.stringify(next));
      } catch {
        /* noop */
      }
      return next;
    });
  }

  async function persistConcurrency(patch: Partial<ConcurrencySettings>) {
    setConc((prev) => ({ ...prev, ...patch }));
    setConcSaving(true);
    try {
      const result = await api.updateConcurrencySettings(patch);
      if (result) setConc(result);
      else toast.error("Failed to save concurrency settings");
    } finally {
      setConcSaving(false);
    }
  }

  async function persistNotifications(patch: Partial<NotificationSettings>) {
    setNotif((prev) => ({ ...prev, ...patch }));
    setNotifSaving(true);
    try {
      const result = await api.updateNotificationSettings(patch);
      if (result) setNotif(result);
      else toast.error("Failed to save notification settings");
    } finally {
      setNotifSaving(false);
    }
  }

  async function handleTestNotification(channel: "slack" | "pagerduty") {
    setTestingChannel(channel);
    try {
      const result = await api.testNotification(channel);
      if (!result) toast.error("Test failed — could not reach FlowForge.");
      else if (result.ok) toast.success(result.message || "Test sent.");
      else toast.error(result.message || "Test failed.");
    } finally {
      setTestingChannel(null);
    }
  }

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
      } else {
        toast.error("Failed to transfer ownership.");
      }
    } finally {
      setTransferring(false);
    }
  }

  async function handleDeleteWorkspace() {
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

  // ---- nav --------------------------------------------------------------------

  const visibleItems = (group: typeof NAV[number]) =>
    group.items.filter((i) => !i.adminOnly || isAdmin);

  return (
    <div>
      <div className="page-hd">
        <div>
          <h1>
            Settings <em>· workspace.</em>
          </h1>
          <p>flowforge · workspace settings</p>
        </div>
      </div>

      <div className="set-grid">
        <nav className="set-nav">
          {NAV.map((g) => {
            const items = visibleItems(g);
            if (items.length === 0) return null;
            return (
              <div key={g.group}>
                <h4>{g.group}</h4>
                {items.map((it) => (
                  <a
                    key={it.id}
                    className={active === it.id ? "is-on" : ""}
                    onClick={(e) => {
                      e.preventDefault();
                      setActive(it.id);
                    }}
                  >
                    {it.label}
                  </a>
                ))}
              </div>
            );
          })}
        </nav>

        <main>
          {active === "general" && (
            <section className="set-section">
              <h2>
                General <em>workspace</em>
              </h2>
              <div className="sub">Top-level identity and defaults for this workspace.</div>
              <div className="set-card">
                <div className="set-row">
                  <div className="set-lbl">
                    Workspace name
                    <small>The display name shown in the sidebar and on shared links.</small>
                  </div>
                  <div>
                    <input
                      className="set-input"
                      value={general.workspaceName}
                      onChange={(e) => updateGeneral("workspaceName", e.target.value)}
                    />
                  </div>
                </div>
                <div className="set-row">
                  <div className="set-lbl">
                    Workspace slug
                    <small>Used in URLs. Lowercase, dashes only.</small>
                  </div>
                  <div>
                    <input
                      className="set-input"
                      value={general.workspaceSlug}
                      onChange={(e) => updateGeneral("workspaceSlug", e.target.value)}
                    />
                    <div className="set-help">
                      flowforge.dev/<b style={{ color: "var(--ink-1)" }}>{general.workspaceSlug || "—"}</b>
                    </div>
                  </div>
                </div>
                <div className="set-row">
                  <div className="set-lbl">
                    Default environment
                    <small>Which environment new functions deploy to.</small>
                  </div>
                  <div>
                    <select
                      className="set-input"
                      value={general.defaultEnv}
                      onChange={(e) => updateGeneral("defaultEnv", e.target.value)}
                    >
                      <option value="production">production</option>
                      <option value="staging">staging</option>
                      <option value="preview">preview</option>
                    </select>
                  </div>
                </div>
                <div className="set-row">
                  <div className="set-lbl">
                    Time zone
                    <small>Used for cron schedules and dashboards.</small>
                  </div>
                  <div>
                    <select
                      className="set-input"
                      value={general.timezone}
                      onChange={(e) => updateGeneral("timezone", e.target.value)}
                    >
                      <option>UTC</option>
                      <option>America/Los_Angeles</option>
                      <option>America/New_York</option>
                      <option>Europe/Berlin</option>
                      <option>Asia/Tehran</option>
                    </select>
                  </div>
                </div>
              </div>
              <div className="set-help">
                Workspace identity is stored client-side until the backend
                <code style={{ margin: "0 4px" }}>PATCH /tenant</code> endpoint ships.
              </div>
            </section>
          )}

          {active === "concurrency" && (
            <section className="set-section">
              <h2>
                Concurrency <em>& limits</em>
              </h2>
              <div className="sub">
                How aggressively the runtime parallelizes runs and steps.
                {concSaving ? " · saving…" : ""}
              </div>
              <div className="set-card">
                <div className="set-row">
                  <div className="set-lbl">
                    Max concurrent runs
                    <small>
                      Tenant-wide cap. Runs over the cap are re-queued (5s delay) until others finish.
                    </small>
                  </div>
                  <div>
                    <input
                      className="set-input"
                      style={{ maxWidth: 120 }}
                      type="number"
                      min={1}
                      defaultValue={conc.max_concurrent_runs}
                      key={`max-${conc.max_concurrent_runs}`}
                      onBlur={(e) => {
                        const v = Number(e.target.value);
                        if (v && v !== conc.max_concurrent_runs) {
                          persistConcurrency({ max_concurrent_runs: v });
                        }
                      }}
                    />
                  </div>
                </div>
                <div className="set-row">
                  <div className="set-lbl">
                    Per-function default
                    <small>Used when a Function does not declare its own concurrency limit.</small>
                  </div>
                  <div>
                    <input
                      className="set-input"
                      style={{ maxWidth: 120 }}
                      type="number"
                      min={1}
                      defaultValue={conc.per_function_default}
                      key={`pfd-${conc.per_function_default}`}
                      onBlur={(e) => {
                        const v = Number(e.target.value);
                        if (v && v !== conc.per_function_default) {
                          persistConcurrency({ per_function_default: v });
                        }
                      }}
                    />
                  </div>
                </div>
                <div className="set-row">
                  <div className="set-lbl">
                    Step timeout
                    <small>Default soft timeout for individual steps, in seconds.</small>
                  </div>
                  <div>
                    <input
                      className="set-input"
                      style={{ maxWidth: 120 }}
                      type="number"
                      min={1}
                      defaultValue={conc.default_step_timeout_s}
                      key={`sto-${conc.default_step_timeout_s}`}
                      onBlur={(e) => {
                        const v = Number(e.target.value);
                        if (v && v !== conc.default_step_timeout_s) {
                          persistConcurrency({ default_step_timeout_s: v });
                        }
                      }}
                    />
                  </div>
                </div>
                <div className="set-row">
                  <div className="set-lbl">
                    Idempotency keys
                    <small>Use the trigger event id as the default idempotency key.</small>
                  </div>
                  <div>
                    <button
                      type="button"
                      aria-label="Toggle idempotency keys"
                      className={`toggle ${conc.use_event_id_idempotency ? "on" : ""}`}
                      onClick={() =>
                        persistConcurrency({
                          use_event_id_idempotency: !conc.use_event_id_idempotency,
                        })
                      }
                    />
                  </div>
                </div>
              </div>
            </section>
          )}

          {isAdmin && active === "members" && (
            <section className="set-section">
              <h2>
                Members <em>& access</em>
              </h2>
              <div className="sub">Manage users who can access the FlowForge dashboard.</div>
              <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 10 }}>
                <button
                  className="btn btn-sm btn-primary"
                  onClick={() => {
                    setEditingUser(null);
                    setUserDialogOpen(true);
                  }}
                >
                  + Add user
                </button>
              </div>
              <UsersList
                key={usersKey}
                onEditUser={(u) => {
                  setEditingUser(u);
                  setUserDialogOpen(true);
                }}
              />
              <UserDialog
                open={userDialogOpen}
                onOpenChange={setUserDialogOpen}
                user={editingUser}
                onSuccess={() => setUsersKey((k) => k + 1)}
              />
              <div style={{ marginTop: 16 }}>
                <SecurityTab />
              </div>
            </section>
          )}

          {active === "billing" && (
            <section className="set-section">
              <h2>
                Billing <em>& usage</em>
              </h2>
              <div className="sub">Model pricing and usage metering for AI calls.</div>
              <ModelPricingTab />
            </section>
          )}

          {isAdmin && active === "audit" && (
            <section className="set-section">
              <h2>Audit log</h2>
              <div className="sub">Who did what, and when.</div>
              <AuditLogTab />
            </section>
          )}

          {active === "api-keys" && (
            <section className="set-section">
              <h2>
                API <em>keys</em>
              </h2>
              <div className="sub">Programmatic access for SDKs and CI.</div>
              <ApiKeysTab />
            </section>
          )}

          {active === "providers" && (
            <section className="set-section">
              <h2>
                Model <em>providers</em>
              </h2>
              <div className="sub">Connect provider keys so agents can call models.</div>
              <AIProvidersTab />
            </section>
          )}

          {active === "secrets" && (
            <section className="set-section">
              <h2>Secrets</h2>
              <div className="sub">Store credentials that custom tools and steps can read.</div>
              <CredentialsTab />
            </section>
          )}

          {active === "notifications" && (
            <section className="set-section">
              <h2>Notifications</h2>
              <div className="sub">
                Where alerts go when things go sideways.
                {notifSaving ? " · saving…" : ""}
              </div>
              <div className="set-card">
                <div className="set-row">
                  <div className="set-lbl">
                    Slack webhook URL
                    <small>
                      Must be on <code>hooks.slack.com</code>. Stored on the workspace, admin-only.
                    </small>
                  </div>
                  <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                    <input
                      className="set-input"
                      type="url"
                      placeholder="https://hooks.slack.com/services/…"
                      disabled={!notifLoaded}
                      defaultValue={notif.slack_webhook_url ?? ""}
                      key={`webhook-${notif.slack_webhook_url ?? "empty"}`}
                      onBlur={(e) => {
                        const v = e.target.value.trim() || null;
                        if (v !== notif.slack_webhook_url) {
                          persistNotifications({ slack_webhook_url: v });
                        }
                      }}
                    />
                    <button
                      type="button"
                      className="btn btn-sm"
                      disabled={!notif.slack_webhook_url || testingChannel === "slack"}
                      onClick={() => handleTestNotification("slack")}
                    >
                      {testingChannel === "slack" ? "Sending…" : "Test"}
                    </button>
                  </div>
                </div>
                <div className="set-row">
                  <div className="set-lbl">
                    Slack channel override
                    <small>Optional. Defaults to the channel configured in the webhook.</small>
                  </div>
                  <div>
                    <input
                      className="set-input"
                      placeholder="#flowforge-alerts"
                      disabled={!notifLoaded}
                      defaultValue={notif.slack_channel ?? ""}
                      key={`channel-${notif.slack_channel ?? "empty"}`}
                      onBlur={(e) => {
                        const v = e.target.value.trim() || null;
                        if (v !== notif.slack_channel) {
                          persistNotifications({ slack_channel: v });
                        }
                      }}
                    />
                  </div>
                </div>
                <div className="set-row">
                  <div className="set-lbl">
                    PagerDuty
                    <small>Page on critical-tier failures via Events API v2.</small>
                  </div>
                  <div>
                    <button
                      type="button"
                      aria-label="Toggle PagerDuty"
                      className={`toggle ${notif.pagerduty_enabled ? "on" : ""}`}
                      onClick={() =>
                        persistNotifications({ pagerduty_enabled: !notif.pagerduty_enabled })
                      }
                    />
                  </div>
                </div>
                <div className="set-row">
                  <div className="set-lbl">
                    PagerDuty integration key
                    <small>32-char routing key. Sent only when PagerDuty is enabled.</small>
                  </div>
                  <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                    <input
                      className="set-input"
                      type="password"
                      disabled={!notifLoaded}
                      defaultValue={notif.pagerduty_integration_key ?? ""}
                      key={`pdkey-${notif.pagerduty_integration_key ?? "empty"}`}
                      onBlur={(e) => {
                        const v = e.target.value.trim() || null;
                        if (v !== notif.pagerduty_integration_key) {
                          persistNotifications({ pagerduty_integration_key: v });
                        }
                      }}
                    />
                    <button
                      type="button"
                      className="btn btn-sm"
                      disabled={
                        !notif.pagerduty_enabled ||
                        !notif.pagerduty_integration_key ||
                        testingChannel === "pagerduty"
                      }
                      onClick={() => handleTestNotification("pagerduty")}
                    >
                      {testingChannel === "pagerduty" ? "Sending…" : "Test"}
                    </button>
                  </div>
                </div>
                <div className="set-row">
                  <div className="set-lbl">
                    Notify on run failed
                    <small>Permanent failures after retries are exhausted.</small>
                  </div>
                  <div>
                    <button
                      type="button"
                      aria-label="Toggle run-failed notifications"
                      className={`toggle ${notif.notify_on_run_failed ? "on" : ""}`}
                      onClick={() =>
                        persistNotifications({ notify_on_run_failed: !notif.notify_on_run_failed })
                      }
                    />
                  </div>
                </div>
                <div className="set-row">
                  <div className="set-lbl">
                    Notify on run timeout
                    <small>Run exceeded its configured step or function timeout.</small>
                  </div>
                  <div>
                    <button
                      type="button"
                      aria-label="Toggle run-timeout notifications"
                      className={`toggle ${notif.notify_on_run_timeout ? "on" : ""}`}
                      onClick={() =>
                        persistNotifications({ notify_on_run_timeout: !notif.notify_on_run_timeout })
                      }
                    />
                  </div>
                </div>
                <div className="set-row">
                  <div className="set-lbl">
                    Email digest
                    <small>Daily summary at 09:00 in workspace timezone.</small>
                  </div>
                  <div>
                    <button
                      type="button"
                      aria-label="Toggle email digest"
                      className={`toggle ${notif.email_digest_enabled ? "on" : ""}`}
                      onClick={() =>
                        persistNotifications({ email_digest_enabled: !notif.email_digest_enabled })
                      }
                    />
                  </div>
                </div>
              </div>
            </section>
          )}

          {active === "danger" && (
            <section className="set-section">
              <div className="set-card danger-card">
                <h3>Danger zone</h3>
                <p style={{ fontSize: 12.5, color: "var(--ink-3)", margin: "0 0 14px" }}>
                  These actions are irreversible.
                </p>
                <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                  <button className="btn" onClick={() => setPauseOpen(true)}>
                    Pause all functions
                  </button>
                  <button className="btn" onClick={() => setTransferOpen(true)}>
                    Transfer ownership
                  </button>
                  <button
                    className="btn"
                    style={{
                      color: "var(--danger)",
                      borderColor: "color-mix(in oklab, var(--danger) 40%, var(--line))",
                    }}
                    onClick={() => setDeleteOpen(true)}
                  >
                    Delete workspace
                  </button>
                </div>
              </div>
            </section>
          )}
        </main>
      </div>

      {/* Confirmation dialogs (rendered always, gated by *Open state) */}
      <Dialog open={pauseOpen} onOpenChange={setPauseOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Pause all functions?</DialogTitle>
            <DialogDescription>
              Every function in <code>{tenantSlug || "this workspace"}</code> will be set to
              inactive. You can re-enable individual functions from the Functions page.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <button className="btn" onClick={() => setPauseOpen(false)} disabled={pausing}>
              Cancel
            </button>
            <button className="btn btn-primary" onClick={handlePauseAll} disabled={pausing}>
              {pausing ? (
                <>
                  <Loader2 size={14} className="animate-spin" /> Pausing…
                </>
              ) : (
                "Pause all"
              )}
            </button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={transferOpen} onOpenChange={setTransferOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Transfer workspace ownership</DialogTitle>
            <DialogDescription>
              Pick the user to promote to admin. You will be demoted to member immediately.
            </DialogDescription>
          </DialogHeader>
          <div style={{ padding: "8px 0" }}>
            <Select value={targetUserId} onValueChange={setTargetUserId}>
              <SelectTrigger>
                <SelectValue placeholder="Choose a user…" />
              </SelectTrigger>
              <SelectContent>
                {transferUsers.length === 0 ? (
                  <SelectItem value="__empty__" disabled>
                    No other users in this workspace
                  </SelectItem>
                ) : (
                  transferUsers.map((u) => (
                    <SelectItem key={u.id} value={u.id}>
                      {u.email}
                    </SelectItem>
                  ))
                )}
              </SelectContent>
            </Select>
          </div>
          <DialogFooter>
            <button className="btn" onClick={() => setTransferOpen(false)} disabled={transferring}>
              Cancel
            </button>
            <button
              className="btn btn-primary"
              onClick={handleTransfer}
              disabled={transferring || !targetUserId || targetUserId === "__empty__"}
            >
              {transferring ? (
                <>
                  <Loader2 size={14} className="animate-spin" /> Transferring…
                </>
              ) : (
                "Transfer"
              )}
            </button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle style={{ color: "var(--danger)" }}>Delete workspace?</DialogTitle>
            <DialogDescription>
              This soft-deletes <code>{tenantSlug}</code>. All API routes will reject auth from
              this workspace with HTTP 410 immediately. Recoverable until the retention window
              expires. Retype the workspace slug below to confirm.
            </DialogDescription>
          </DialogHeader>
          <div style={{ padding: "8px 0" }}>
            <input
              className="set-input"
              value={confirmSlug}
              onChange={(e) => setConfirmSlug(e.target.value)}
              placeholder={tenantSlug}
              autoComplete="off"
            />
          </div>
          <DialogFooter>
            <button className="btn" onClick={() => setDeleteOpen(false)} disabled={deleting}>
              Cancel
            </button>
            <button
              className="btn"
              style={{
                color: "var(--danger)",
                borderColor: "color-mix(in oklab, var(--danger) 40%, var(--line))",
              }}
              onClick={handleDeleteWorkspace}
              disabled={deleting || confirmSlug.trim() !== tenantSlug}
            >
              {deleting ? (
                <>
                  <Loader2 size={14} className="animate-spin" /> Deleting…
                </>
              ) : (
                "Delete workspace"
              )}
            </button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

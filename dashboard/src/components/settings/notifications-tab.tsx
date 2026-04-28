"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Bell, Slack, AlertTriangle, Mail, Send, Loader2 } from "lucide-react";
import { toast } from "sonner";
import {
  api,
  DEFAULT_NOTIFICATION_SETTINGS,
  type NotificationSettings,
} from "@/lib/api";

/**
 * Notifications tab — manages workspace-level Slack / PagerDuty / email digest
 * settings backed by /api/v1/tenant/notifications. Used by services/notifier.py
 * to actually fire when a Run hits a terminal failure.
 */
export function NotificationsTab() {
  const [settings, setSettings] = useState<NotificationSettings>(DEFAULT_NOTIFICATION_SETTINGS);
  const [loaded, setLoaded] = useState(false);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState<"slack" | "pagerduty" | null>(null);

  // Initial fetch
  useEffect(() => {
    let cancelled = false;
    api.getNotificationSettings().then((s) => {
      if (!cancelled) {
        setSettings(s);
        setLoaded(true);
      }
    });
    return () => {
      cancelled = true;
    };
  }, []);

  /** Optimistic patch: update local state immediately, persist, surface result. */
  async function persist(patch: Partial<NotificationSettings>) {
    setSettings((prev) => ({ ...prev, ...patch }));
    setSaving(true);
    try {
      const result = await api.updateNotificationSettings(patch);
      if (result) {
        setSettings(result);
      } else {
        toast.error("Failed to save notification settings");
      }
    } finally {
      setSaving(false);
    }
  }

  async function handleTest(channel: "slack" | "pagerduty") {
    setTesting(channel);
    try {
      const result = await api.testNotification(channel);
      if (!result) {
        toast.error("Test failed — could not reach FlowForge.");
      } else if (result.ok) {
        toast.success(result.message || "Test sent.");
      } else {
        toast.error(result.message || "Test failed.");
      }
    } finally {
      setTesting(null);
    }
  }

  return (
    <div className="space-y-6">
      {/* Slack */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Slack className="h-5 w-5" />
            Slack
          </CardTitle>
          <CardDescription>
            Post run failures to a Slack channel via incoming webhook.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="slack-webhook">Incoming webhook URL</Label>
              <Input
                id="slack-webhook"
                type="url"
                placeholder="https://hooks.slack.com/services/…"
                disabled={!loaded}
                defaultValue={settings.slack_webhook_url ?? ""}
                key={`webhook-${settings.slack_webhook_url ?? "empty"}`}
                onBlur={(e) => {
                  const v = e.target.value.trim() || null;
                  if (v !== settings.slack_webhook_url) {
                    persist({ slack_webhook_url: v });
                  }
                }}
              />
              <p className="text-xs text-muted-foreground">
                Stored on the workspace. Only admins can read or edit.
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="slack-channel">Channel override (optional)</Label>
              <Input
                id="slack-channel"
                placeholder="#flowforge-alerts"
                disabled={!loaded}
                defaultValue={settings.slack_channel ?? ""}
                key={`channel-${settings.slack_channel ?? "empty"}`}
                onBlur={(e) => {
                  const v = e.target.value.trim() || null;
                  if (v !== settings.slack_channel) {
                    persist({ slack_channel: v });
                  }
                }}
              />
              <p className="text-xs text-muted-foreground">
                Defaults to the channel configured in the webhook.
              </p>
            </div>
          </div>
          <div className="flex justify-end">
            <Button
              variant="outline"
              size="sm"
              disabled={!settings.slack_webhook_url || testing === "slack"}
              onClick={() => handleTest("slack")}
            >
              {testing === "slack" ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Sending…
                </>
              ) : (
                <>
                  <Send className="mr-2 h-4 w-4" /> Send test
                </>
              )}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* PagerDuty */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5" />
            PagerDuty
          </CardTitle>
          <CardDescription>
            Page on-call when a run fails permanently.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium">Enable PagerDuty</p>
              <p className="text-sm text-muted-foreground">
                When off, the integration key is kept but no events are sent.
              </p>
            </div>
            <Switch
              disabled={!loaded}
              checked={settings.pagerduty_enabled}
              onCheckedChange={(v) => persist({ pagerduty_enabled: v })}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="pd-key">Events API v2 integration key</Label>
            <Input
              id="pd-key"
              type="password"
              placeholder="32-char routing key from PagerDuty"
              disabled={!loaded}
              defaultValue={settings.pagerduty_integration_key ?? ""}
              key={`pdkey-${settings.pagerduty_integration_key ?? "empty"}`}
              onBlur={(e) => {
                const v = e.target.value.trim() || null;
                if (v !== settings.pagerduty_integration_key) {
                  persist({ pagerduty_integration_key: v });
                }
              }}
            />
          </div>
          <div className="flex justify-end">
            <Button
              variant="outline"
              size="sm"
              disabled={
                !settings.pagerduty_enabled ||
                !settings.pagerduty_integration_key ||
                testing === "pagerduty"
              }
              onClick={() => handleTest("pagerduty")}
            >
              {testing === "pagerduty" ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Sending…
                </>
              ) : (
                <>
                  <Send className="mr-2 h-4 w-4" /> Send test
                </>
              )}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Triggers */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Bell className="h-5 w-5" />
            Triggers
          </CardTitle>
          <CardDescription>Which run events fire notifications.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium">Run failed</p>
              <p className="text-sm text-muted-foreground">
                Permanent failure after retries are exhausted.
              </p>
            </div>
            <Switch
              disabled={!loaded}
              checked={settings.notify_on_run_failed}
              onCheckedChange={(v) => persist({ notify_on_run_failed: v })}
            />
          </div>
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium">Run timed out</p>
              <p className="text-sm text-muted-foreground">
                Run exceeded its configured timeout.
              </p>
            </div>
            <Switch
              disabled={!loaded}
              checked={settings.notify_on_run_timeout}
              onCheckedChange={(v) => persist({ notify_on_run_timeout: v })}
            />
          </div>
        </CardContent>
      </Card>

      {/* Email digest */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Mail className="h-5 w-5" />
            Email digest
          </CardTitle>
          <CardDescription>Daily summary of runs &amp; failures.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium">Send a daily digest</p>
              <p className="text-sm text-muted-foreground">
                Delivery cadence is once per day at 09:00 in the workspace timezone.
              </p>
            </div>
            <Switch
              disabled={!loaded}
              checked={settings.email_digest_enabled}
              onCheckedChange={(v) => persist({ email_digest_enabled: v })}
            />
          </div>
        </CardContent>
      </Card>

      {saving && (
        <p className="text-xs text-muted-foreground text-right">Saving…</p>
      )}
    </div>
  );
}

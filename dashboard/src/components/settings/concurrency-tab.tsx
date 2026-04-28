"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Gauge, Timer, Hash, ShieldCheck } from "lucide-react";
import { toast } from "sonner";
import {
  api,
  DEFAULT_CONCURRENCY_SETTINGS,
  type ConcurrencySettings,
} from "@/lib/api";

/**
 * Concurrency & limits tab — workspace-level dispatcher knobs persisted via
 * /api/v1/tenant/concurrency and enforced by services/runner.py and
 * services/executor.py.
 */
export function ConcurrencyTab() {
  const [conc, setConc] = useState<ConcurrencySettings>(DEFAULT_CONCURRENCY_SETTINGS);
  const [loaded, setLoaded] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    let cancelled = false;
    api.getConcurrencySettings().then((s) => {
      if (!cancelled) {
        setConc(s);
        setLoaded(true);
      }
    });
    return () => {
      cancelled = true;
    };
  }, []);

  /** Optimistic update + PATCH; reconciles with the server's authoritative response. */
  async function persist(patch: Partial<ConcurrencySettings>) {
    setConc((prev) => ({ ...prev, ...patch }));
    setSaving(true);
    try {
      const result = await api.updateConcurrencySettings(patch);
      if (result) {
        setConc(result);
      } else {
        toast.error("Failed to save concurrency settings");
      }
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Gauge className="h-5 w-5" />
            Concurrency
          </CardTitle>
          <CardDescription>
            Limits how aggressively the runtime parallelizes runs and steps.
            Enforced by the runner.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="max-runs">Max concurrent runs</Label>
              <Input
                id="max-runs"
                type="number"
                min={1}
                disabled={!loaded}
                defaultValue={conc.max_concurrent_runs}
                key={`max-${conc.max_concurrent_runs}`}
                onBlur={(e) => {
                  const v = Number(e.target.value);
                  if (v && v !== conc.max_concurrent_runs) {
                    persist({ max_concurrent_runs: v });
                  }
                }}
              />
              <p className="text-xs text-muted-foreground">
                Tenant-wide cap. Runs over the cap are re-queued after a 5s
                delay until others finish.
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="per-fn">Per-function default</Label>
              <Input
                id="per-fn"
                type="number"
                min={1}
                disabled={!loaded}
                defaultValue={conc.per_function_default}
                key={`pfd-${conc.per_function_default}`}
                onBlur={(e) => {
                  const v = Number(e.target.value);
                  if (v && v !== conc.per_function_default) {
                    persist({ per_function_default: v });
                  }
                }}
              />
              <p className="text-xs text-muted-foreground">
                Used when a Function does not declare its own
                <code className="mx-1">concurrency.limit</code>.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Timer className="h-5 w-5" />
            Step timeout
          </CardTitle>
          <CardDescription>
            Soft timeout for individual steps. Falls back through:
            step → function → workspace default.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-2 max-w-sm">
            <Label htmlFor="timeout">Default step timeout (seconds)</Label>
            <Input
              id="timeout"
              type="number"
              min={1}
              disabled={!loaded}
              defaultValue={conc.default_step_timeout_s}
              key={`sto-${conc.default_step_timeout_s}`}
              onBlur={(e) => {
                const v = Number(e.target.value);
                if (v && v !== conc.default_step_timeout_s) {
                  persist({ default_step_timeout_s: v });
                }
              }}
            />
            <p className="text-xs text-muted-foreground">
              Applied to worker-mode HTTP invokes and inline AI steps.
            </p>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Hash className="h-5 w-5" />
            Idempotency
          </CardTitle>
          <CardDescription>
            Prevents duplicate runs when the broker redelivers the same event.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium">Use event id as idempotency key</p>
              <p className="text-sm text-muted-foreground">
                When on, the trigger event id becomes the run&apos;s
                <code className="mx-1">idempotency_key</code> so a redelivered
                event maps to the same logical run.
              </p>
            </div>
            <Switch
              disabled={!loaded}
              checked={conc.use_event_id_idempotency}
              onCheckedChange={(v) => persist({ use_event_id_idempotency: v })}
            />
          </div>
        </CardContent>
      </Card>

      <p className="text-xs text-muted-foreground text-right flex items-center justify-end gap-1">
        <ShieldCheck className="h-3 w-3" />
        Admin-only — saved server-side.
        {saving ? " · Saving…" : ""}
      </p>
    </div>
  );
}

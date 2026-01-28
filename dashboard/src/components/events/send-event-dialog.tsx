"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { FormField } from "@/components/forms/form-field";
import { JSONEditor, isValidJSON, parseJSON } from "@/components/forms/json-editor";
import { Loader2, Zap, ExternalLink, CheckCircle2, AlertCircle } from "lucide-react";
import Link from "next/link";
import { api, Function, Event } from "@/lib/api";

interface SendEventDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
  onError: (message: string) => void;
  prefillEvent?: Event | null;
}

export function SendEventDialog({
  open,
  onOpenChange,
  onSuccess,
  onError,
  prefillEvent,
}: SendEventDialogProps) {
  const [eventName, setEventName] = useState("");
  const [eventData, setEventData] = useState("{}");
  const [userId, setUserId] = useState("");
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [functions, setFunctions] = useState<Function[]>([]);
  const [sentEventId, setSentEventId] = useState<string | null>(null);

  const fetchFunctions = useCallback(async () => {
    const response = await api.getFunctions();
    setFunctions(response.functions.filter((f) => f.is_active && f.trigger_type === "event"));
  }, []);

  useEffect(() => {
    if (open) {
      fetchFunctions();
      setSentEventId(null);

      if (prefillEvent) {
        setEventName(prefillEvent.name);
        setEventData(JSON.stringify(prefillEvent.data, null, 2));
        setUserId(prefillEvent.user_id || "");
      } else {
        setEventName("");
        setEventData("{}");
        setUserId("");
      }
      setErrors({});
    }
  }, [open, prefillEvent, fetchFunctions]);

  const matchingFunctions = functions.filter((f) => {
    if (!eventName) return false;
    const pattern = f.trigger_value;
    if (pattern === eventName) return true;
    if (pattern.endsWith("/*")) {
      const prefix = pattern.slice(0, -2);
      return eventName.startsWith(prefix);
    }
    if (pattern.endsWith("*")) {
      const prefix = pattern.slice(0, -1);
      return eventName.startsWith(prefix);
    }
    return false;
  });

  const eventTriggers = functions.map((f) => f.trigger_value);
  const uniqueTriggers = [...new Set(eventTriggers)];

  const validate = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (!eventName.trim()) {
      newErrors.name = "Event name is required";
    }

    if (!isValidJSON(eventData)) {
      newErrors.data = "Invalid JSON";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async () => {
    if (!validate()) return;

    setLoading(true);
    const data = parseJSON(eventData) || {};

    const result = await api.sendEvent({
      name: eventName.trim(),
      data,
      user_id: userId.trim() || undefined,
    });

    setLoading(false);

    if (result) {
      setSentEventId(result.event_id);
      onSuccess();
    } else {
      onError("Failed to send event. Please try again.");
    }
  };

  const handleClose = () => {
    onOpenChange(false);
    setSentEventId(null);
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Zap className="h-5 w-5 text-amber-500" />
            {sentEventId ? "Event Sent" : "Send Event"}
          </DialogTitle>
          {!sentEventId && (
            <DialogDescription>
              Send an event to trigger registered functions
            </DialogDescription>
          )}
        </DialogHeader>

        {sentEventId ? (
          <div className="space-y-4 py-2">
            {/* Success Message */}
            <div className="flex items-start gap-3 p-4 rounded-lg bg-green-500/10 border border-green-500/20">
              <CheckCircle2 className="h-5 w-5 text-green-600 shrink-0 mt-0.5" />
              <div className="space-y-1 min-w-0">
                <p className="text-sm font-medium text-green-700 dark:text-green-400">
                  Event sent successfully
                </p>
                <p className="text-xs text-muted-foreground font-mono break-all">
                  {sentEventId}
                </p>
              </div>
            </div>

            {/* Triggered Functions */}
            {matchingFunctions.length > 0 && (
              <div className="space-y-2">
                <p className="text-sm font-medium">Triggered Functions</p>
                <div className="space-y-2">
                  {matchingFunctions.map((fn) => (
                    <div
                      key={fn.function_id}
                      className="flex items-center justify-between rounded-lg border p-3 bg-card"
                    >
                      <div className="min-w-0">
                        <p className="text-sm font-medium truncate">{fn.name}</p>
                        <p className="text-xs text-muted-foreground font-mono">{fn.trigger_value}</p>
                      </div>
                      <Link href={`/runs?function_id=${fn.function_id}`}>
                        <Button variant="ghost" size="sm" className="h-8 gap-1.5 shrink-0">
                          View Runs
                          <ExternalLink className="h-3.5 w-3.5" />
                        </Button>
                      </Link>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <DialogFooter className="gap-2 sm:gap-0">
              <Button variant="outline" onClick={() => setSentEventId(null)}>
                Send Another
              </Button>
              <Button onClick={handleClose}>Done</Button>
            </DialogFooter>
          </div>
        ) : (
          <>
            <div className="space-y-4 py-2">
              <FormField
                label="Event Name"
                required
                description="The event name that triggers functions"
                error={errors.name}
                htmlFor="event-name"
              >
                <Input
                  id="event-name"
                  value={eventName}
                  onChange={(e) => setEventName(e.target.value)}
                  placeholder="order/created"
                  disabled={loading}
                  className="font-mono h-9"
                  list="event-triggers"
                />
                <datalist id="event-triggers">
                  {uniqueTriggers.map((trigger) => (
                    <option key={trigger} value={trigger} />
                  ))}
                </datalist>
              </FormField>

              {/* Function Match Indicator */}
              {eventName && matchingFunctions.length > 0 && (
                <div className="flex items-start gap-2.5 p-3 rounded-lg bg-primary/5 border border-primary/20">
                  <CheckCircle2 className="h-4 w-4 text-primary shrink-0 mt-0.5" />
                  <div className="space-y-1.5 min-w-0">
                    <p className="text-xs font-medium text-primary">
                      Will trigger {matchingFunctions.length} function{matchingFunctions.length > 1 ? "s" : ""}
                    </p>
                    <div className="flex flex-wrap gap-1">
                      {matchingFunctions.map((fn) => (
                        <Badge key={fn.function_id} variant="secondary" className="text-[10px] font-medium">
                          {fn.name}
                        </Badge>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {eventName && matchingFunctions.length === 0 && (
                <div className="flex items-start gap-2.5 p-3 rounded-lg bg-amber-500/10 border border-amber-500/20">
                  <AlertCircle className="h-4 w-4 text-amber-600 shrink-0 mt-0.5" />
                  <p className="text-xs text-amber-700 dark:text-amber-400">
                    No active functions are configured for this event name
                  </p>
                </div>
              )}

              <FormField
                label="Event Data"
                description="JSON payload for the event"
                error={errors.data}
              >
                <JSONEditor
                  value={eventData}
                  onChange={setEventData}
                  placeholder='{\n  "order_id": "123",\n  "customer": "Alice"\n}'
                  rows={5}
                  disabled={loading}
                />
              </FormField>

              <FormField
                label="User ID"
                description="Optional user identifier"
                htmlFor="user-id"
              >
                <Input
                  id="user-id"
                  value={userId}
                  onChange={(e) => setUserId(e.target.value)}
                  placeholder="user_123"
                  disabled={loading}
                  className="font-mono h-9"
                />
              </FormField>
            </div>

            <DialogFooter className="gap-2 sm:gap-0">
              <Button variant="outline" onClick={handleClose} disabled={loading}>
                Cancel
              </Button>
              <Button onClick={handleSubmit} disabled={loading}>
                {loading ? (
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                ) : (
                  <Zap className="h-4 w-4 mr-2" />
                )}
                Send Event
              </Button>
            </DialogFooter>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}

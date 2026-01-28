"use client";

import { Input } from "@/components/ui/input";
import { FormField } from "@/components/forms/form-field";
import { Card, CardContent } from "@/components/ui/card";
import { Zap, Clock, Globe } from "lucide-react";
import { cn } from "@/lib/utils";

export type TriggerType = "event" | "cron" | "webhook";

const TRIGGER_OPTIONS = [
  {
    value: "event" as const,
    label: "Event",
    icon: Zap,
    placeholder: "order/created",
    description: "Triggered when an event is emitted",
    inputLabel: "Event Name",
  },
  {
    value: "cron" as const,
    label: "Schedule",
    icon: Clock,
    placeholder: "0 9 * * *",
    description: "Runs on a cron schedule",
    inputLabel: "Cron Expression",
  },
  {
    value: "webhook" as const,
    label: "Webhook",
    icon: Globe,
    placeholder: "/webhook/my-hook",
    description: "Triggered by HTTP request",
    inputLabel: "Webhook Path",
  },
];

interface FunctionStepIdentityProps {
  id: string;
  name: string;
  triggerType: TriggerType;
  triggerValue: string;
  onIdChange: (value: string) => void;
  onNameChange: (value: string) => void;
  onTriggerTypeChange: (value: TriggerType) => void;
  onTriggerValueChange: (value: string) => void;
  errors: Record<string, string>;
  disabled?: boolean;
  idDisabled?: boolean;
}

export function FunctionStepIdentity({
  id,
  name,
  triggerType,
  triggerValue,
  onIdChange,
  onNameChange,
  onTriggerTypeChange,
  onTriggerValueChange,
  errors,
  disabled = false,
  idDisabled = false,
}: FunctionStepIdentityProps) {
  const currentTrigger = TRIGGER_OPTIONS.find((t) => t.value === triggerType);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold mb-1">Identity & Trigger</h2>
        <p className="text-sm text-muted-foreground">
          Give your function a name and define what triggers it.
        </p>
      </div>

      {/* Basic info */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <FormField
          label="Function ID"
          required
          description={!errors.id ? (idDisabled ? "Function ID cannot be changed" : "Lowercase with hyphens (e.g., my-function)") : undefined}
          error={errors.id}
          htmlFor="function-id"
        >
          <Input
            id="function-id"
            value={id}
            onChange={(e) => onIdChange(e.target.value.toLowerCase().replace(/\s/g, "-"))}
            placeholder="my-function"
            className="font-mono h-10"
            disabled={disabled || idDisabled}
          />
        </FormField>

        <FormField
          label="Display Name"
          required
          error={errors.name}
          htmlFor="function-name"
        >
          <Input
            id="function-name"
            value={name}
            onChange={(e) => onNameChange(e.target.value)}
            placeholder="My Function"
            className="h-10"
            disabled={disabled}
          />
        </FormField>
      </div>

      {/* Trigger type */}
      <div className="space-y-3">
        <label className="text-sm font-medium">Trigger Type</label>
        <div className="grid grid-cols-3 gap-2">
          {TRIGGER_OPTIONS.map((trigger) => {
            const Icon = trigger.icon;
            const isActive = triggerType === trigger.value;

            return (
              <button
                key={trigger.value}
                type="button"
                onClick={() => onTriggerTypeChange(trigger.value)}
                disabled={disabled}
                className={cn(
                  "p-3 rounded-lg border text-center transition-all",
                  isActive
                    ? "border-primary bg-primary/5 ring-1 ring-primary/20"
                    : "border-border hover:border-primary/50 hover:bg-muted/50",
                  disabled && "opacity-50 cursor-not-allowed"
                )}
              >
                <Icon
                  className={cn(
                    "h-5 w-5 mx-auto mb-1",
                    isActive ? "text-primary" : "text-muted-foreground"
                  )}
                />
                <div className="text-sm font-medium">{trigger.label}</div>
                <div className="text-[10px] text-muted-foreground mt-0.5 hidden sm:block">
                  {trigger.description}
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Trigger value */}
      <FormField
        label={currentTrigger?.inputLabel || "Trigger Value"}
        required
        error={errors.trigger_value}
        htmlFor="trigger-value"
      >
        <Input
          id="trigger-value"
          value={triggerValue}
          onChange={(e) => onTriggerValueChange(e.target.value)}
          placeholder={currentTrigger?.placeholder}
          className="font-mono h-10"
          disabled={disabled}
        />
      </FormField>

      {/* Trigger help */}
      <Card className="bg-muted/30">
        <CardContent className="p-4 text-sm text-muted-foreground">
          {triggerType === "event" && (
            <>
              <strong className="text-foreground">Event triggers</strong> activate when a matching
              event is sent. Use patterns like <code className="font-mono bg-muted px-1 rounded">order/created</code> or{" "}
              <code className="font-mono bg-muted px-1 rounded">user/signup</code>.
            </>
          )}
          {triggerType === "cron" && (
            <>
              <strong className="text-foreground">Schedule triggers</strong> use cron expressions.
              Examples: <code className="font-mono bg-muted px-1 rounded">0 9 * * *</code> (daily at 9 AM),{" "}
              <code className="font-mono bg-muted px-1 rounded">*/5 * * * *</code> (every 5 minutes).
            </>
          )}
          {triggerType === "webhook" && (
            <>
              <strong className="text-foreground">Webhook triggers</strong> create an HTTP endpoint.
              The path you specify will be available at{" "}
              <code className="font-mono bg-muted px-1 rounded">POST /api/webhooks/[path]</code>.
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

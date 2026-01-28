"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Input } from "@/components/ui/input";
import { Shield, Code, Settings2, Check } from "lucide-react";
import type { ToolParameter } from "./tool-step-parameters";

interface ToolStepReviewProps {
  name: string;
  description: string;
  parameters: ToolParameter[];
  code: string;
  codeEnabled: boolean;
  requiresApproval: boolean;
  approvalTimeout: string;
  onRequiresApprovalChange: (value: boolean) => void;
  onApprovalTimeoutChange: (value: string) => void;
  disabled?: boolean;
}

export function ToolStepReview({
  name,
  description,
  parameters,
  code,
  codeEnabled,
  requiresApproval,
  approvalTimeout,
  onRequiresApprovalChange,
  onApprovalTimeoutChange,
  disabled = false,
}: ToolStepReviewProps) {
  const validParameters = parameters.filter((p) => p.name);
  const requiredParams = validParameters.filter((p) => p.required);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold mb-1">Review & Settings</h2>
        <p className="text-sm text-muted-foreground">
          Review your tool configuration and set approval requirements.
        </p>
      </div>

      {/* Summary */}
      <Card>
        <CardContent className="p-4 space-y-4">
          <div className="flex items-start justify-between">
            <div>
              <div className="text-sm text-muted-foreground">Tool Name</div>
              <div className="font-mono font-medium">{name || "—"}</div>
            </div>
            {name && <Check className="h-5 w-5 text-green-500" />}
          </div>

          <div>
            <div className="text-sm text-muted-foreground">Description</div>
            <div className="text-sm line-clamp-2">{description || "—"}</div>
          </div>

          <div className="flex items-center gap-4 pt-2 border-t">
            <div className="flex items-center gap-2">
              <Settings2 className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm">
                {validParameters.length} parameter{validParameters.length !== 1 ? "s" : ""}
              </span>
              {requiredParams.length > 0 && (
                <Badge variant="secondary" className="text-xs">
                  {requiredParams.length} required
                </Badge>
              )}
            </div>

            <div className="flex items-center gap-2">
              <Code className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm">
                {codeEnabled && code ? "Custom code" : "No code"}
              </span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Parameters preview */}
      {validParameters.length > 0 && (
        <div className="space-y-2">
          <div className="text-sm font-medium">Parameters</div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {validParameters.map((param) => (
              <div
                key={param.id}
                className="flex items-center justify-between p-2.5 rounded-lg bg-muted/50 text-sm"
              >
                <div className="flex items-center gap-2 min-w-0">
                  <code className="font-mono truncate">{param.name}</code>
                  <Badge variant="outline" className="text-[10px] shrink-0">
                    {param.type}
                  </Badge>
                </div>
                {param.required && (
                  <Badge variant="secondary" className="text-[10px] shrink-0">
                    required
                  </Badge>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Approval settings */}
      <Card className="bg-amber-50 dark:bg-amber-950/30 border-amber-200 dark:border-amber-900">
        <CardContent className="p-4 space-y-4">
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-start gap-3">
              <Shield className="h-5 w-5 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
              <div>
                <div className="font-medium text-amber-900 dark:text-amber-100">
                  Human Approval
                </div>
                <p className="text-sm text-amber-800 dark:text-amber-200 mt-0.5">
                  Require explicit approval before the tool executes
                </p>
              </div>
            </div>
            <Switch
              checked={requiresApproval}
              onCheckedChange={onRequiresApprovalChange}
              disabled={disabled}
            />
          </div>

          {requiresApproval && (
            <div className="flex items-center gap-3 pt-3 border-t border-amber-200 dark:border-amber-800">
              <label className="text-sm text-amber-800 dark:text-amber-200 shrink-0">
                Timeout:
              </label>
              <Input
                value={approvalTimeout}
                onChange={(e) => onApprovalTimeoutChange(e.target.value)}
                placeholder="1h"
                className="w-24 h-8 text-sm bg-white dark:bg-background"
                disabled={disabled}
              />
              <span className="text-xs text-amber-700 dark:text-amber-300">
                e.g., 30m, 1h, 1d
              </span>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

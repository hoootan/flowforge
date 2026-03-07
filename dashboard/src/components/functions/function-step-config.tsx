"use client";

import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { FormField } from "@/components/forms/form-field";
import { Card, CardContent } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { Bot, Server, ChevronRight, Settings } from "lucide-react";
import { useState } from "react";
import type { FunctionMode } from "./function-step-type";
import { MODEL_OPTIONS } from "./constants";

interface FunctionStepConfigProps {
  mode: FunctionMode;
  // AI Agent fields
  model: string;
  systemPrompt: string;
  onModelChange: (value: string) => void;
  onSystemPromptChange: (value: string) => void;
  // Worker fields
  endpointUrl: string;
  onEndpointUrlChange: (value: string) => void;
  errors: Record<string, string>;
  disabled?: boolean;
}

export function FunctionStepConfig({
  mode,
  model,
  systemPrompt,
  onModelChange,
  onSystemPromptChange,
  endpointUrl,
  onEndpointUrlChange,
  errors,
  disabled = false,
}: FunctionStepConfigProps) {
  const [showAdvanced, setShowAdvanced] = useState(false);

  if (mode === "inline") {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
            <Bot className="h-5 w-5 text-primary" />
          </div>
          <div>
            <h2 className="text-lg font-semibold">AI Agent Configuration</h2>
            <p className="text-sm text-muted-foreground">
              Configure how the AI agent processes incoming data.
            </p>
          </div>
        </div>

        <FormField label="Model" required htmlFor="model-select">
          <Select value={model} onValueChange={onModelChange} disabled={disabled}>
            <SelectTrigger id="model-select" className="h-10">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {MODEL_OPTIONS.map((opt) => (
                <SelectItem key={opt.value} value={opt.value}>
                  <div className="flex items-center gap-2">
                    <span>{opt.label}</span>
                    <span className="text-xs text-muted-foreground">- {opt.desc}</span>
                  </div>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </FormField>

        <FormField
          label="Instructions"
          required
          description={
            !errors.system_prompt
              ? "Tell the AI what to do when triggered. Be specific about steps and tool usage."
              : undefined
          }
          error={errors.system_prompt}
          htmlFor="system-prompt"
        >
          <Textarea
            id="system-prompt"
            value={systemPrompt}
            onChange={(e) => onSystemPromptChange(e.target.value)}
            placeholder="You are an assistant that processes incoming data. When triggered, analyze the payload and take appropriate action using the available tools..."
            rows={8}
            className="resize-none text-sm leading-relaxed"
            disabled={disabled}
          />
        </FormField>

        {/* Advanced settings */}
        <Collapsible open={showAdvanced} onOpenChange={setShowAdvanced}>
          <CollapsibleTrigger asChild>
            <button
              type="button"
              className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              <ChevronRight
                className={`h-4 w-4 transition-transform ${showAdvanced ? "rotate-90" : ""}`}
              />
              <Settings className="h-4 w-4" />
              Advanced Settings
            </button>
          </CollapsibleTrigger>
          <CollapsibleContent className="mt-4">
            <Card className="bg-muted/30">
              <CardContent className="p-4 space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <FormField label="Max Iterations" htmlFor="max-iterations">
                    <Input
                      id="max-iterations"
                      type="number"
                      defaultValue={30}
                      className="h-9"
                      disabled={disabled}
                    />
                  </FormField>
                  <FormField label="Max Tool Calls" htmlFor="max-tool-calls">
                    <Input
                      id="max-tool-calls"
                      type="number"
                      defaultValue={50}
                      className="h-9"
                      disabled={disabled}
                    />
                  </FormField>
                </div>
                <p className="text-xs text-muted-foreground">
                  These limits prevent runaway agents. The agent will stop if either limit is reached.
                </p>
              </CardContent>
            </Card>
          </CollapsibleContent>
        </Collapsible>
      </div>
    );
  }

  // Worker mode
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-lg bg-muted flex items-center justify-center">
          <Server className="h-5 w-5 text-muted-foreground" />
        </div>
        <div>
          <h2 className="text-lg font-semibold">Worker Configuration</h2>
          <p className="text-sm text-muted-foreground">
            Configure where to send incoming data for processing.
          </p>
        </div>
      </div>

      <FormField
        label="Endpoint URL"
        required
        description={!errors.endpoint_url ? "Receives POST requests with JSON payload" : undefined}
        error={errors.endpoint_url}
        htmlFor="endpoint-url"
      >
        <Input
          id="endpoint-url"
          value={endpointUrl}
          onChange={(e) => onEndpointUrlChange(e.target.value)}
          placeholder="https://your-server.com/api/webhook"
          className="font-mono h-10"
          disabled={disabled}
        />
      </FormField>

      <Card className="bg-muted/30">
        <CardContent className="p-4">
          <h4 className="font-medium text-sm mb-2">Request Format</h4>
          <pre className="text-xs font-mono bg-muted p-3 rounded overflow-auto">
{`POST /your-endpoint
Content-Type: application/json

{
  "event": {
    "name": "order/created",
    "data": { ... },
    "timestamp": "2024-01-15T10:30:00Z"
  },
  "run_id": "run_abc123",
  "function_id": "your-function"
}`}
          </pre>
          <p className="text-xs text-muted-foreground mt-3">
            Your endpoint should return a JSON response. The response body becomes the function output.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}

"use client";

import { useState, useEffect } from "react";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { FormField } from "@/components/forms/form-field";
import { JSONEditor, isValidJSON, parseJSON } from "@/components/forms/json-editor";
import { Loader2, X } from "lucide-react";
import { Function, Tool } from "@/lib/api";

export interface InlineFunctionFormData {
  mode: "inline";
  id: string;
  name: string;
  trigger_type: "event" | "cron" | "webhook";
  trigger_value: string;
  system_prompt: string;
  tools: string[];
  agent_config: {
    model: string;
    max_iterations: number;
    max_tool_calls: number;
  };
}

export interface WorkerFunctionFormData {
  mode: "worker";
  id: string;
  name: string;
  trigger_type: "event" | "cron" | "webhook";
  trigger_value: string;
  endpoint_url: string;
  config: Record<string, unknown>;
}

export type FunctionFormData = InlineFunctionFormData | WorkerFunctionFormData;

interface FunctionFormProps {
  func?: Function | null;
  availableTools: Tool[];
  onSubmit: (data: FunctionFormData) => Promise<void>;
  onCancel: () => void;
  loading?: boolean;
}

const MODEL_OPTIONS = [
  { value: "claude-sonnet-4-5-20250514", label: "Claude Sonnet 4.5" },
  { value: "claude-3-5-sonnet-20241022", label: "Claude 3.5 Sonnet" },
  { value: "gpt-4o", label: "GPT-4o" },
  { value: "gpt-4o-mini", label: "GPT-4o Mini" },
];

export function FunctionForm({
  func,
  availableTools,
  onSubmit,
  onCancel,
  loading = false,
}: FunctionFormProps) {
  const isEdit = !!func;
  const initialMode = func?.is_inline !== false ? "inline" : "worker";

  const [mode, setMode] = useState<"inline" | "worker">(initialMode);
  const [id, setId] = useState("");
  const [name, setName] = useState("");
  const [triggerType, setTriggerType] = useState<"event" | "cron" | "webhook">("event");
  const [triggerValue, setTriggerValue] = useState("");

  // Inline mode fields
  const [systemPrompt, setSystemPrompt] = useState("");
  const [selectedTools, setSelectedTools] = useState<string[]>([]);
  const [model, setModel] = useState("claude-sonnet-4-5-20250514");
  const [maxIterations, setMaxIterations] = useState(30);
  const [maxToolCalls, setMaxToolCalls] = useState(50);

  // Worker mode fields
  const [endpointUrl, setEndpointUrl] = useState("");
  const [configJson, setConfigJson] = useState("{}");

  const [errors, setErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    if (func) {
      setMode(func.is_inline ? "inline" : "worker");
      setId(func.function_id);
      setName(func.name);
      setTriggerType(func.trigger_type);
      setTriggerValue(func.trigger_value);

      if (func.is_inline) {
        setSystemPrompt(func.system_prompt || "");
        setSelectedTools(func.tools_config || []);
        const agentConfig = func.agent_config as Record<string, unknown> | null;
        if (agentConfig) {
          setModel((agentConfig.model as string) || "claude-sonnet-4-5-20250514");
          setMaxIterations((agentConfig.max_iterations as number) || 30);
          setMaxToolCalls((agentConfig.max_tool_calls as number) || 50);
        }
      } else {
        setEndpointUrl(func.endpoint_url || "");
        setConfigJson(JSON.stringify(func.config || {}, null, 2));
      }
    }
  }, [func]);

  const validate = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (!id.trim()) {
      newErrors.id = "ID is required";
    } else if (!/^[a-z][a-z0-9_-]*$/.test(id)) {
      newErrors.id = "ID must be lowercase, start with a letter, and contain only letters, numbers, hyphens, and underscores";
    }

    if (!name.trim()) {
      newErrors.name = "Name is required";
    }

    if (!triggerValue.trim()) {
      newErrors.trigger_value = "Trigger value is required";
    }

    if (mode === "inline") {
      if (!systemPrompt.trim()) {
        newErrors.system_prompt = "System prompt is required";
      }
    } else {
      if (!endpointUrl.trim()) {
        newErrors.endpoint_url = "Endpoint URL is required";
      } else {
        try {
          new URL(endpointUrl);
        } catch {
          newErrors.endpoint_url = "Invalid URL";
        }
      }
      if (!isValidJSON(configJson)) {
        newErrors.config = "Invalid JSON";
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validate()) return;

    if (mode === "inline") {
      await onSubmit({
        mode: "inline",
        id: id.trim(),
        name: name.trim(),
        trigger_type: triggerType,
        trigger_value: triggerValue.trim(),
        system_prompt: systemPrompt.trim(),
        tools: selectedTools,
        agent_config: {
          model,
          max_iterations: maxIterations,
          max_tool_calls: maxToolCalls,
        },
      });
    } else {
      const config = parseJSON(configJson) || {};
      await onSubmit({
        mode: "worker",
        id: id.trim(),
        name: name.trim(),
        trigger_type: triggerType,
        trigger_value: triggerValue.trim(),
        endpoint_url: endpointUrl.trim(),
        config,
      });
    }
  };

  const handleAddTool = (toolName: string) => {
    if (!selectedTools.includes(toolName)) {
      setSelectedTools([...selectedTools, toolName]);
    }
  };

  const handleRemoveTool = (toolName: string) => {
    setSelectedTools(selectedTools.filter((t) => t !== toolName));
  };

  const activeTools = availableTools.filter((t) => t.is_active);

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <Tabs value={mode} onValueChange={(v) => setMode(v as "inline" | "worker")}>
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="inline" disabled={isEdit}>
            Serverless (Agent)
          </TabsTrigger>
          <TabsTrigger value="worker" disabled={isEdit}>
            Worker
          </TabsTrigger>
        </TabsList>

        {/* Common Fields */}
        <div className="mt-6 space-y-4">
          <FormField
            label="Function ID"
            required
            description="Unique identifier (lowercase, hyphens allowed)"
            error={errors.id}
            htmlFor="function-id"
          >
            <Input
              id="function-id"
              value={id}
              onChange={(e) => setId(e.target.value)}
              placeholder="my-function"
              disabled={loading || isEdit}
              className="font-mono"
            />
          </FormField>

          <FormField
            label="Name"
            required
            description="Human-readable name for the function"
            error={errors.name}
            htmlFor="function-name"
          >
            <Input
              id="function-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="My Function"
              disabled={loading}
            />
          </FormField>

          <div className="grid grid-cols-2 gap-4">
            <FormField
              label="Trigger Type"
              required
              htmlFor="trigger-type"
            >
              <Select
                value={triggerType}
                onValueChange={(v) => setTriggerType(v as "event" | "cron" | "webhook")}
                disabled={loading}
              >
                <SelectTrigger id="trigger-type">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="event">Event</SelectItem>
                  <SelectItem value="cron">Cron</SelectItem>
                  <SelectItem value="webhook">Webhook</SelectItem>
                </SelectContent>
              </Select>
            </FormField>

            <FormField
              label="Trigger Value"
              required
              description={
                triggerType === "event"
                  ? "Event name pattern"
                  : triggerType === "cron"
                  ? "Cron expression"
                  : "Webhook path"
              }
              error={errors.trigger_value}
              htmlFor="trigger-value"
            >
              <Input
                id="trigger-value"
                value={triggerValue}
                onChange={(e) => setTriggerValue(e.target.value)}
                placeholder={
                  triggerType === "event"
                    ? "order/created"
                    : triggerType === "cron"
                    ? "0 9 * * *"
                    : "/webhook/my-hook"
                }
                disabled={loading}
                className="font-mono"
              />
            </FormField>
          </div>
        </div>

        {/* Serverless Mode Fields */}
        <TabsContent value="inline" className="mt-6 space-y-4">
          <FormField
            label="System Prompt"
            required
            description="Instructions for the AI agent"
            error={errors.system_prompt}
            htmlFor="system-prompt"
          >
            <Textarea
              id="system-prompt"
              value={systemPrompt}
              onChange={(e) => setSystemPrompt(e.target.value)}
              placeholder="You are a helpful assistant that..."
              rows={6}
              disabled={loading}
            />
          </FormField>

          <FormField
            label="Tools"
            description="Select tools available to the agent"
          >
            <div className="space-y-3">
              <Select onValueChange={handleAddTool} disabled={loading}>
                <SelectTrigger>
                  <SelectValue placeholder="Add a tool..." />
                </SelectTrigger>
                <SelectContent>
                  {activeTools
                    .filter((t) => !selectedTools.includes(t.name))
                    .map((tool) => (
                      <SelectItem key={tool.name} value={tool.name}>
                        <div className="flex items-center gap-2">
                          <span className="font-mono">{tool.name}</span>
                          {tool.is_builtin && (
                            <Badge variant="secondary" className="text-xs">built-in</Badge>
                          )}
                        </div>
                      </SelectItem>
                    ))}
                </SelectContent>
              </Select>
              {selectedTools.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {selectedTools.map((toolName) => (
                    <Badge key={toolName} variant="secondary" className="gap-1 pr-1">
                      <span className="font-mono">{toolName}</span>
                      <button
                        type="button"
                        onClick={() => handleRemoveTool(toolName)}
                        className="ml-1 rounded-full p-0.5 hover:bg-muted"
                        disabled={loading}
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </Badge>
                  ))}
                </div>
              )}
            </div>
          </FormField>

          <div className="space-y-4 rounded-lg border p-4">
            <h4 className="font-medium">Agent Configuration</h4>
            <div className="grid grid-cols-3 gap-4">
              <FormField label="Model" htmlFor="model">
                <Select
                  value={model}
                  onValueChange={setModel}
                  disabled={loading}
                >
                  <SelectTrigger id="model">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {MODEL_OPTIONS.map((opt) => (
                      <SelectItem key={opt.value} value={opt.value}>
                        {opt.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </FormField>

              <FormField label="Max Iterations" htmlFor="max-iterations">
                <Input
                  id="max-iterations"
                  type="number"
                  min={1}
                  max={100}
                  value={maxIterations}
                  onChange={(e) => setMaxIterations(parseInt(e.target.value) || 30)}
                  disabled={loading}
                />
              </FormField>

              <FormField label="Max Tool Calls" htmlFor="max-tool-calls">
                <Input
                  id="max-tool-calls"
                  type="number"
                  min={1}
                  max={200}
                  value={maxToolCalls}
                  onChange={(e) => setMaxToolCalls(parseInt(e.target.value) || 50)}
                  disabled={loading}
                />
              </FormField>
            </div>
          </div>
        </TabsContent>

        {/* Worker Mode Fields */}
        <TabsContent value="worker" className="mt-6 space-y-4">
          <FormField
            label="Endpoint URL"
            required
            description="HTTP endpoint that will receive function invocations"
            error={errors.endpoint_url}
            htmlFor="endpoint-url"
          >
            <Input
              id="endpoint-url"
              type="url"
              value={endpointUrl}
              onChange={(e) => setEndpointUrl(e.target.value)}
              placeholder="https://my-worker.example.com/function"
              disabled={loading}
              className="font-mono"
            />
          </FormField>

          <FormField
            label="Configuration"
            description="Additional configuration passed to the worker"
            error={errors.config}
          >
            <JSONEditor
              value={configJson}
              onChange={setConfigJson}
              placeholder='{\n  "timeout": 30000,\n  "retries": 3\n}'
              rows={6}
              disabled={loading}
            />
          </FormField>
        </TabsContent>
      </Tabs>

      <div className="flex justify-end gap-3 pt-4 border-t">
        <Button type="button" variant="outline" onClick={onCancel} disabled={loading}>
          Cancel
        </Button>
        <Button type="submit" disabled={loading}>
          {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          {isEdit ? "Save Changes" : "Create Function"}
        </Button>
      </div>
    </form>
  );
}

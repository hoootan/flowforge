"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Loader2,
  X,
  Sparkles,
  Bot,
  Server,
  Zap,
  Clock,
  Globe,
  Workflow,
} from "lucide-react";
import { api, Tool } from "@/lib/api";

interface CreateFunctionDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
  onError: (message: string) => void;
}

const MODEL_OPTIONS = [
  { value: "claude-sonnet-4-5-20250514", label: "Claude 4.5 Sonnet" },
  { value: "claude-3-5-sonnet-20241022", label: "Claude 3.5 Sonnet" },
  { value: "gpt-4o", label: "GPT-4o" },
  { value: "gpt-4o-mini", label: "GPT-4o Mini" },
];

const TRIGGER_TYPES = [
  { value: "event", label: "Event", icon: Zap, placeholder: "order/created", desc: "Triggered by events" },
  { value: "cron", label: "Schedule", icon: Clock, placeholder: "0 9 * * *", desc: "Runs on schedule" },
  { value: "webhook", label: "Webhook", icon: Globe, placeholder: "/webhook/my-hook", desc: "HTTP requests" },
];

const FUNCTION_EXAMPLES = [
  {
    name: "Order Processor",
    id: "process-order",
    trigger_type: "event" as const,
    trigger_value: "order/created",
    system_prompt: "You are an order processing assistant. When a new order comes in, verify the order details, check inventory, and notify the customer about their order status.",
    desc: "Process new orders automatically",
  },
  {
    name: "Daily Report",
    id: "daily-report",
    trigger_type: "cron" as const,
    trigger_value: "0 9 * * *",
    system_prompt: "You are a reporting assistant. Generate a daily summary report of key metrics and send it to the team.",
    desc: "Generate reports at 9 AM",
  },
  {
    name: "Support Bot",
    id: "support-bot",
    trigger_type: "webhook" as const,
    trigger_value: "/webhook/support",
    system_prompt: "You are a helpful customer support agent. Answer customer questions, help resolve issues, and escalate complex problems when needed.",
    desc: "Handle customer inquiries",
  },
];

export function CreateFunctionDialog({
  open,
  onOpenChange,
  onSuccess,
  onError,
}: CreateFunctionDialogProps) {
  const [tools, setTools] = useState<Tool[]>([]);
  const [loading, setLoading] = useState(false);

  const [mode, setMode] = useState<"inline" | "worker">("inline");
  const [id, setId] = useState("");
  const [name, setName] = useState("");
  const [triggerType, setTriggerType] = useState<"event" | "cron" | "webhook">("event");
  const [triggerValue, setTriggerValue] = useState("");
  const [systemPrompt, setSystemPrompt] = useState("");
  const [selectedTools, setSelectedTools] = useState<string[]>([]);
  const [model, setModel] = useState("claude-sonnet-4-5-20250514");
  const [endpointUrl, setEndpointUrl] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});

  const fetchTools = useCallback(async () => {
    const response = await api.getTools();
    setTools(response.tools);
  }, []);

  useEffect(() => {
    if (open) fetchTools();
  }, [open, fetchTools]);

  const resetForm = () => {
    setMode("inline");
    setId("");
    setName("");
    setTriggerType("event");
    setTriggerValue("");
    setSystemPrompt("");
    setSelectedTools([]);
    setModel("claude-sonnet-4-5-20250514");
    setEndpointUrl("");
    setErrors({});
  };

  const applyExample = (example: typeof FUNCTION_EXAMPLES[0]) => {
    setId(example.id);
    setName(example.name);
    setTriggerType(example.trigger_type);
    setTriggerValue(example.trigger_value);
    setSystemPrompt(example.system_prompt);
    setMode("inline");
  };

  const handleAddTool = (toolName: string) => {
    if (!selectedTools.includes(toolName)) {
      setSelectedTools([...selectedTools, toolName]);
    }
  };

  const handleRemoveTool = (toolName: string) => {
    setSelectedTools(selectedTools.filter((t) => t !== toolName));
  };

  const validate = (): boolean => {
    const newErrors: Record<string, string> = {};
    if (!id.trim()) newErrors.id = "Required";
    else if (!/^[a-z][a-z0-9_-]*$/.test(id)) newErrors.id = "Lowercase with hyphens only";
    if (!name.trim()) newErrors.name = "Required";
    if (!triggerValue.trim()) newErrors.trigger_value = "Required";
    if (mode === "inline" && !systemPrompt.trim()) newErrors.system_prompt = "Required";
    if (mode === "worker") {
      if (!endpointUrl.trim()) newErrors.endpoint_url = "Required";
      else { try { new URL(endpointUrl); } catch { newErrors.endpoint_url = "Invalid URL"; } }
    }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;
    setLoading(true);

    let result;
    if (mode === "inline") {
      result = await api.createInlineFunction({
        id: id.trim(),
        name: name.trim(),
        trigger: { type: triggerType, value: triggerValue.trim() },
        system_prompt: systemPrompt.trim(),
        tools: selectedTools,
        agent_config: { model, max_iterations: 30, max_tool_calls: 50 },
      });
    } else {
      result = await api.createWorkerFunction({
        id: id.trim(),
        name: name.trim(),
        trigger: { type: triggerType, value: triggerValue.trim() },
        endpoint_url: endpointUrl.trim(),
        config: {},
      });
    }

    setLoading(false);
    if (result) {
      resetForm();
      onSuccess();
      onOpenChange(false);
    } else {
      onError("Failed to create function");
    }
  };

  const activeTools = tools.filter((t) => t.is_active);
  const currentTrigger = TRIGGER_TYPES.find((t) => t.value === triggerType);

  return (
    <Dialog open={open} onOpenChange={(isOpen) => { if (!isOpen) resetForm(); onOpenChange(isOpen); }}>
      <DialogContent className="max-w-[90vw] w-[1400px] p-0 gap-0 overflow-hidden">
        <div className="grid grid-cols-[320px_1fr_1fr]">
          {/* Left Sidebar - Examples & Mode */}
          <div className="bg-muted/40 p-8 border-r">
            <div className="flex items-center gap-2 mb-6">
              <Sparkles className="h-5 w-5 text-blue-500" />
              <span className="font-semibold">Templates</span>
            </div>
            <div className="space-y-3">
              {FUNCTION_EXAMPLES.map((example) => {
                const TriggerIcon = TRIGGER_TYPES.find((t) => t.value === example.trigger_type)?.icon || Zap;
                return (
                  <button
                    key={example.id}
                    type="button"
                    onClick={() => applyExample(example)}
                    className="w-full text-left p-4 rounded-xl border-2 border-transparent bg-background hover:border-blue-400 hover:shadow-md transition-all"
                  >
                    <div className="flex items-center gap-2">
                      <TriggerIcon className="h-4 w-4 text-muted-foreground" />
                      <span className="font-semibold text-sm">{example.name}</span>
                    </div>
                    <div className="text-xs text-muted-foreground mt-1">{example.desc}</div>
                    <Badge variant="secondary" className="mt-3 text-[10px] font-mono">
                      {example.trigger_value}
                    </Badge>
                  </button>
                );
              })}
            </div>

            {/* Function Type */}
            <div className="mt-8 pt-6 border-t">
              <span className="text-sm font-medium mb-4 block">Function Type</span>
              <div className="grid grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={() => setMode("inline")}
                  className={`p-4 rounded-xl border-2 text-center transition-all ${
                    mode === "inline" ? "border-blue-500 bg-blue-500/10" : "border-transparent bg-background hover:border-muted-foreground/30"
                  }`}
                >
                  <Bot className={`h-6 w-6 mx-auto mb-2 ${mode === "inline" ? "text-blue-500" : "text-muted-foreground"}`} />
                  <div className="text-sm font-medium">AI Agent</div>
                  <div className="text-[10px] text-muted-foreground mt-1">Uses AI + tools</div>
                </button>
                <button
                  type="button"
                  onClick={() => setMode("worker")}
                  className={`p-4 rounded-xl border-2 text-center transition-all ${
                    mode === "worker" ? "border-blue-500 bg-blue-500/10" : "border-transparent bg-background hover:border-muted-foreground/30"
                  }`}
                >
                  <Server className={`h-6 w-6 mx-auto mb-2 ${mode === "worker" ? "text-blue-500" : "text-muted-foreground"}`} />
                  <div className="text-sm font-medium">Worker</div>
                  <div className="text-[10px] text-muted-foreground mt-1">Your endpoint</div>
                </button>
              </div>
            </div>
          </div>

          {/* Middle - Function Info */}
          <div className="p-8 border-r">
            <DialogHeader className="mb-6">
              <DialogTitle className="flex items-center gap-2 text-xl">
                <Workflow className="h-5 w-5" />
                Create Function
              </DialogTitle>
            </DialogHeader>

            <form onSubmit={handleSubmit} className="space-y-5">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-medium mb-2 block">Function ID</label>
                  <Input
                    value={id}
                    onChange={(e) => setId(e.target.value.toLowerCase().replace(/\s/g, "-"))}
                    placeholder="my-function"
                    className="font-mono h-11"
                    disabled={loading}
                  />
                  {errors.id && <p className="text-xs text-red-500 mt-1">{errors.id}</p>}
                </div>
                <div>
                  <label className="text-sm font-medium mb-2 block">Display Name</label>
                  <Input
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="My Function"
                    className="h-11"
                    disabled={loading}
                  />
                  {errors.name && <p className="text-xs text-red-500 mt-1">{errors.name}</p>}
                </div>
              </div>

              {/* Trigger */}
              <div className="p-4 rounded-xl border bg-muted/30">
                <label className="text-sm font-medium mb-3 block">Trigger</label>
                <div className="grid grid-cols-3 gap-2 mb-4">
                  {TRIGGER_TYPES.map((trigger) => {
                    const Icon = trigger.icon;
                    return (
                      <button
                        key={trigger.value}
                        type="button"
                        onClick={() => setTriggerType(trigger.value as typeof triggerType)}
                        className={`p-3 rounded-lg border text-center transition-all ${
                          triggerType === trigger.value ? "border-blue-500 bg-blue-500/10" : "hover:bg-muted"
                        }`}
                      >
                        <Icon className={`h-4 w-4 mx-auto mb-1 ${triggerType === trigger.value ? "text-blue-500" : "text-muted-foreground"}`} />
                        <div className="text-xs font-medium">{trigger.label}</div>
                      </button>
                    );
                  })}
                </div>
                <Input
                  value={triggerValue}
                  onChange={(e) => setTriggerValue(e.target.value)}
                  placeholder={currentTrigger?.placeholder}
                  className="font-mono h-11"
                  disabled={loading}
                />
                {errors.trigger_value && <p className="text-xs text-red-500 mt-1">{errors.trigger_value}</p>}
                <p className="text-xs text-muted-foreground mt-2">{currentTrigger?.desc}</p>
              </div>

              {mode === "worker" && (
                <div>
                  <label className="text-sm font-medium mb-2 block">Endpoint URL</label>
                  <Input
                    value={endpointUrl}
                    onChange={(e) => setEndpointUrl(e.target.value)}
                    placeholder="https://your-server.com/webhook"
                    className="font-mono h-11"
                    disabled={loading}
                  />
                  {errors.endpoint_url && <p className="text-xs text-red-500 mt-1">{errors.endpoint_url}</p>}
                </div>
              )}

              {mode === "inline" && (
                <div>
                  <label className="text-sm font-medium mb-2 block">AI Model</label>
                  <Select value={model} onValueChange={setModel}>
                    <SelectTrigger className="h-11">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {MODEL_OPTIONS.map((opt) => (
                        <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              )}

              <div className="flex justify-end gap-3 pt-4">
                <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={loading}>
                  Cancel
                </Button>
                <Button type="submit" disabled={loading} className="min-w-[140px]">
                  {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : "Create Function"}
                </Button>
              </div>
            </form>
          </div>

          {/* Right - Instructions & Tools */}
          <div className="p-6 bg-muted/20">
            {mode === "inline" ? (
              <>
                <div className="mb-6">
                  <h3 className="font-semibold">AI Instructions</h3>
                  <p className="text-xs text-muted-foreground mt-1">Tell the AI what to do when triggered</p>
                </div>
                <Textarea
                  value={systemPrompt}
                  onChange={(e) => setSystemPrompt(e.target.value)}
                  placeholder="You are a helpful assistant that processes incoming requests. When triggered, analyze the data and take appropriate actions..."
                  rows={8}
                  className="resize-none mb-6"
                  disabled={loading}
                />
                {errors.system_prompt && <p className="text-xs text-red-500 mb-4">{errors.system_prompt}</p>}

                <div className="mb-4">
                  <h3 className="font-semibold">Available Tools</h3>
                  <p className="text-xs text-muted-foreground mt-1">Tools the AI can use</p>
                </div>
                <Select onValueChange={handleAddTool}>
                  <SelectTrigger className="h-11 mb-4">
                    <SelectValue placeholder="Add a tool..." />
                  </SelectTrigger>
                  <SelectContent>
                    {activeTools
                      .filter((t) => !selectedTools.includes(t.name))
                      .map((tool) => (
                        <SelectItem key={tool.name} value={tool.name}>
                          <span className="font-mono text-sm">{tool.name}</span>
                        </SelectItem>
                      ))}
                  </SelectContent>
                </Select>

                <ScrollArea className="h-[120px]">
                  {selectedTools.length > 0 ? (
                    <div className="flex flex-wrap gap-2">
                      {selectedTools.map((toolName) => (
                        <Badge key={toolName} variant="secondary" className="gap-1 pr-1 py-1.5 text-sm">
                          {toolName}
                          <button
                            type="button"
                            onClick={() => handleRemoveTool(toolName)}
                            className="ml-1 rounded-full p-0.5 hover:bg-muted-foreground/20"
                          >
                            <X className="h-3 w-3" />
                          </button>
                        </Badge>
                      ))}
                    </div>
                  ) : (
                    <div className="text-center py-6 text-muted-foreground text-sm">
                      No tools selected
                    </div>
                  )}
                </ScrollArea>
              </>
            ) : (
              <div className="flex flex-col items-center justify-center h-full text-center p-6">
                <Server className="h-12 w-12 text-muted-foreground mb-4" />
                <h3 className="font-semibold mb-2">Worker Mode</h3>
                <p className="text-sm text-muted-foreground">
                  Your HTTP endpoint will receive function invocations and handle all business logic.
                  The endpoint should accept POST requests with JSON payload.
                </p>
              </div>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

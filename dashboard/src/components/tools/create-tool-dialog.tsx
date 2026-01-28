"use client";

import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
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
  Plus,
  Trash2,
  Sparkles,
  Shield,
  Settings,
  Wrench,
} from "lucide-react";
import { api } from "@/lib/api";

interface CreateToolDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
  onError: (message: string) => void;
}

interface ToolParameter {
  id: string;
  name: string;
  type: "string" | "number" | "boolean" | "array";
  description: string;
  required: boolean;
}

const PARAMETER_TYPES = [
  { value: "string", label: "Text" },
  { value: "number", label: "Number" },
  { value: "boolean", label: "Yes/No" },
  { value: "array", label: "List" },
];

const TOOL_EXAMPLES = [
  {
    name: "send_email",
    description: "Send an email to a recipient",
    parameters: [
      { name: "to", type: "string", description: "Email address", required: true },
      { name: "subject", type: "string", description: "Subject line", required: true },
      { name: "body", type: "string", description: "Email content", required: true },
    ],
  },
  {
    name: "search_database",
    description: "Search records in the database",
    parameters: [
      { name: "query", type: "string", description: "Search query", required: true },
      { name: "limit", type: "number", description: "Max results", required: false },
    ],
  },
  {
    name: "create_ticket",
    description: "Create a support ticket",
    parameters: [
      { name: "title", type: "string", description: "Ticket title", required: true },
      { name: "priority", type: "string", description: "Priority level", required: true },
    ],
  },
];

export function CreateToolDialog({
  open,
  onOpenChange,
  onSuccess,
  onError,
}: CreateToolDialogProps) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [parameters, setParameters] = useState<ToolParameter[]>([]);
  const [code, setCode] = useState("");
  const [requiresApproval, setRequiresApproval] = useState(false);
  const [approvalTimeout, setApprovalTimeout] = useState("1h");
  const [showCode, setShowCode] = useState(false);
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const resetForm = () => {
    setName("");
    setDescription("");
    setParameters([]);
    setCode("");
    setRequiresApproval(false);
    setApprovalTimeout("1h");
    setShowCode(false);
    setErrors({});
  };

  const addParameter = () => {
    setParameters([
      ...parameters,
      { id: crypto.randomUUID(), name: "", type: "string", description: "", required: false },
    ]);
  };

  const updateParameter = (id: string, updates: Partial<ToolParameter>) => {
    setParameters(parameters.map((p) => (p.id === id ? { ...p, ...updates } : p)));
  };

  const removeParameter = (id: string) => {
    setParameters(parameters.filter((p) => p.id !== id));
  };

  const applyExample = (example: typeof TOOL_EXAMPLES[0]) => {
    setName(example.name);
    setDescription(example.description);
    setParameters(
      example.parameters.map((p) => ({
        id: crypto.randomUUID(),
        name: p.name,
        type: p.type as ToolParameter["type"],
        description: p.description,
        required: p.required,
      }))
    );
  };

  const buildJsonSchema = () => {
    const properties: Record<string, unknown> = {};
    const required: string[] = [];
    parameters.forEach((param) => {
      if (param.name) {
        properties[param.name] = {
          type: param.type === "array" ? "array" : param.type,
          description: param.description || undefined,
          ...(param.type === "array" && { items: { type: "string" } }),
        };
        if (param.required) required.push(param.name);
      }
    });
    return { type: "object", properties, required: required.length > 0 ? required : undefined };
  };

  const validate = (): boolean => {
    const newErrors: Record<string, string> = {};
    if (!name.trim()) newErrors.name = "Name is required";
    else if (!/^[a-z][a-z0-9_]*$/.test(name)) newErrors.name = "Lowercase with underscores only";
    if (!description.trim()) newErrors.description = "Description is required";
    parameters.forEach((param, i) => {
      if (!param.name.trim()) newErrors[`param_${i}`] = "Name required";
      else if (!/^[a-z][a-z0-9_]*$/.test(param.name)) newErrors[`param_${i}`] = "Lowercase only";
    });
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;
    setLoading(true);
    const result = await api.createTool({
      name: name.trim(),
      description: description.trim(),
      parameters: buildJsonSchema(),
      code: code.trim() || undefined,
      requires_approval: requiresApproval,
      approval_timeout: requiresApproval ? approvalTimeout : undefined,
    });
    setLoading(false);
    if (result) {
      resetForm();
      onSuccess();
      onOpenChange(false);
    } else {
      onError("Failed to create tool");
    }
  };

  return (
    <Dialog open={open} onOpenChange={(isOpen) => { if (!isOpen) resetForm(); onOpenChange(isOpen); }}>
      <DialogContent className="max-w-[90vw] w-[1400px] p-0 gap-0 overflow-hidden">
        <div className="grid grid-cols-[320px_1fr_1fr]">
          {/* Left Sidebar - Examples */}
          <div className="bg-muted/40 p-8 border-r">
            <div className="flex items-center gap-2 mb-6">
              <Sparkles className="h-5 w-5 text-blue-500" />
              <span className="font-semibold">Templates</span>
            </div>
            <div className="space-y-3">
              {TOOL_EXAMPLES.map((example) => (
                <button
                  key={example.name}
                  type="button"
                  onClick={() => applyExample(example)}
                  className="w-full text-left p-4 rounded-xl border-2 border-transparent bg-background hover:border-blue-400 hover:shadow-md transition-all"
                >
                  <div className="font-mono text-sm font-semibold text-foreground">{example.name}</div>
                  <div className="text-xs text-muted-foreground mt-1 line-clamp-2">{example.description}</div>
                  <div className="flex gap-1 mt-3 flex-wrap">
                    {example.parameters.slice(0, 3).map((p) => (
                      <Badge key={p.name} variant="secondary" className="text-[10px] px-2">
                        {p.name}
                      </Badge>
                    ))}
                  </div>
                </button>
              ))}
            </div>

            {/* Settings */}
            <div className="mt-8 pt-6 border-t">
              <div className="flex items-center gap-2 mb-4">
                <Settings className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm font-medium">Settings</span>
              </div>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Shield className="h-4 w-4 text-orange-500" />
                    <span className="text-sm">Requires Approval</span>
                  </div>
                  <Switch checked={requiresApproval} onCheckedChange={setRequiresApproval} />
                </div>
                {requiresApproval && (
                  <Input
                    value={approvalTimeout}
                    onChange={(e) => setApprovalTimeout(e.target.value)}
                    placeholder="Timeout (1h, 30m)"
                    className="h-9"
                  />
                )}
              </div>
            </div>
          </div>

          {/* Middle - Tool Info */}
          <div className="p-8 border-r">
            <DialogHeader className="mb-6">
              <DialogTitle className="flex items-center gap-2 text-xl">
                <Wrench className="h-5 w-5" />
                Create Tool
              </DialogTitle>
            </DialogHeader>

            <form onSubmit={handleSubmit} className="space-y-5">
              <div>
                <label className="text-sm font-medium mb-2 block">Tool Name</label>
                <Input
                  value={name}
                  onChange={(e) => setName(e.target.value.toLowerCase().replace(/\s/g, "_"))}
                  placeholder="my_tool_name"
                  className="font-mono h-11"
                  disabled={loading}
                />
                {errors.name && <p className="text-xs text-red-500 mt-1.5">{errors.name}</p>}
                <p className="text-xs text-muted-foreground mt-1.5">Lowercase letters, numbers, underscores</p>
              </div>

              <div>
                <label className="text-sm font-medium mb-2 block">Description</label>
                <Textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Describe what this tool does. The AI reads this to decide when to use it."
                  rows={4}
                  className="resize-none"
                  disabled={loading}
                />
                {errors.description && <p className="text-xs text-red-500 mt-1.5">{errors.description}</p>}
              </div>

              <div>
                <button
                  type="button"
                  onClick={() => setShowCode(!showCode)}
                  className="text-sm text-muted-foreground hover:text-foreground flex items-center gap-1"
                >
                  {showCode ? "Hide" : "Add"} Python Code (Optional)
                </button>
                {showCode && (
                  <Textarea
                    value={code}
                    onChange={(e) => setCode(e.target.value)}
                    placeholder={"def execute(arguments):\n    # Your code here\n    return result"}
                    rows={6}
                    className="mt-3 font-mono text-sm resize-none"
                    disabled={loading}
                  />
                )}
              </div>

              <div className="flex justify-end gap-3 pt-4">
                <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={loading}>
                  Cancel
                </Button>
                <Button type="submit" disabled={loading} className="min-w-[120px]">
                  {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : "Create Tool"}
                </Button>
              </div>
            </form>
          </div>

          {/* Right - Parameters */}
          <div className="p-8 bg-muted/20">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h3 className="font-semibold">Parameters</h3>
                <p className="text-xs text-muted-foreground mt-1">Define inputs for this tool</p>
              </div>
              <Button type="button" variant="outline" size="sm" onClick={addParameter}>
                <Plus className="h-4 w-4 mr-1" />
                Add
              </Button>
            </div>

            <ScrollArea className="h-[400px] pr-4">
              {parameters.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-[300px] text-center border-2 border-dashed rounded-xl p-6">
                  <div className="w-12 h-12 rounded-full bg-muted flex items-center justify-center mb-4">
                    <Plus className="h-6 w-6 text-muted-foreground" />
                  </div>
                  <p className="font-medium">No parameters</p>
                  <p className="text-sm text-muted-foreground mt-1">Click Add to define what inputs this tool needs</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {parameters.map((param, index) => (
                    <div key={param.id} className="p-4 rounded-xl border bg-background space-y-3">
                      <div className="flex items-center gap-3">
                        <Input
                          value={param.name}
                          onChange={(e) => updateParameter(param.id, { name: e.target.value.toLowerCase().replace(/\s/g, "_") })}
                          placeholder="parameter_name"
                          className="font-mono flex-1 h-10"
                          disabled={loading}
                        />
                        <Select
                          value={param.type}
                          onValueChange={(v) => updateParameter(param.id, { type: v as ToolParameter["type"] })}
                        >
                          <SelectTrigger className="w-[100px] h-10">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {PARAMETER_TYPES.map((t) => (
                              <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon"
                          onClick={() => removeParameter(param.id)}
                          className="text-muted-foreground hover:text-red-500 shrink-0"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                      {errors[`param_${index}`] && (
                        <p className="text-xs text-red-500">{errors[`param_${index}`]}</p>
                      )}
                      <Input
                        value={param.description}
                        onChange={(e) => updateParameter(param.id, { description: e.target.value })}
                        placeholder="Description (helps AI understand this parameter)"
                        className="h-10"
                        disabled={loading}
                      />
                      <label className="flex items-center gap-2 text-sm">
                        <Switch
                          checked={param.required}
                          onCheckedChange={(c) => updateParameter(param.id, { required: c })}
                        />
                        <span className="text-muted-foreground">Required</span>
                      </label>
                    </div>
                  ))}
                </div>
              )}
            </ScrollArea>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

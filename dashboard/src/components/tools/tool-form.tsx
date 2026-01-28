"use client";

import { useState, useEffect } from "react";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { Button } from "@/components/ui/button";
import { FormField } from "@/components/forms/form-field";
import { JSONEditor, isValidJSON, parseJSON } from "@/components/forms/json-editor";
import { Loader2 } from "lucide-react";
import { Tool } from "@/lib/api";

export interface ToolFormData {
  name: string;
  description: string;
  parameters: Record<string, unknown>;
  code: string;
  requires_approval: boolean;
  approval_timeout: string;
}

interface ToolFormProps {
  tool?: Tool | null;
  onSubmit: (data: ToolFormData) => Promise<void>;
  onCancel: () => void;
  loading?: boolean;
}

const defaultParameters = {
  type: "object",
  properties: {},
  required: [],
};

export function ToolForm({ tool, onSubmit, onCancel, loading = false }: ToolFormProps) {
  const isEdit = !!tool;

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [parametersJson, setParametersJson] = useState(JSON.stringify(defaultParameters, null, 2));
  const [code, setCode] = useState("");
  const [requiresApproval, setRequiresApproval] = useState(false);
  const [approvalTimeout, setApprovalTimeout] = useState("1h");

  const [errors, setErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    if (tool) {
      setName(tool.name);
      setDescription(tool.description);
      setParametersJson(JSON.stringify(tool.parameters || defaultParameters, null, 2));
      setCode(tool.code || "");
      setRequiresApproval(tool.requires_approval);
      setApprovalTimeout(tool.approval_timeout || "1h");
    }
  }, [tool]);

  const validate = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (!name.trim()) {
      newErrors.name = "Name is required";
    } else if (!/^[a-z][a-z0-9_]*$/.test(name)) {
      newErrors.name = "Name must be lowercase, start with a letter, and contain only letters, numbers, and underscores";
    }

    if (!description.trim()) {
      newErrors.description = "Description is required";
    }

    if (!isValidJSON(parametersJson)) {
      newErrors.parameters = "Invalid JSON";
    }

    if (requiresApproval && !approvalTimeout.trim()) {
      newErrors.approval_timeout = "Timeout is required when approval is enabled";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validate()) return;

    const parameters = parseJSON(parametersJson) || defaultParameters;

    await onSubmit({
      name: name.trim(),
      description: description.trim(),
      parameters,
      code: code.trim(),
      requires_approval: requiresApproval,
      approval_timeout: approvalTimeout.trim(),
    });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <FormField
        label="Name"
        required
        description="Unique identifier for the tool (lowercase, underscores allowed)"
        error={errors.name}
        htmlFor="name"
      >
        <Input
          id="name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="my_custom_tool"
          disabled={loading || isEdit}
          className="font-mono"
        />
      </FormField>

      <FormField
        label="Description"
        required
        description="Describe what this tool does (shown to the LLM)"
        error={errors.description}
        htmlFor="description"
      >
        <Textarea
          id="description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="This tool performs..."
          rows={3}
          disabled={loading}
        />
      </FormField>

      <FormField
        label="Parameters"
        description="JSON Schema defining the tool's input parameters"
        error={errors.parameters}
      >
        <JSONEditor
          value={parametersJson}
          onChange={setParametersJson}
          placeholder='{\n  "type": "object",\n  "properties": {\n    "query": { "type": "string", "description": "Search query" }\n  },\n  "required": ["query"]\n}'
          rows={10}
          disabled={loading}
        />
      </FormField>

      <FormField
        label="Python Code"
        description="Python code to execute when the tool is called (optional)"
        htmlFor="code"
      >
        <Textarea
          id="code"
          value={code}
          onChange={(e) => setCode(e.target.value)}
          placeholder="def execute(arguments):\n    # Your code here\n    return result"
          rows={8}
          disabled={loading}
          className="font-mono text-sm"
        />
      </FormField>

      <div className="space-y-4 rounded-lg border p-4">
        <div className="flex items-center justify-between">
          <div className="space-y-0.5">
            <label className="text-sm font-medium">Requires Approval</label>
            <p className="text-sm text-muted-foreground">
              Pause execution and wait for human approval before running this tool
            </p>
          </div>
          <Switch
            checked={requiresApproval}
            onCheckedChange={setRequiresApproval}
            disabled={loading}
          />
        </div>

        {requiresApproval && (
          <FormField
            label="Approval Timeout"
            description="How long to wait for approval (e.g., 1h, 30m, 1d)"
            error={errors.approval_timeout}
            htmlFor="approval_timeout"
          >
            <Input
              id="approval_timeout"
              value={approvalTimeout}
              onChange={(e) => setApprovalTimeout(e.target.value)}
              placeholder="1h"
              disabled={loading}
              className="w-32"
            />
          </FormField>
        )}
      </div>

      <div className="flex justify-end gap-3 pt-4 border-t">
        <Button type="button" variant="outline" onClick={onCancel} disabled={loading}>
          Cancel
        </Button>
        <Button type="submit" disabled={loading}>
          {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          {isEdit ? "Save Changes" : "Create Tool"}
        </Button>
      </div>
    </form>
  );
}

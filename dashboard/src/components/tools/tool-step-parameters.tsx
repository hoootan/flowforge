"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
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
import { Plus, Trash2, GripVertical, ChevronRight, Code } from "lucide-react";
import { useState } from "react";

export interface ToolParameter {
  id: string;
  name: string;
  type: "string" | "number" | "boolean" | "array";
  description: string;
  required: boolean;
}

const PARAMETER_TYPES = [
  { value: "string", label: "Text" },
  { value: "number", label: "Number" },
  { value: "boolean", label: "Boolean" },
  { value: "array", label: "Array" },
];

interface ToolStepParametersProps {
  parameters: ToolParameter[];
  onParametersChange: (parameters: ToolParameter[]) => void;
  errors: Record<string, string>;
  disabled?: boolean;
}

export function ToolStepParameters({
  parameters,
  onParametersChange,
  errors,
  disabled = false,
}: ToolStepParametersProps) {
  const [showJson, setShowJson] = useState(false);

  const addParameter = () => {
    onParametersChange([
      ...parameters,
      { id: crypto.randomUUID(), name: "", type: "string", description: "", required: false },
    ]);
  };

  const updateParameter = (id: string, updates: Partial<ToolParameter>) => {
    onParametersChange(
      parameters.map((p) => (p.id === id ? { ...p, ...updates } : p))
    );
  };

  const removeParameter = (id: string) => {
    onParametersChange(parameters.filter((p) => p.id !== id));
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

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-lg font-semibold mb-1">Parameters</h2>
          <p className="text-sm text-muted-foreground">
            Define what inputs this tool accepts. These become the function arguments.
          </p>
        </div>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={addParameter}
          disabled={disabled}
          className="gap-2 shrink-0"
        >
          <Plus className="h-4 w-4" />
          Add Parameter
        </Button>
      </div>

      {parameters.length === 0 ? (
        <Card className="bg-muted/30 border-dashed">
          <CardContent className="p-8 text-center">
            <div className="w-12 h-12 rounded-full bg-muted flex items-center justify-center mx-auto mb-4">
              <Plus className="h-6 w-6 text-muted-foreground" />
            </div>
            <p className="font-medium">No parameters defined</p>
            <p className="text-sm text-muted-foreground mt-1 mb-4">
              Add parameters to define what inputs this tool needs
            </p>
            <Button
              type="button"
              variant="outline"
              onClick={addParameter}
              disabled={disabled}
              className="gap-2"
            >
              <Plus className="h-4 w-4" />
              Add First Parameter
            </Button>
          </CardContent>
        </Card>
      ) : (
        <ScrollArea className="max-h-[400px]">
          <div className="space-y-3 pr-1">
            {parameters.map((param, index) => (
              <Card key={param.id}>
                <CardContent className="p-4">
                  <div className="flex items-start gap-3">
                    <div className="pt-2 text-muted-foreground cursor-grab">
                      <GripVertical className="h-4 w-4" />
                    </div>

                    <div className="flex-1 space-y-3">
                      <div className="flex items-center gap-2">
                        <Input
                          value={param.name}
                          onChange={(e) =>
                            updateParameter(param.id, {
                              name: e.target.value.toLowerCase().replace(/\s/g, "_"),
                            })
                          }
                          placeholder="param_name"
                          className="font-mono text-sm h-9 flex-1"
                          disabled={disabled}
                        />
                        <Select
                          value={param.type}
                          onValueChange={(v) =>
                            updateParameter(param.id, { type: v as ToolParameter["type"] })
                          }
                        >
                          <SelectTrigger className="w-[100px] h-9 text-sm">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {PARAMETER_TYPES.map((t) => (
                              <SelectItem key={t.value} value={t.value}>
                                {t.label}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon"
                          onClick={() => removeParameter(param.id)}
                          disabled={disabled}
                          className="h-9 w-9 text-muted-foreground hover:text-destructive shrink-0"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>

                      {errors[`param_${index}`] && (
                        <p className="text-xs text-destructive">{errors[`param_${index}`]}</p>
                      )}

                      <Input
                        value={param.description}
                        onChange={(e) =>
                          updateParameter(param.id, { description: e.target.value })
                        }
                        placeholder="Describe what this parameter does..."
                        className="text-sm h-9"
                        disabled={disabled}
                      />

                      <div className="flex items-center justify-between">
                        <label className="flex items-center gap-2 text-sm cursor-pointer">
                          <Switch
                            checked={param.required}
                            onCheckedChange={(c) =>
                              updateParameter(param.id, { required: c })
                            }
                            disabled={disabled}
                          />
                          <span className="text-muted-foreground">Required</span>
                        </label>
                        {param.required && (
                          <Badge variant="secondary" className="text-xs">
                            Required
                          </Badge>
                        )}
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </ScrollArea>
      )}

      {/* View as JSON */}
      {parameters.length > 0 && (
        <Collapsible open={showJson} onOpenChange={setShowJson}>
          <CollapsibleTrigger asChild>
            <button
              type="button"
              className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              <ChevronRight
                className={`h-4 w-4 transition-transform ${showJson ? "rotate-90" : ""}`}
              />
              <Code className="h-4 w-4" />
              View as JSON Schema
            </button>
          </CollapsibleTrigger>
          <CollapsibleContent className="mt-3">
            <pre className="p-4 bg-muted rounded-lg text-xs font-mono overflow-auto max-h-48">
              {JSON.stringify(buildJsonSchema(), null, 2)}
            </pre>
          </CollapsibleContent>
        </Collapsible>
      )}
    </div>
  );
}

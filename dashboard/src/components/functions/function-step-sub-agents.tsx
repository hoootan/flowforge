"use client";

import { useState, useMemo } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { ScrollArea } from "@/components/ui/scroll-area";
import { FormField } from "@/components/forms/form-field";
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
import { Bot, Plus, Trash2, ChevronRight, Settings, X } from "lucide-react";
import { cn } from "@/lib/utils";
import type { Tool } from "@/lib/api";
import { MODEL_OPTIONS } from "./constants";

export interface SubAgentEntry {
  name: string;
  description: string;
  model: string;
  systemPrompt: string;
  tools: string[];
  maxIterations: number;
  maxToolCalls: number;
}

interface FunctionStepSubAgentsProps {
  subAgents: SubAgentEntry[];
  onSubAgentsChange: (subAgents: SubAgentEntry[]) => void;
  availableTools: Tool[];
  disabled?: boolean;
}

function createDefaultSubAgent(): SubAgentEntry {
  return {
    name: "",
    description: "",
    model: "claude-sonnet-4-6",
    systemPrompt: "",
    tools: [],
    maxIterations: 20,
    maxToolCalls: 50,
  };
}

function SubAgentCard({
  agent,
  index,
  onChange,
  onDelete,
  availableTools,
  disabled,
}: {
  agent: SubAgentEntry;
  index: number;
  onChange: (updated: SubAgentEntry) => void;
  onDelete: () => void;
  availableTools: Tool[];
  disabled?: boolean;
}) {
  const [expanded, setExpanded] = useState(true);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [toolSearch, setToolSearch] = useState("");

  const filteredTools = useMemo(() => {
    const q = toolSearch.toLowerCase();
    return availableTools.filter(
      (t) => t.name.toLowerCase().includes(q) || t.description.toLowerCase().includes(q)
    );
  }, [availableTools, toolSearch]);

  const selectedToolObjects = useMemo(
    () => availableTools.filter((t) => agent.tools.includes(t.name)),
    [availableTools, agent.tools]
  );

  const handleToggleTool = (toolName: string) => {
    const tools = agent.tools.includes(toolName)
      ? agent.tools.filter((t) => t !== toolName)
      : [...agent.tools, toolName];
    onChange({ ...agent, tools });
  };

  const modelLabel = MODEL_OPTIONS.find((m) => m.value === agent.model)?.label ?? agent.model;

  return (
    <Card>
      <Collapsible open={expanded} onOpenChange={setExpanded}>
        <div className="flex items-center justify-between p-4 pb-0">
          <CollapsibleTrigger asChild>
            <button type="button" className="flex items-center gap-2 hover:text-foreground transition-colors">
              <ChevronRight className={cn("h-4 w-4 transition-transform", expanded && "rotate-90")} />
              <code className="font-mono text-sm font-medium">
                {agent.name || `sub-agent-${index + 1}`}
              </code>
              <Badge variant="secondary" className="text-xs">{modelLabel}</Badge>
            </button>
          </CollapsibleTrigger>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="h-8 w-8 text-muted-foreground hover:text-destructive"
            onClick={onDelete}
            disabled={disabled}
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>

        <CollapsibleContent>
          <CardContent className="p-4 pt-4 space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <FormField label="Name" required htmlFor={`sa-name-${index}`}>
                <Input
                  id={`sa-name-${index}`}
                  value={agent.name}
                  onChange={(e) => onChange({ ...agent, name: e.target.value.toLowerCase().replace(/[^a-z0-9_-]/g, "") })}
                  placeholder="research-agent"
                  className="font-mono h-9"
                  disabled={disabled}
                />
              </FormField>
              <FormField label="Model" required htmlFor={`sa-model-${index}`}>
                <Select
                  value={agent.model}
                  onValueChange={(v) => onChange({ ...agent, model: v })}
                  disabled={disabled}
                >
                  <SelectTrigger id={`sa-model-${index}`} className="h-9">
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
            </div>

            <FormField label="Description" required htmlFor={`sa-desc-${index}`}>
              <Input
                id={`sa-desc-${index}`}
                value={agent.description}
                onChange={(e) => onChange({ ...agent, description: e.target.value })}
                placeholder="Performs deep research on a given topic and returns findings"
                className="h-9"
                disabled={disabled}
              />
            </FormField>

            <FormField label="System Prompt" required htmlFor={`sa-prompt-${index}`}>
              <Textarea
                id={`sa-prompt-${index}`}
                value={agent.systemPrompt}
                onChange={(e) => onChange({ ...agent, systemPrompt: e.target.value })}
                placeholder="You are a specialist agent that..."
                rows={4}
                className="resize-none text-sm leading-relaxed"
                disabled={disabled}
              />
            </FormField>

            {/* Tools selection */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-sm font-medium">Tools</label>
                <Badge variant="secondary" className="text-xs">{agent.tools.length} selected</Badge>
              </div>

              {selectedToolObjects.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {selectedToolObjects.map((tool) => (
                    <Badge key={tool.name} variant="outline" className="pl-2 pr-1 py-1 gap-1 text-xs">
                      <code className="font-mono">{tool.name}</code>
                      <button
                        type="button"
                        onClick={() => handleToggleTool(tool.name)}
                        disabled={disabled}
                        className="ml-0.5 hover:bg-muted rounded p-0.5"
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </Badge>
                  ))}
                </div>
              )}

              {availableTools.length > 0 && (
                <>
                  <Input
                    value={toolSearch}
                    onChange={(e) => setToolSearch(e.target.value)}
                    placeholder="Search tools..."
                    className="h-8 text-sm"
                    disabled={disabled}
                  />
                  <ScrollArea className="h-[160px]">
                    <div className="space-y-1 pr-3">
                      {filteredTools.map((tool) => {
                        const isSelected = agent.tools.includes(tool.name);
                        return (
                          <button
                            key={tool.name}
                            type="button"
                            onClick={() => handleToggleTool(tool.name)}
                            disabled={disabled}
                            className={cn(
                              "w-full text-left p-2 rounded-md border text-sm transition-all flex items-start gap-2",
                              isSelected
                                ? "border-primary bg-primary/5"
                                : "border-border bg-card hover:border-primary/50"
                            )}
                          >
                            <Checkbox checked={isSelected} className="mt-0.5" disabled={disabled} />
                            <div className="flex-1 min-w-0">
                              <code className="font-mono text-xs font-medium">{tool.name}</code>
                              <p className="text-xs text-muted-foreground line-clamp-1">{tool.description}</p>
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  </ScrollArea>
                </>
              )}
            </div>

            {/* Advanced settings */}
            <Collapsible open={showAdvanced} onOpenChange={setShowAdvanced}>
              <CollapsibleTrigger asChild>
                <button
                  type="button"
                  className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
                >
                  <ChevronRight className={cn("h-4 w-4 transition-transform", showAdvanced && "rotate-90")} />
                  <Settings className="h-3.5 w-3.5" />
                  Advanced
                </button>
              </CollapsibleTrigger>
              <CollapsibleContent className="mt-3">
                <Card className="bg-muted/30">
                  <CardContent className="p-3 space-y-3">
                    <div className="grid grid-cols-2 gap-3">
                      <FormField label="Max Iterations" htmlFor={`sa-iter-${index}`}>
                        <Input
                          id={`sa-iter-${index}`}
                          type="number"
                          value={agent.maxIterations}
                          onChange={(e) => onChange({ ...agent, maxIterations: parseInt(e.target.value) || 20 })}
                          className="h-8"
                          disabled={disabled}
                        />
                      </FormField>
                      <FormField label="Max Tool Calls" htmlFor={`sa-tc-${index}`}>
                        <Input
                          id={`sa-tc-${index}`}
                          type="number"
                          value={agent.maxToolCalls}
                          onChange={(e) => onChange({ ...agent, maxToolCalls: parseInt(e.target.value) || 50 })}
                          className="h-8"
                          disabled={disabled}
                        />
                      </FormField>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      Limits for this sub-agent. It will stop if either limit is reached.
                    </p>
                  </CardContent>
                </Card>
              </CollapsibleContent>
            </Collapsible>
          </CardContent>
        </CollapsibleContent>
      </Collapsible>
    </Card>
  );
}

export function FunctionStepSubAgents({
  subAgents,
  onSubAgentsChange,
  availableTools,
  disabled = false,
}: FunctionStepSubAgentsProps) {
  const handleAdd = () => {
    onSubAgentsChange([...subAgents, createDefaultSubAgent()]);
  };

  const handleChange = (index: number, updated: SubAgentEntry) => {
    const next = [...subAgents];
    next[index] = updated;
    onSubAgentsChange(next);
  };

  const handleDelete = (index: number) => {
    onSubAgentsChange(subAgents.filter((_, i) => i !== index));
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
          <Bot className="h-5 w-5 text-primary" />
        </div>
        <div className="flex-1">
          <h2 className="text-lg font-semibold">Sub-Agents</h2>
          <p className="text-sm text-muted-foreground">
            Define specialist agents that can be delegated tasks at runtime.
          </p>
        </div>
        <Button type="button" variant="outline" size="sm" onClick={handleAdd} disabled={disabled}>
          <Plus className="h-4 w-4 mr-1.5" />
          Add Sub-Agent
        </Button>
      </div>

      {subAgents.length === 0 ? (
        <Card className="bg-muted/30 border-dashed">
          <CardContent className="p-8 text-center">
            <div className="w-12 h-12 rounded-full bg-muted flex items-center justify-center mx-auto mb-4">
              <Bot className="h-6 w-6 text-muted-foreground" />
            </div>
            <p className="font-medium">No sub-agents configured</p>
            <p className="text-sm text-muted-foreground mt-1">
              Sub-agents are optional. Add one to enable the parent agent to delegate specialized tasks.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {subAgents.map((agent, i) => (
            <SubAgentCard
              key={i}
              agent={agent}
              index={i}
              onChange={(updated) => handleChange(i, updated)}
              onDelete={() => handleDelete(i)}
              availableTools={availableTools}
              disabled={disabled}
            />
          ))}
        </div>
      )}
    </div>
  );
}

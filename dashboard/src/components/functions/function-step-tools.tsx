"use client";

import { useState, useMemo } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Checkbox } from "@/components/ui/checkbox";
import { Search, Wrench, X, Plus } from "lucide-react";
import { cn } from "@/lib/utils";
import type { Tool } from "@/lib/api";

interface FunctionStepToolsProps {
  availableTools: Tool[];
  selectedTools: string[];
  onSelectedToolsChange: (tools: string[]) => void;
  loading?: boolean;
  disabled?: boolean;
}

export function FunctionStepTools({
  availableTools,
  selectedTools,
  onSelectedToolsChange,
  loading = false,
  disabled = false,
}: FunctionStepToolsProps) {
  const [searchQuery, setSearchQuery] = useState("");

  const filteredTools = useMemo(() => {
    const query = searchQuery.toLowerCase();
    return availableTools.filter(
      (tool) =>
        tool.name.toLowerCase().includes(query) ||
        tool.description.toLowerCase().includes(query)
    );
  }, [availableTools, searchQuery]);

  const selectedToolObjects = useMemo(() => {
    return availableTools.filter((t) => selectedTools.includes(t.name));
  }, [availableTools, selectedTools]);

  const handleToggleTool = (toolName: string) => {
    if (selectedTools.includes(toolName)) {
      onSelectedToolsChange(selectedTools.filter((t) => t !== toolName));
    } else {
      onSelectedToolsChange([...selectedTools, toolName]);
    }
  };

  const handleRemoveTool = (toolName: string) => {
    onSelectedToolsChange(selectedTools.filter((t) => t !== toolName));
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold mb-1">Tools Selection</h2>
        <p className="text-sm text-muted-foreground">
          Select the tools this AI agent can use to complete its tasks.
        </p>
      </div>

      {/* Selected tools */}
      {selectedTools.length > 0 && (
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <label className="text-sm font-medium">Selected Tools</label>
            <Badge variant="secondary">{selectedTools.length} selected</Badge>
          </div>
          <div className="flex flex-wrap gap-2">
            {selectedToolObjects.map((tool) => (
              <Badge
                key={tool.name}
                variant="outline"
                className="pl-2 pr-1 py-1.5 gap-1.5 text-sm"
              >
                <code className="font-mono">{tool.name}</code>
                <button
                  type="button"
                  onClick={() => handleRemoveTool(tool.name)}
                  disabled={disabled}
                  className="ml-1 hover:bg-muted rounded p-0.5"
                >
                  <X className="h-3 w-3" />
                </button>
              </Badge>
            ))}
          </div>
        </div>
      )}

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search tools..."
          className="pl-9 h-10"
          disabled={disabled}
        />
      </div>

      {/* Tools list */}
      {loading ? (
        <Card className="bg-muted/30">
          <CardContent className="p-8 text-center">
            <div className="animate-pulse space-y-3">
              <div className="h-4 bg-muted rounded w-1/3 mx-auto" />
              <div className="h-3 bg-muted rounded w-1/2 mx-auto" />
            </div>
          </CardContent>
        </Card>
      ) : availableTools.length === 0 ? (
        <Card className="bg-muted/30 border-dashed">
          <CardContent className="p-8 text-center">
            <div className="w-12 h-12 rounded-full bg-muted flex items-center justify-center mx-auto mb-4">
              <Wrench className="h-6 w-6 text-muted-foreground" />
            </div>
            <p className="font-medium">No tools available</p>
            <p className="text-sm text-muted-foreground mt-1">
              Create some tools first, then come back to add them to this function.
            </p>
          </CardContent>
        </Card>
      ) : filteredTools.length === 0 ? (
        <Card className="bg-muted/30">
          <CardContent className="p-6 text-center">
            <p className="text-sm text-muted-foreground">
              No tools match &quot;{searchQuery}&quot;
            </p>
          </CardContent>
        </Card>
      ) : (
        <ScrollArea className="h-[320px]">
          <div className="space-y-2 pr-3">
            {filteredTools.map((tool) => {
              const isSelected = selectedTools.includes(tool.name);

              return (
                <button
                  key={tool.name}
                  type="button"
                  onClick={() => handleToggleTool(tool.name)}
                  disabled={disabled}
                  className={cn(
                    "w-full text-left p-3 rounded-lg border transition-all flex items-start gap-3",
                    isSelected
                      ? "border-primary bg-primary/5"
                      : "border-border bg-card hover:border-primary/50 hover:bg-muted/30"
                  )}
                >
                  <Checkbox
                    checked={isSelected}
                    className="mt-0.5"
                    disabled={disabled}
                  />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <code className="font-mono text-sm font-medium">{tool.name}</code>
                      {tool.requires_approval && (
                        <Badge variant="secondary" className="text-[10px]">
                          Approval
                        </Badge>
                      )}
                    </div>
                    <p className="text-sm text-muted-foreground mt-0.5 line-clamp-2">
                      {tool.description}
                    </p>
                  </div>
                </button>
              );
            })}
          </div>
        </ScrollArea>
      )}

      {/* No tools selected info */}
      {selectedTools.length === 0 && availableTools.length > 0 && (
        <Card className="bg-amber-50 dark:bg-amber-950/30 border-amber-200 dark:border-amber-900">
          <CardContent className="p-4 text-sm text-amber-800 dark:text-amber-200">
            <strong>Note:</strong> Without tools, the AI agent can only respond with text.
            Select tools to enable the agent to take actions.
          </CardContent>
        </Card>
      )}
    </div>
  );
}

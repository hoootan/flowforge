"use client";

import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Code, Info } from "lucide-react";
import type { ToolParameter } from "./tool-step-parameters";

interface ToolStepCodeProps {
  code: string;
  onCodeChange: (value: string) => void;
  enabled: boolean;
  onEnabledChange: (enabled: boolean) => void;
  parameters: ToolParameter[];
  disabled?: boolean;
}

export function ToolStepCode({
  code,
  onCodeChange,
  enabled,
  onEnabledChange,
  parameters,
  disabled = false,
}: ToolStepCodeProps) {
  // Generate function signature from parameters
  const generateSignature = () => {
    if (parameters.length === 0) {
      return "def execute(arguments):\n    # arguments is an empty dict\n    pass";
    }
    const params = parameters.filter((p) => p.name).map((p) => p.name);
    return `def execute(arguments):
    # Available arguments:
${params.map((p) => `    # - arguments["${p}"]`).join("\n")}

    # Your code here
    result = None
    return result`;
  };

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-lg font-semibold mb-1">Python Code</h2>
          <p className="text-sm text-muted-foreground">
            Optionally add Python code that executes when the tool is called.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Badge variant="secondary" className="text-xs">
            Optional
          </Badge>
          <label className="flex items-center gap-2 cursor-pointer">
            <span className="text-sm text-muted-foreground">Enable</span>
            <Switch
              checked={enabled}
              onCheckedChange={onEnabledChange}
              disabled={disabled}
            />
          </label>
        </div>
      </div>

      {enabled ? (
        <div className="space-y-4">
          {/* Info card */}
          <Card className="bg-blue-50 dark:bg-blue-950/30 border-blue-200 dark:border-blue-900">
            <CardContent className="p-4">
              <div className="flex gap-3">
                <Info className="h-5 w-5 text-blue-600 dark:text-blue-400 shrink-0 mt-0.5" />
                <div className="text-sm text-blue-800 dark:text-blue-200">
                  <p className="font-medium mb-1">Code receives arguments as a dictionary</p>
                  <p className="text-blue-700 dark:text-blue-300">
                    Access parameters via <code className="font-mono bg-blue-100 dark:bg-blue-900 px-1 rounded">arguments[&quot;param_name&quot;]</code>.
                    Return value becomes the tool output.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Code editor */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Code className="h-4 w-4" />
                <span>Python</span>
              </div>
              {parameters.length > 0 && (
                <button
                  type="button"
                  onClick={() => !code && onCodeChange(generateSignature())}
                  className="text-xs text-primary hover:underline"
                  disabled={disabled || !!code}
                >
                  Generate template
                </button>
              )}
            </div>
            <Textarea
              value={code}
              onChange={(e) => onCodeChange(e.target.value)}
              placeholder={generateSignature()}
              rows={12}
              className="font-mono text-sm resize-none"
              disabled={disabled}
            />
          </div>
        </div>
      ) : (
        <Card className="bg-muted/30 border-dashed">
          <CardContent className="p-8 text-center">
            <div className="w-12 h-12 rounded-full bg-muted flex items-center justify-center mx-auto mb-4">
              <Code className="h-6 w-6 text-muted-foreground" />
            </div>
            <p className="font-medium">No code execution</p>
            <p className="text-sm text-muted-foreground mt-1 max-w-sm mx-auto">
              This tool will only define parameters. Enable code execution to add custom logic
              that runs when the AI calls this tool.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

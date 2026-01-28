"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Bot, Server, Check } from "lucide-react";
import { cn } from "@/lib/utils";

export type FunctionMode = "inline" | "worker";

interface FunctionStepTypeProps {
  mode: FunctionMode;
  onModeChange: (mode: FunctionMode) => void;
  disabled?: boolean;
}

const MODE_OPTIONS = [
  {
    value: "inline" as const,
    label: "AI Agent",
    description: "Powered by an LLM that can reason and use tools to complete tasks autonomously.",
    icon: Bot,
    features: ["LLM-powered reasoning", "Tool calling", "Multi-step workflows"],
  },
  {
    value: "worker" as const,
    label: "Worker",
    description: "Calls your HTTP endpoint directly. You handle all the business logic.",
    icon: Server,
    features: ["Direct HTTP calls", "Full control", "Custom logic"],
  },
];

export function FunctionStepType({
  mode,
  onModeChange,
  disabled = false,
}: FunctionStepTypeProps) {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold mb-1">Function Type</h2>
        <p className="text-sm text-muted-foreground">
          Choose how this function will process incoming events or requests.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {MODE_OPTIONS.map((option) => {
          const Icon = option.icon;
          const isSelected = mode === option.value;

          return (
            <button
              key={option.value}
              type="button"
              onClick={() => onModeChange(option.value)}
              disabled={disabled}
              className={cn(
                "relative text-left p-5 rounded-xl border-2 transition-all",
                isSelected
                  ? "border-primary bg-primary/5 ring-2 ring-primary/20"
                  : "border-border bg-card hover:border-primary/50 hover:bg-muted/30",
                disabled && "opacity-50 cursor-not-allowed"
              )}
            >
              {/* Selected indicator */}
              {isSelected && (
                <div className="absolute top-3 right-3">
                  <div className="w-6 h-6 rounded-full bg-primary flex items-center justify-center">
                    <Check className="w-4 h-4 text-primary-foreground" />
                  </div>
                </div>
              )}

              <Icon
                className={cn(
                  "h-10 w-10 mb-4",
                  isSelected ? "text-primary" : "text-muted-foreground"
                )}
              />

              <h3 className="font-semibold text-lg mb-1">{option.label}</h3>
              <p className="text-sm text-muted-foreground mb-4">{option.description}</p>

              <ul className="space-y-1.5">
                {option.features.map((feature) => (
                  <li
                    key={feature}
                    className="flex items-center gap-2 text-sm text-muted-foreground"
                  >
                    <div
                      className={cn(
                        "w-1.5 h-1.5 rounded-full",
                        isSelected ? "bg-primary" : "bg-muted-foreground/50"
                      )}
                    />
                    {feature}
                  </li>
                ))}
              </ul>
            </button>
          );
        })}
      </div>

      {/* Mode-specific info */}
      <Card className="bg-muted/30">
        <CardContent className="p-4">
          {mode === "inline" ? (
            <div className="text-sm text-muted-foreground">
              <strong className="text-foreground">AI Agent</strong> functions use a language model
              to interpret incoming data, decide which tools to use, and complete tasks
              autonomously. Great for complex workflows that require reasoning.
            </div>
          ) : (
            <div className="text-sm text-muted-foreground">
              <strong className="text-foreground">Worker</strong> functions forward incoming data
              directly to your HTTP endpoint. You receive a POST request with JSON payload and
              return the result. Ideal for integrating existing services.
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

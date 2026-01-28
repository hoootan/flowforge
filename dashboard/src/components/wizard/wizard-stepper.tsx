"use client";

import { cn } from "@/lib/utils";
import { Check } from "lucide-react";
import type { WizardStep } from "./use-wizard";

interface WizardStepperProps {
  steps: WizardStep[];
  currentStep: number;
  completedSteps: Set<number>;
  onStepClick?: (index: number) => void;
  className?: string;
}

export function WizardStepper({
  steps,
  currentStep,
  completedSteps,
  onStepClick,
  className,
}: WizardStepperProps) {
  const maxClickable = Math.max(...Array.from(completedSteps), -1) + 1;

  return (
    <nav className={cn("flex flex-col gap-1", className)} aria-label="Progress">
      {steps.map((step, index) => {
        const isCompleted = completedSteps.has(index);
        const isCurrent = index === currentStep;
        const isClickable = index <= maxClickable;

        return (
          <button
            key={step.id}
            type="button"
            onClick={() => isClickable && onStepClick?.(index)}
            disabled={!isClickable}
            className={cn(
              "flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-all group",
              isCurrent && "bg-primary/10",
              isClickable && !isCurrent && "hover:bg-muted/50 cursor-pointer",
              !isClickable && "opacity-50 cursor-not-allowed"
            )}
          >
            {/* Step indicator */}
            <div
              className={cn(
                "w-7 h-7 rounded-full flex items-center justify-center text-xs font-medium shrink-0 transition-colors",
                isCompleted && "bg-primary text-primary-foreground",
                isCurrent && !isCompleted && "bg-primary text-primary-foreground",
                !isCurrent && !isCompleted && "bg-muted text-muted-foreground"
              )}
            >
              {isCompleted ? (
                <Check className="w-4 h-4" />
              ) : (
                <span>{index + 1}</span>
              )}
            </div>

            {/* Step label */}
            <div className="min-w-0 hidden md:block">
              <div
                className={cn(
                  "text-sm font-medium truncate",
                  isCurrent && "text-foreground",
                  !isCurrent && "text-muted-foreground"
                )}
              >
                {step.label}
              </div>
              {step.optional && (
                <div className="text-[10px] text-muted-foreground">Optional</div>
              )}
            </div>

            {/* Active indicator line */}
            {isCurrent && (
              <div className="ml-auto w-1 h-5 bg-primary rounded-full hidden md:block" />
            )}
          </button>
        );
      })}
    </nav>
  );
}

// Compact version for mobile - shows as a horizontal progress bar
export function WizardStepperCompact({
  steps,
  currentStep,
  completedSteps,
  className,
}: Omit<WizardStepperProps, "onStepClick">) {
  return (
    <div className={cn("flex items-center gap-2", className)}>
      {steps.map((step, index) => {
        const isCompleted = completedSteps.has(index);
        const isCurrent = index === currentStep;

        return (
          <div key={step.id} className="flex items-center gap-2">
            <div
              className={cn(
                "w-2 h-2 rounded-full transition-colors",
                isCompleted && "bg-primary",
                isCurrent && !isCompleted && "bg-primary",
                !isCurrent && !isCompleted && "bg-muted"
              )}
            />
            {index < steps.length - 1 && (
              <div
                className={cn(
                  "w-6 h-0.5 transition-colors",
                  isCompleted ? "bg-primary" : "bg-muted"
                )}
              />
            )}
          </div>
        );
      })}
      <span className="ml-2 text-xs text-muted-foreground">
        Step {currentStep + 1} of {steps.length}
      </span>
    </div>
  );
}

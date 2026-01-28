"use client";

import { Button } from "@/components/ui/button";
import { Loader2, ArrowRight, ArrowLeft, SkipForward } from "lucide-react";
import { cn } from "@/lib/utils";

interface WizardNavigationProps {
  onBack?: () => void;
  onNext?: () => void;
  onSkip?: () => void;
  isFirstStep: boolean;
  isLastStep: boolean;
  canSkip?: boolean;
  loading?: boolean;
  nextLabel?: string;
  backLabel?: string;
  className?: string;
}

export function WizardNavigation({
  onBack,
  onNext,
  onSkip,
  isFirstStep,
  isLastStep,
  canSkip = false,
  loading = false,
  nextLabel,
  backLabel = "Back",
  className,
}: WizardNavigationProps) {
  const finalNextLabel = nextLabel ?? (isLastStep ? "Create" : "Continue");

  return (
    <div className={cn("flex items-center justify-between pt-6 mt-6 border-t", className)}>
      <div>
        {!isFirstStep && (
          <Button
            type="button"
            variant="ghost"
            onClick={onBack}
            disabled={loading}
            className="gap-2"
          >
            <ArrowLeft className="h-4 w-4" />
            {backLabel}
          </Button>
        )}
      </div>

      <div className="flex items-center gap-2">
        {canSkip && !isLastStep && (
          <Button
            type="button"
            variant="ghost"
            onClick={onSkip}
            disabled={loading}
            className="gap-2 text-muted-foreground"
          >
            Skip
            <SkipForward className="h-4 w-4" />
          </Button>
        )}
        <Button
          type="button"
          onClick={onNext}
          disabled={loading}
          className="gap-2 min-w-[120px]"
        >
          {loading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <>
              {finalNextLabel}
              {!isLastStep && <ArrowRight className="h-4 w-4" />}
            </>
          )}
        </Button>
      </div>
    </div>
  );
}

"use client";

import { useState, useCallback, useEffect, useMemo } from "react";

export interface WizardStep {
  id: string;
  label: string;
  optional?: boolean;
  validate?: () => boolean | Promise<boolean>;
}

export interface UseWizardOptions {
  steps: WizardStep[];
  draftKey?: string;
  onComplete?: () => void | Promise<void>;
}

export interface UseWizardReturn {
  currentStep: number;
  currentStepId: string;
  isFirstStep: boolean;
  isLastStep: boolean;
  completedSteps: Set<number>;
  steps: WizardStep[];

  next: () => Promise<boolean>;
  back: () => void;
  skip: () => void;
  goTo: (index: number) => void;

  saveDraft: (data: Record<string, unknown>) => void;
  restoreDraft: () => Record<string, unknown> | null;
  clearDraft: () => void;
  hasDraft: boolean;

  canGoNext: boolean;
  canGoBack: boolean;
  canSkip: boolean;
}

export function useWizard({
  steps,
  draftKey,
  onComplete,
}: UseWizardOptions): UseWizardReturn {
  const [currentStep, setCurrentStep] = useState(0);
  const [completedSteps, setCompletedSteps] = useState<Set<number>>(new Set());
  const [hasDraft, setHasDraft] = useState(false);

  const isFirstStep = currentStep === 0;
  const isLastStep = currentStep === steps.length - 1;
  const currentStepId = steps[currentStep]?.id ?? "";
  const currentStepConfig = steps[currentStep];
  const canSkip = currentStepConfig?.optional ?? false;

  // Check for existing draft on mount
  useEffect(() => {
    if (draftKey && typeof window !== "undefined") {
      const saved = localStorage.getItem(`wizard_draft_${draftKey}`);
      setHasDraft(!!saved);
    }
  }, [draftKey]);

  const next = useCallback(async () => {
    const step = steps[currentStep];

    // Validate current step if validator exists
    if (step?.validate) {
      const isValid = await step.validate();
      if (!isValid) {
        return false;
      }
    }

    // Mark current step as completed
    setCompletedSteps((prev) => new Set([...prev, currentStep]));

    if (currentStep < steps.length - 1) {
      setCurrentStep((i) => i + 1);
      return true;
    } else {
      // Last step - trigger completion
      if (onComplete) {
        await onComplete();
      }
      return true;
    }
  }, [currentStep, steps, onComplete]);

  const back = useCallback(() => {
    if (currentStep > 0) {
      setCurrentStep((i) => i - 1);
    }
  }, [currentStep]);

  const skip = useCallback(() => {
    if (currentStepConfig?.optional && currentStep < steps.length - 1) {
      setCurrentStep((i) => i + 1);
    }
  }, [currentStep, currentStepConfig, steps.length]);

  const goTo = useCallback(
    (index: number) => {
      // Can only go to completed steps or the next step after the last completed
      const maxAllowed = Math.max(...Array.from(completedSteps), -1) + 1;
      if (index >= 0 && index <= maxAllowed && index < steps.length) {
        setCurrentStep(index);
      }
    },
    [completedSteps, steps.length]
  );

  const saveDraft = useCallback(
    (data: Record<string, unknown>) => {
      if (draftKey && typeof window !== "undefined") {
        localStorage.setItem(
          `wizard_draft_${draftKey}`,
          JSON.stringify({
            step: currentStep,
            data,
            timestamp: Date.now(),
          })
        );
        setHasDraft(true);
      }
    },
    [draftKey, currentStep]
  );

  const restoreDraft = useCallback(() => {
    if (draftKey && typeof window !== "undefined") {
      const saved = localStorage.getItem(`wizard_draft_${draftKey}`);
      if (saved) {
        try {
          const parsed = JSON.parse(saved);
          // Restore step position
          if (typeof parsed.step === "number" && parsed.step < steps.length) {
            setCurrentStep(parsed.step);
            // Mark all previous steps as completed
            const completed = new Set<number>();
            for (let i = 0; i < parsed.step; i++) {
              completed.add(i);
            }
            setCompletedSteps(completed);
          }
          return parsed.data as Record<string, unknown>;
        } catch {
          return null;
        }
      }
    }
    return null;
  }, [draftKey, steps.length]);

  const clearDraft = useCallback(() => {
    if (draftKey && typeof window !== "undefined") {
      localStorage.removeItem(`wizard_draft_${draftKey}`);
      setHasDraft(false);
    }
  }, [draftKey]);

  const canGoNext = useMemo(() => {
    return currentStep < steps.length;
  }, [currentStep, steps.length]);

  const canGoBack = useMemo(() => {
    return currentStep > 0;
  }, [currentStep]);

  return {
    currentStep,
    currentStepId,
    isFirstStep,
    isLastStep,
    completedSteps,
    steps,
    next,
    back,
    skip,
    goTo,
    saveDraft,
    restoreDraft,
    clearDraft,
    hasDraft,
    canGoNext,
    canGoBack,
    canSkip,
  };
}

"use client";

import { ReactNode } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ArrowLeft, X, Save } from "lucide-react";
import { cn } from "@/lib/utils";
import { WizardStepper, WizardStepperCompact } from "./wizard-stepper";
import type { WizardStep } from "./use-wizard";

interface WizardContainerProps {
  title: string;
  subtitle?: string;
  icon?: ReactNode;
  backHref: string;
  steps: WizardStep[];
  currentStep: number;
  completedSteps: Set<number>;
  onStepClick?: (index: number) => void;
  onSaveDraft?: () => void;
  hasDraft?: boolean;
  headerContent?: ReactNode;
  children: ReactNode;
  className?: string;
}

export function WizardContainer({
  title,
  subtitle,
  icon,
  backHref,
  steps,
  currentStep,
  completedSteps,
  onStepClick,
  onSaveDraft,
  hasDraft,
  headerContent,
  children,
  className,
}: WizardContainerProps) {
  return (
    <div className={cn("-m-6", className)}>
      {/* Sticky Header */}
      <div className="sticky top-0 z-10 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="flex items-center justify-between gap-4 px-6 py-4 max-w-7xl mx-auto">
          <div className="flex items-center gap-4 min-w-0">
            <Link href={backHref}>
              <Button variant="ghost" size="icon" className="shrink-0">
                <ArrowLeft className="h-5 w-5" />
              </Button>
            </Link>
            <div className="min-w-0">
              <h1 className="text-xl font-semibold flex items-center gap-2">
                {icon}
                {title}
              </h1>
              {subtitle && (
                <p className="text-sm text-muted-foreground truncate">{subtitle}</p>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Mobile step indicator */}
            <div className="md:hidden">
              <WizardStepperCompact
                steps={steps}
                currentStep={currentStep}
                completedSteps={completedSteps}
              />
            </div>

            {onSaveDraft && (
              <Button
                variant="outline"
                size="sm"
                onClick={onSaveDraft}
                className="gap-2 hidden sm:flex"
              >
                <Save className="h-4 w-4" />
                Save Draft
              </Button>
            )}
            <Link href={backHref}>
              <Button variant="ghost" size="icon" className="shrink-0">
                <X className="h-5 w-5" />
              </Button>
            </Link>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-5xl mx-auto px-6 py-6">
        <div className="flex gap-8">
          {/* Sidebar Stepper - Desktop only */}
          <aside className="hidden md:block w-48 shrink-0">
            <div className="sticky top-24">
              <WizardStepper
                steps={steps}
                currentStep={currentStep}
                completedSteps={completedSteps}
                onStepClick={onStepClick}
              />
            </div>
          </aside>

          {/* Step Content */}
          <div className="flex-1 min-w-0">
            {headerContent && (
              <div className="mb-4">{headerContent}</div>
            )}
            <Card className="shadow-sm">
              <CardContent className="p-6">
                {children}
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}

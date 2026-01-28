"use client";

import { useState, useCallback, useMemo, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Workflow, Zap, Clock, Globe } from "lucide-react";
import { toast } from "sonner";

import { useWizard, WizardContainer, WizardNavigation, WizardStep } from "@/components/wizard";
import { TemplateDropdown, Template } from "@/components/templates";
import { api, Tool, Function } from "@/lib/api";

import { FunctionStepType, FunctionMode } from "./function-step-type";
import { FunctionStepIdentity, TriggerType } from "./function-step-identity";
import { FunctionStepConfig } from "./function-step-config";
import { FunctionStepTools } from "./function-step-tools";
import { FunctionStepReview } from "./function-step-review";

// Template type for functions
interface FunctionTemplateData {
  id: string;
  name: string;
  triggerType: TriggerType;
  triggerValue: string;
  systemPrompt: string;
  mode: FunctionMode;
}

const FUNCTION_TEMPLATES: Template<FunctionTemplateData>[] = [
  {
    id: "order-processor",
    name: "Order Processor",
    description: "Automatically process new orders with AI-powered validation",
    icon: <Zap className="h-4 w-4 text-amber-500" />,
    tags: ["event", "orders"],
    data: {
      id: "process-order",
      name: "Order Processor",
      triggerType: "event",
      triggerValue: "order/created",
      mode: "inline",
      systemPrompt:
        "You are an order processing assistant. When a new order comes in, verify the order details, check inventory availability, and notify the customer about their order status. Use the available tools to complete these tasks.",
    },
  },
  {
    id: "daily-report",
    name: "Daily Report Generator",
    description: "Generate reports every day at 9 AM",
    icon: <Clock className="h-4 w-4 text-blue-500" />,
    tags: ["cron", "reports"],
    data: {
      id: "daily-report",
      name: "Daily Report Generator",
      triggerType: "cron",
      triggerValue: "0 9 * * *",
      mode: "inline",
      systemPrompt:
        "You are a reporting assistant. Generate a daily summary report of key metrics including sales, active users, and system health. Send the report to the team via email.",
    },
  },
  {
    id: "support-bot",
    name: "Customer Support Bot",
    description: "Handle customer support inquiries via webhook",
    icon: <Globe className="h-4 w-4 text-green-500" />,
    tags: ["webhook", "support"],
    data: {
      id: "support-bot",
      name: "Customer Support Bot",
      triggerType: "webhook",
      triggerValue: "/webhook/support",
      mode: "inline",
      systemPrompt:
        "You are a helpful customer support agent. Answer customer questions professionally, help resolve issues, and escalate complex problems to human agents when needed. Always be polite and helpful.",
    },
  },
];

interface FunctionWizardProps {
  initialData?: Function | null;
}

export function FunctionWizard({ initialData }: FunctionWizardProps) {
  const router = useRouter();
  const isEditMode = !!initialData;

  // Form state
  const [mode, setMode] = useState<FunctionMode>("inline");
  const [id, setId] = useState("");
  const [name, setName] = useState("");
  const [triggerType, setTriggerType] = useState<TriggerType>("event");
  const [triggerValue, setTriggerValue] = useState("");
  const [model, setModel] = useState("claude-sonnet-4-5-20250514");
  const [systemPrompt, setSystemPrompt] = useState("");
  const [selectedTools, setSelectedTools] = useState<string[]>([]);
  const [endpointUrl, setEndpointUrl] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);

  // Available tools
  const [availableTools, setAvailableTools] = useState<Tool[]>([]);
  const [toolsLoading, setToolsLoading] = useState(true);

  // Fetch tools on mount
  useEffect(() => {
    const fetchTools = async () => {
      setToolsLoading(true);
      const response = await api.getTools();
      setAvailableTools(response.tools.filter((t) => t.is_active));
      setToolsLoading(false);
    };
    fetchTools();
  }, []);

  // Initialize form with initial data when in edit mode
  useEffect(() => {
    if (initialData) {
      setMode(initialData.is_inline ? "inline" : "worker");
      setId(initialData.function_id);
      setName(initialData.name);
      setTriggerType(initialData.trigger_type);
      setTriggerValue(initialData.trigger_value);
      if (initialData.is_inline) {
        setSystemPrompt(initialData.system_prompt || "");
        setSelectedTools(initialData.tools_config || []);
        const agentConfig = initialData.agent_config as { model?: string } | null;
        if (agentConfig?.model) {
          setModel(agentConfig.model);
        }
      } else {
        setEndpointUrl(initialData.endpoint_url || "");
      }
    }
  }, [initialData]);

  // Validation functions
  const validateIdentity = useCallback(() => {
    const newErrors: Record<string, string> = {};
    if (!id.trim()) {
      newErrors.id = "Function ID is required";
    } else if (!/^[a-z][a-z0-9_-]*$/.test(id)) {
      newErrors.id = "Must be lowercase with hyphens (e.g., my-function)";
    }
    if (!name.trim()) {
      newErrors.name = "Name is required";
    }
    if (!triggerValue.trim()) {
      newErrors.trigger_value = "Trigger value is required";
    }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }, [id, name, triggerValue]);

  const validateConfig = useCallback(() => {
    const newErrors: Record<string, string> = {};
    if (mode === "inline" && !systemPrompt.trim()) {
      newErrors.system_prompt = "Instructions are required";
    }
    if (mode === "worker") {
      if (!endpointUrl.trim()) {
        newErrors.endpoint_url = "Endpoint URL is required";
      } else {
        try {
          new URL(endpointUrl);
        } catch {
          newErrors.endpoint_url = "Invalid URL";
        }
      }
    }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }, [mode, systemPrompt, endpointUrl]);

  // Dynamic steps based on mode
  const steps = useMemo<WizardStep[]>(() => {
    const baseSteps: WizardStep[] = [
      { id: "type", label: "Type" },
      { id: "identity", label: "Identity", validate: validateIdentity },
      { id: "config", label: "Config", validate: validateConfig },
    ];

    // Only add tools step for AI Agent mode
    if (mode === "inline") {
      baseSteps.push({ id: "tools", label: "Tools", optional: true });
    }

    baseSteps.push({ id: "review", label: "Review" });

    return baseSteps;
  }, [mode, validateIdentity, validateConfig]);

  // Handle form submission
  const handleComplete = useCallback(async () => {
    setLoading(true);

    let result;
    if (isEditMode) {
      // Update existing function
      if (mode === "inline") {
        result = await api.updateFunction(initialData!.function_id, {
          name: name.trim(),
          trigger: { type: triggerType, value: triggerValue.trim() },
          system_prompt: systemPrompt.trim(),
          tools: selectedTools,
          agent_config: { model, max_iterations: 30, max_tool_calls: 50 },
        });
      } else {
        result = await api.updateFunction(initialData!.function_id, {
          name: name.trim(),
          trigger: { type: triggerType, value: triggerValue.trim() },
          endpoint_url: endpointUrl.trim(),
        });
      }
    } else {
      // Create new function
      if (mode === "inline") {
        result = await api.createInlineFunction({
          id: id.trim(),
          name: name.trim(),
          trigger: { type: triggerType, value: triggerValue.trim() },
          system_prompt: systemPrompt.trim(),
          tools: selectedTools,
          agent_config: { model, max_iterations: 30, max_tool_calls: 50 },
        });
      } else {
        result = await api.createWorkerFunction({
          id: id.trim(),
          name: name.trim(),
          trigger: { type: triggerType, value: triggerValue.trim() },
          endpoint_url: endpointUrl.trim(),
          config: {},
        });
      }
    }

    setLoading(false);

    if (result) {
      toast.success(isEditMode ? "Function updated successfully" : "Function created successfully");
      router.push("/functions");
    } else {
      toast.error(isEditMode ? "Failed to update function" : "Failed to create function");
    }
  }, [isEditMode, initialData, mode, id, name, triggerType, triggerValue, systemPrompt, selectedTools, model, endpointUrl, router]);

  // Wizard hook
  const wizard = useWizard({
    steps,
    draftKey: isEditMode ? undefined : "function_wizard",
    onComplete: handleComplete,
  });

  // Handle template selection
  const handleTemplateSelect = (template: Template<FunctionTemplateData>) => {
    setMode(template.data.mode);
    setId(template.data.id);
    setName(template.data.name);
    setTriggerType(template.data.triggerType);
    setTriggerValue(template.data.triggerValue);
    setSystemPrompt(template.data.systemPrompt);
    setErrors({});
  };

  // Save draft
  const handleSaveDraft = () => {
    wizard.saveDraft({
      mode,
      id,
      name,
      triggerType,
      triggerValue,
      model,
      systemPrompt,
      selectedTools,
      endpointUrl,
    });
    toast.success("Draft saved");
  };

  // Render current step content
  const renderStepContent = () => {
    switch (wizard.currentStepId) {
      case "type":
        return (
          <FunctionStepType
            mode={mode}
            onModeChange={setMode}
            disabled={loading || isEditMode}
          />
        );
      case "identity":
        return (
          <FunctionStepIdentity
            id={id}
            name={name}
            triggerType={triggerType}
            triggerValue={triggerValue}
            onIdChange={setId}
            onNameChange={setName}
            onTriggerTypeChange={setTriggerType}
            onTriggerValueChange={setTriggerValue}
            errors={errors}
            disabled={loading}
            idDisabled={isEditMode}
          />
        );
      case "config":
        return (
          <FunctionStepConfig
            mode={mode}
            model={model}
            systemPrompt={systemPrompt}
            onModelChange={setModel}
            onSystemPromptChange={setSystemPrompt}
            endpointUrl={endpointUrl}
            onEndpointUrlChange={setEndpointUrl}
            errors={errors}
            disabled={loading}
          />
        );
      case "tools":
        return (
          <FunctionStepTools
            availableTools={availableTools}
            selectedTools={selectedTools}
            onSelectedToolsChange={setSelectedTools}
            loading={toolsLoading}
            disabled={loading}
          />
        );
      case "review":
        return (
          <FunctionStepReview
            mode={mode}
            id={id}
            name={name}
            triggerType={triggerType}
            triggerValue={triggerValue}
            model={model}
            systemPrompt={systemPrompt}
            selectedTools={selectedTools}
            availableTools={availableTools}
            endpointUrl={endpointUrl}
          />
        );
      default:
        return null;
    }
  };

  return (
    <WizardContainer
      title={isEditMode ? "Edit Function" : "Create Function"}
      subtitle={isEditMode ? "Update your function configuration" : "Define an automated workflow triggered by events, schedules, or webhooks"}
      icon={<Workflow className="h-5 w-5 text-primary" />}
      backHref="/functions"
      steps={wizard.steps}
      currentStep={wizard.currentStep}
      completedSteps={wizard.completedSteps}
      onStepClick={wizard.goTo}
      onSaveDraft={isEditMode ? undefined : handleSaveDraft}
      hasDraft={wizard.hasDraft}
      headerContent={
        !isEditMode ? (
          <TemplateDropdown
            templates={FUNCTION_TEMPLATES}
            onSelect={handleTemplateSelect}
            disabled={loading}
          />
        ) : undefined
      }
    >
      {renderStepContent()}

      <WizardNavigation
        onBack={wizard.back}
        onNext={wizard.next}
        onSkip={wizard.skip}
        isFirstStep={wizard.isFirstStep}
        isLastStep={wizard.isLastStep}
        canSkip={wizard.canSkip}
        loading={loading}
        nextLabel={wizard.isLastStep ? (isEditMode ? "Save Changes" : "Create Function") : undefined}
      />
    </WizardContainer>
  );
}

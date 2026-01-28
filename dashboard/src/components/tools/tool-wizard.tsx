"use client";

import { useState, useCallback, useMemo, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Wrench } from "lucide-react";
import { toast } from "sonner";

import { useWizard, WizardContainer, WizardNavigation } from "@/components/wizard";
import { TemplateDropdown, Template } from "@/components/templates";
import { api, Tool } from "@/lib/api";

import { ToolStepBasics } from "./tool-step-basics";
import { ToolStepParameters, ToolParameter } from "./tool-step-parameters";
import { ToolStepCode } from "./tool-step-code";
import { ToolStepReview } from "./tool-step-review";

// Template type for tools
interface ToolTemplateData {
  name: string;
  description: string;
  parameters: Omit<ToolParameter, "id">[];
}

const TOOL_TEMPLATES: Template<ToolTemplateData>[] = [
  {
    id: "send_email",
    name: "Send Email",
    description: "Send an email to a recipient with subject and body",
    tags: ["email", "communication"],
    data: {
      name: "send_email",
      description: "Send an email to a recipient with subject and body",
      parameters: [
        { name: "to", type: "string", description: "Recipient email address", required: true },
        { name: "subject", type: "string", description: "Email subject line", required: true },
        { name: "body", type: "string", description: "Email content", required: true },
      ],
    },
  },
  {
    id: "search_database",
    name: "Search Database",
    description: "Search for records in the database matching a query",
    tags: ["database", "search"],
    data: {
      name: "search_database",
      description: "Search for records in the database matching a query",
      parameters: [
        { name: "query", type: "string", description: "Search query", required: true },
        { name: "limit", type: "number", description: "Maximum results to return", required: false },
      ],
    },
  },
  {
    id: "create_ticket",
    name: "Create Ticket",
    description: "Create a new support ticket in the system",
    tags: ["support", "ticketing"],
    data: {
      name: "create_ticket",
      description: "Create a new support ticket in the system",
      parameters: [
        { name: "title", type: "string", description: "Ticket title", required: true },
        { name: "priority", type: "string", description: "Priority: low, medium, high", required: true },
        { name: "description", type: "string", description: "Detailed description", required: false },
      ],
    },
  },
];

// Helper to convert JSON schema parameters to ToolParameter array
function parseJsonSchemaParameters(parameters: Record<string, unknown>): ToolParameter[] {
  const properties = (parameters as { properties?: Record<string, { type: string; description?: string }> }).properties;
  const required = (parameters as { required?: string[] }).required || [];

  if (!properties) return [];

  return Object.entries(properties).map(([name, prop]) => ({
    id: crypto.randomUUID(),
    name,
    type: prop.type as ToolParameter["type"],
    description: prop.description || "",
    required: required.includes(name),
  }));
}

interface ToolWizardProps {
  initialData?: Tool | null;
}

export function ToolWizard({ initialData }: ToolWizardProps) {
  const router = useRouter();
  const isEditMode = !!initialData;

  // Form state
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [parameters, setParameters] = useState<ToolParameter[]>([]);
  const [code, setCode] = useState("");
  const [codeEnabled, setCodeEnabled] = useState(false);
  const [requiresApproval, setRequiresApproval] = useState(false);
  const [approvalTimeout, setApprovalTimeout] = useState("1h");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);

  // Initialize form with initial data when in edit mode
  useEffect(() => {
    if (initialData) {
      setName(initialData.name);
      setDescription(initialData.description);
      setParameters(parseJsonSchemaParameters(initialData.parameters));
      setCode(initialData.code || "");
      setCodeEnabled(!!initialData.code);
      setRequiresApproval(initialData.requires_approval);
      setApprovalTimeout(initialData.approval_timeout || "1h");
    }
  }, [initialData]);

  // Validation functions for each step
  const validateBasics = useCallback(() => {
    const newErrors: Record<string, string> = {};
    if (!name.trim()) {
      newErrors.name = "Tool name is required";
    } else if (!/^[a-z][a-z0-9_]*$/.test(name)) {
      newErrors.name = "Must be lowercase with underscores (e.g., my_tool)";
    }
    if (!description.trim()) {
      newErrors.description = "Description is required";
    }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }, [name, description]);

  const validateParameters = useCallback(() => {
    const newErrors: Record<string, string> = {};
    parameters.forEach((param, i) => {
      if (!param.name.trim()) {
        newErrors[`param_${i}`] = "Parameter name is required";
      } else if (!/^[a-z][a-z0-9_]*$/.test(param.name)) {
        newErrors[`param_${i}`] = "Must be lowercase with underscores";
      }
    });
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }, [parameters]);

  // Steps configuration
  const steps = useMemo(
    () => [
      { id: "basics", label: "Basics", validate: validateBasics },
      { id: "parameters", label: "Parameters", validate: validateParameters },
      { id: "code", label: "Code", optional: true },
      { id: "review", label: "Review" },
    ],
    [validateBasics, validateParameters]
  );

  // Build JSON schema from parameters
  const buildJsonSchema = useCallback(() => {
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
  }, [parameters]);

  // Handle form submission
  const handleComplete = useCallback(async () => {
    setLoading(true);

    let result;
    if (isEditMode) {
      // Update existing tool
      result = await api.updateTool(initialData!.name, {
        description: description.trim(),
        parameters: buildJsonSchema(),
        code: codeEnabled && code.trim() ? code.trim() : undefined,
        requires_approval: requiresApproval,
        approval_timeout: requiresApproval ? approvalTimeout : undefined,
      });
    } else {
      // Create new tool
      result = await api.createTool({
        name: name.trim(),
        description: description.trim(),
        parameters: buildJsonSchema(),
        code: codeEnabled && code.trim() ? code.trim() : undefined,
        requires_approval: requiresApproval,
        approval_timeout: requiresApproval ? approvalTimeout : undefined,
      });
    }

    setLoading(false);

    if (result) {
      toast.success(isEditMode ? "Tool updated successfully" : "Tool created successfully");
      router.push("/tools");
    } else {
      toast.error(isEditMode ? "Failed to update tool" : "Failed to create tool");
    }
  }, [isEditMode, initialData, name, description, buildJsonSchema, codeEnabled, code, requiresApproval, approvalTimeout, router]);

  // Wizard hook
  const wizard = useWizard({
    steps,
    draftKey: isEditMode ? undefined : "tool_wizard",
    onComplete: handleComplete,
  });

  // Handle template selection
  const handleTemplateSelect = (template: Template<ToolTemplateData>) => {
    setName(template.data.name);
    setDescription(template.data.description);
    setParameters(
      template.data.parameters.map((p) => ({
        ...p,
        id: crypto.randomUUID(),
        type: p.type as ToolParameter["type"],
      }))
    );
    setErrors({});
  };

  // Save draft
  const handleSaveDraft = () => {
    wizard.saveDraft({
      name,
      description,
      parameters,
      code,
      codeEnabled,
      requiresApproval,
      approvalTimeout,
    });
    toast.success("Draft saved");
  };

  // Render current step content
  const renderStepContent = () => {
    switch (wizard.currentStepId) {
      case "basics":
        return (
          <ToolStepBasics
            name={name}
            description={description}
            onNameChange={setName}
            onDescriptionChange={setDescription}
            errors={errors}
            disabled={loading}
            nameDisabled={isEditMode}
          />
        );
      case "parameters":
        return (
          <ToolStepParameters
            parameters={parameters}
            onParametersChange={setParameters}
            errors={errors}
            disabled={loading}
          />
        );
      case "code":
        return (
          <ToolStepCode
            code={code}
            onCodeChange={setCode}
            enabled={codeEnabled}
            onEnabledChange={setCodeEnabled}
            parameters={parameters}
            disabled={loading}
          />
        );
      case "review":
        return (
          <ToolStepReview
            name={name}
            description={description}
            parameters={parameters}
            code={code}
            codeEnabled={codeEnabled}
            requiresApproval={requiresApproval}
            approvalTimeout={approvalTimeout}
            onRequiresApprovalChange={setRequiresApproval}
            onApprovalTimeoutChange={setApprovalTimeout}
            disabled={loading}
          />
        );
      default:
        return null;
    }
  };

  return (
    <WizardContainer
      title={isEditMode ? "Edit Tool" : "Create Tool"}
      subtitle={isEditMode ? "Update your tool configuration" : "Define a tool that AI agents can use in your workflows"}
      icon={<Wrench className="h-5 w-5 text-primary" />}
      backHref="/tools"
      steps={wizard.steps}
      currentStep={wizard.currentStep}
      completedSteps={wizard.completedSteps}
      onStepClick={wizard.goTo}
      onSaveDraft={isEditMode ? undefined : handleSaveDraft}
      hasDraft={wizard.hasDraft}
      headerContent={
        !isEditMode ? (
          <TemplateDropdown
            templates={TOOL_TEMPLATES}
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
        nextLabel={wizard.isLastStep ? (isEditMode ? "Save Changes" : "Create Tool") : undefined}
      />
    </WizardContainer>
  );
}

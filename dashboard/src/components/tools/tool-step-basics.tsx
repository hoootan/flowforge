"use client";

import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { FormField } from "@/components/forms/form-field";

interface ToolStepBasicsProps {
  name: string;
  description: string;
  onNameChange: (value: string) => void;
  onDescriptionChange: (value: string) => void;
  errors: Record<string, string>;
  disabled?: boolean;
  nameDisabled?: boolean;
}

export function ToolStepBasics({
  name,
  description,
  onNameChange,
  onDescriptionChange,
  errors,
  disabled = false,
  nameDisabled = false,
}: ToolStepBasicsProps) {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold mb-1">Basic Information</h2>
        <p className="text-sm text-muted-foreground">
          Give your tool a name and description that helps the AI understand when to use it.
        </p>
      </div>

      <FormField
        label="Tool Name"
        required
        description={!errors.name ? (nameDisabled ? "Tool name cannot be changed" : "Lowercase with underscores (e.g., my_tool_name)") : undefined}
        error={errors.name}
        htmlFor="tool-name"
      >
        <Input
          id="tool-name"
          value={name}
          onChange={(e) => onNameChange(e.target.value.toLowerCase().replace(/\s/g, "_"))}
          placeholder="my_tool_name"
          className="font-mono h-10"
          disabled={disabled || nameDisabled}
        />
      </FormField>

      <FormField
        label="Description"
        required
        description={!errors.description ? "The AI reads this to decide when to use the tool" : undefined}
        error={errors.description}
        htmlFor="tool-description"
      >
        <Textarea
          id="tool-description"
          value={description}
          onChange={(e) => onDescriptionChange(e.target.value)}
          placeholder="Describe what this tool does. Be specific about inputs and outputs so the AI knows when to use it."
          rows={4}
          className="text-sm resize-none leading-relaxed"
          disabled={disabled}
        />
      </FormField>
    </div>
  );
}

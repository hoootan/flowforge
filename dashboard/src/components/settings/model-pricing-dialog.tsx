"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";
import api from "@/lib/api";
import type { ModelPricingConfig, EffectiveModelPricing, DefaultModelPricing } from "@/lib/api";

interface ModelPricingDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  pricing: ModelPricingConfig | null; // null = create mode
  existingModels: EffectiveModelPricing[];
  defaults: DefaultModelPricing[];
  onSuccess: () => void;
}

const KNOWN_PROVIDERS = ["openai", "anthropic", "google", "mistral", "cohere", "custom"];

export function ModelPricingDialog({
  open,
  onOpenChange,
  pricing,
  existingModels,
  defaults,
  onSuccess,
}: ModelPricingDialogProps) {
  const isEdit = pricing !== null;

  const [modelId, setModelId] = useState("");
  const [provider, setProvider] = useState("openai");
  const [inputPrice, setInputPrice] = useState("");
  const [outputPrice, setOutputPrice] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [isGlobal, setIsGlobal] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Populate form when editing
  useEffect(() => {
    if (pricing) {
      setModelId(pricing.model_id);
      setProvider(pricing.provider);
      setInputPrice(String(pricing.input_price_per_m));
      setOutputPrice(String(pricing.output_price_per_m));
      setDisplayName(pricing.display_name || "");
      setIsGlobal(pricing.is_global);
    } else {
      // Reset form for create mode
      setModelId("");
      setProvider("openai");
      setInputPrice("");
      setOutputPrice("");
      setDisplayName("");
      setIsGlobal(false);
    }
  }, [pricing, open]);

  // Auto-fill pricing from defaults when model is selected/typed
  useEffect(() => {
    if (!isEdit && modelId) {
      const defaultPricing = defaults.find((d) => d.model_id === modelId);
      if (defaultPricing) {
        setProvider(defaultPricing.provider);
        if (!inputPrice) setInputPrice(String(defaultPricing.input_price_per_m));
        if (!outputPrice) setOutputPrice(String(defaultPricing.output_price_per_m));
      }
    }
  }, [modelId, defaults, isEdit, inputPrice, outputPrice]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!modelId.trim()) {
      toast.error("Model ID is required");
      return;
    }

    const inputPriceNum = parseFloat(inputPrice);
    const outputPriceNum = parseFloat(outputPrice);

    if (isNaN(inputPriceNum) || inputPriceNum < 0) {
      toast.error("Invalid input price");
      return;
    }

    if (isNaN(outputPriceNum) || outputPriceNum < 0) {
      toast.error("Invalid output price");
      return;
    }

    setIsSubmitting(true);

    try {
      if (isEdit) {
        // Update existing pricing
        const result = await api.updateModelPricing(pricing!.id, {
          input_price_per_m: inputPriceNum,
          output_price_per_m: outputPriceNum,
          display_name: displayName || undefined,
        });

        if (result) {
          toast.success("Pricing updated successfully");
          onSuccess();
          onOpenChange(false);
        } else {
          toast.error("Failed to update pricing");
        }
      } else {
        // Create new pricing
        const result = await api.createModelPricing({
          model_id: modelId.trim(),
          provider: provider,
          input_price_per_m: inputPriceNum,
          output_price_per_m: outputPriceNum,
          display_name: displayName || undefined,
          is_global: isGlobal,
        });

        if (result) {
          toast.success("Pricing created successfully");
          onSuccess();
          onOpenChange(false);
        } else {
          toast.error("Failed to create pricing");
        }
      }
    } catch (error) {
      toast.error("An error occurred");
    } finally {
      setIsSubmitting(false);
    }
  };

  // Get list of models from defaults that don't have custom pricing yet
  const availableModelsFromDefaults = defaults.filter(
    (d) => !existingModels.some((e) => e.model_id === d.model_id && e.source !== "default")
  );

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>{isEdit ? "Edit Pricing" : "Add Custom Pricing"}</DialogTitle>
            <DialogDescription>
              {isEdit
                ? "Update the pricing for this model."
                : "Configure custom pricing for an AI model. This overrides the default pricing."}
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-4 py-4">
            {/* Model ID */}
            <div className="space-y-2">
              <Label htmlFor="model-id">Model ID</Label>
              {isEdit ? (
                <Input id="model-id" value={modelId} disabled className="font-mono" />
              ) : (
                <div className="flex gap-2">
                  <Input
                    id="model-id"
                    value={modelId}
                    onChange={(e) => setModelId(e.target.value)}
                    placeholder="e.g., gpt-4o or my-custom-model"
                    className="font-mono flex-1"
                    list="model-suggestions"
                  />
                  <datalist id="model-suggestions">
                    {availableModelsFromDefaults.map((d) => (
                      <option key={d.model_id} value={d.model_id} />
                    ))}
                  </datalist>
                </div>
              )}
              {!isEdit && (
                <p className="text-xs text-muted-foreground">
                  Enter any model name - can be standard or custom/fine-tuned models
                </p>
              )}
            </div>

            {/* Provider */}
            <div className="space-y-2">
              <Label htmlFor="provider">Provider</Label>
              <Select value={provider} onValueChange={setProvider} disabled={isEdit}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {KNOWN_PROVIDERS.map((p) => (
                    <SelectItem key={p} value={p}>
                      {p.charAt(0).toUpperCase() + p.slice(1)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Pricing */}
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="input-price">Input Price (per 1M tokens)</Label>
                <div className="relative">
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">
                    $
                  </span>
                  <Input
                    id="input-price"
                    type="number"
                    step="0.01"
                    min="0"
                    value={inputPrice}
                    onChange={(e) => setInputPrice(e.target.value)}
                    placeholder="0.00"
                    className="pl-7"
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="output-price">Output Price (per 1M tokens)</Label>
                <div className="relative">
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">
                    $
                  </span>
                  <Input
                    id="output-price"
                    type="number"
                    step="0.01"
                    min="0"
                    value={outputPrice}
                    onChange={(e) => setOutputPrice(e.target.value)}
                    placeholder="0.00"
                    className="pl-7"
                  />
                </div>
              </div>
            </div>

            {/* Display Name (optional) */}
            <div className="space-y-2">
              <Label htmlFor="display-name">Display Name (optional)</Label>
              <Input
                id="display-name"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                placeholder="e.g., GPT-4o"
              />
            </div>

            {/* Global checkbox (only for create) */}
            {!isEdit && (
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="is-global"
                  checked={isGlobal}
                  onCheckedChange={(checked) => setIsGlobal(checked === true)}
                />
                <Label htmlFor="is-global" className="text-sm font-normal">
                  Global pricing (applies to all tenants as default)
                </Label>
              </div>
            )}
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {isEdit ? "Save Changes" : "Create Pricing"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

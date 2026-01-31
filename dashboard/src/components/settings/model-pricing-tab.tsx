"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  DollarSign,
  Plus,
  AlertCircle,
  Trash2,
  Edit,
  Loader2,
  Globe,
  Building2,
  Database,
  HelpCircle,
} from "lucide-react";
import { toast } from "sonner";
import { usePermissions } from "@/stores/auth-store";
import { ModelPricingDialog } from "./model-pricing-dialog";
import api from "@/lib/api";
import type {
  EffectiveModelPricing,
  ModelPricingConfig,
  DefaultModelPricing,
  PricingSource,
} from "@/lib/api";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

// Source badge colors
const sourceStyles: Record<PricingSource, { label: string; variant: "default" | "secondary" | "outline"; icon: React.ReactNode }> = {
  tenant: {
    label: "Tenant",
    variant: "default",
    icon: <Building2 className="h-3 w-3" />,
  },
  global: {
    label: "Global",
    variant: "secondary",
    icon: <Globe className="h-3 w-3" />,
  },
  default: {
    label: "Default",
    variant: "outline",
    icon: <Database className="h-3 w-3" />,
  },
  fallback: {
    label: "Fallback",
    variant: "outline",
    icon: <HelpCircle className="h-3 w-3" />,
  },
};

// Provider colors for visual distinction
const providerColors: Record<string, string> = {
  openai: "text-emerald-600",
  anthropic: "text-orange-600",
  google: "text-blue-600",
  mistral: "text-purple-600",
  cohere: "text-pink-600",
};

function formatPrice(price: number): string {
  return `$${price.toFixed(2)}`;
}

interface PricingRowProps {
  model: EffectiveModelPricing;
  customConfig: ModelPricingConfig | undefined;
  onEdit: (config: ModelPricingConfig) => void;
  onDelete: (id: string) => void;
  isAdmin: boolean;
}

function PricingRow({ model, customConfig, onEdit, onDelete, isAdmin }: PricingRowProps) {
  const sourceStyle = sourceStyles[model.source];
  const providerColor = providerColors[model.provider] || "text-slate-600";
  const hasCustomPricing = model.source === "tenant" || model.source === "global";

  return (
    <TableRow>
      <TableCell>
        <div>
          <span className="font-mono text-sm">{model.model_id}</span>
          {model.display_name && (
            <span className="ml-2 text-xs text-muted-foreground">({model.display_name})</span>
          )}
        </div>
      </TableCell>
      <TableCell>
        <span className={`capitalize ${providerColor}`}>{model.provider}</span>
      </TableCell>
      <TableCell className="text-right font-mono">
        {formatPrice(model.input_price_per_m)}
      </TableCell>
      <TableCell className="text-right font-mono">
        {formatPrice(model.output_price_per_m)}
      </TableCell>
      <TableCell>
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <Badge variant={sourceStyle.variant} className="gap-1">
                {sourceStyle.icon}
                {sourceStyle.label}
              </Badge>
            </TooltipTrigger>
            <TooltipContent>
              {model.source === "tenant" && "Custom pricing for this tenant"}
              {model.source === "global" && "Custom global pricing (admin-set default)"}
              {model.source === "default" && "Hardcoded default pricing"}
              {model.source === "fallback" && "Fallback pricing for unknown models"}
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </TableCell>
      <TableCell className="text-right">
        {isAdmin && hasCustomPricing && customConfig && (
          <div className="flex justify-end gap-1">
            <Button variant="ghost" size="sm" onClick={() => onEdit(customConfig)}>
              <Edit className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onDelete(customConfig.id)}
              className="text-destructive hover:text-destructive"
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        )}
      </TableCell>
    </TableRow>
  );
}

export function ModelPricingTab() {
  const { isAdmin } = usePermissions();
  const [effectiveModels, setEffectiveModels] = useState<EffectiveModelPricing[]>([]);
  const [customConfigs, setCustomConfigs] = useState<ModelPricingConfig[]>([]);
  const [defaults, setDefaults] = useState<DefaultModelPricing[]>([]);
  const [fallbackPricing, setFallbackPricing] = useState({ input: 1.0, output: 2.0 });
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingPricing, setEditingPricing] = useState<ModelPricingConfig | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    try {
      const [effectiveResponse, configsResponse, defaultsResponse] = await Promise.all([
        api.getEffectiveModelPricing(),
        api.getModelPricingConfigs(),
        api.getDefaultModelPricing(),
      ]);

      setEffectiveModels(effectiveResponse.models);
      setCustomConfigs(configsResponse.pricing_configs);
      setDefaults(defaultsResponse.defaults);
      setFallbackPricing({
        input: defaultsResponse.fallback_input_price,
        output: defaultsResponse.fallback_output_price,
      });
    } catch (error) {
      toast.error("Failed to load pricing data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleEdit = (config: ModelPricingConfig) => {
    setEditingPricing(config);
    setDialogOpen(true);
  };

  const handleCreate = () => {
    setEditingPricing(null);
    setDialogOpen(true);
  };

  const handleDelete = async () => {
    if (!deletingId) return;

    const success = await api.deleteModelPricing(deletingId);
    if (success) {
      toast.success("Pricing deleted - model will use default pricing");
      loadData();
    } else {
      toast.error("Failed to delete pricing");
    }
    setDeleteDialogOpen(false);
    setDeletingId(null);
  };

  const confirmDelete = (id: string) => {
    setDeletingId(id);
    setDeleteDialogOpen(true);
  };

  const handleDialogSuccess = () => {
    loadData();
  };

  // Get custom config for a model by its pricing_id
  const getCustomConfig = (model: EffectiveModelPricing): ModelPricingConfig | undefined => {
    if (!model.pricing_id) return undefined;
    return customConfigs.find((c) => c.id === model.pricing_id);
  };

  // Sort models: custom pricing first, then by provider, then by model name
  const sortedModels = [...effectiveModels].sort((a, b) => {
    // Custom pricing first
    const aHasCustom = a.source === "tenant" || a.source === "global";
    const bHasCustom = b.source === "tenant" || b.source === "global";
    if (aHasCustom && !bHasCustom) return -1;
    if (!aHasCustom && bHasCustom) return 1;

    // Then by provider
    if (a.provider !== b.provider) return a.provider.localeCompare(b.provider);

    // Then by model name
    return a.model_id.localeCompare(b.model_id);
  });

  return (
    <div className="space-y-6">
      <Alert>
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>
          Configure custom pricing to override default costs. Pricing priority: Tenant-specific
          &gt; Global &gt; Default &gt; Fallback (${fallbackPricing.input}/${fallbackPricing.output} per 1M tokens).
        </AlertDescription>
      </Alert>

      {/* Model Pricing Table */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <DollarSign className="h-5 w-5" />
              Model Pricing
            </CardTitle>
            <CardDescription>
              View and customize pricing for AI models. Costs are per 1 million tokens.
            </CardDescription>
          </div>
          {isAdmin && (
            <Button size="sm" onClick={handleCreate}>
              <Plus className="mr-2 h-4 w-4" />
              Add Custom Pricing
            </Button>
          )}
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : sortedModels.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-8 text-center">
              <DollarSign className="h-12 w-12 text-muted-foreground/50" />
              <p className="mt-4 text-sm text-muted-foreground">No models found.</p>
            </div>
          ) : (
            <div className="rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Model</TableHead>
                    <TableHead>Provider</TableHead>
                    <TableHead className="text-right">Input $/1M</TableHead>
                    <TableHead className="text-right">Output $/1M</TableHead>
                    <TableHead>Source</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {sortedModels.map((model) => (
                    <PricingRow
                      key={model.model_id}
                      model={model}
                      customConfig={getCustomConfig(model)}
                      onEdit={handleEdit}
                      onDelete={confirmDelete}
                      isAdmin={isAdmin}
                    />
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Custom Pricing Overview */}
      {customConfigs.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Custom Pricing Summary</CardTitle>
            <CardDescription>
              You have {customConfigs.length} custom pricing configuration{customConfigs.length !== 1 ? "s" : ""}.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {customConfigs.map((config) => (
                <Badge key={config.id} variant={config.is_global ? "secondary" : "default"}>
                  {config.is_global && <Globe className="mr-1 h-3 w-3" />}
                  {config.model_id}
                </Badge>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Pricing Dialog */}
      <ModelPricingDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        pricing={editingPricing}
        existingModels={effectiveModels}
        defaults={defaults}
        onSuccess={handleDialogSuccess}
      />

      {/* Delete Confirmation */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Custom Pricing</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete this custom pricing? The model will fall back to
              the next available pricing source (global, default, or fallback).
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

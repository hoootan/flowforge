"use client";

import { useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Loader2, Eye, EyeOff } from "lucide-react";
import { toast } from "sonner";
import api from "@/lib/api";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import type { AIProvider, AuthType, KnownProviderInfo, CreateAIProviderRequest, UpdateAIProviderRequest } from "@/lib/api";

interface ProviderDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  provider: AIProvider | null; // null = create mode
  knownProviders: KnownProviderInfo[];
  onSuccess: () => void;
}

type ProviderName = "openai" | "anthropic" | "google" | "mistral" | "cohere" | "custom";

export function ProviderDialog({
  open,
  onOpenChange,
  provider,
  knownProviders,
  onSuccess,
}: ProviderDialogProps) {
  const isEditing = provider !== null;

  const [providerName, setProviderName] = useState<ProviderName>("openai");
  const [displayName, setDisplayName] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [authType, setAuthType] = useState<AuthType>("api_key");
  const [baseUrl, setBaseUrl] = useState("");
  const [isDefault, setIsDefault] = useState(false);
  const [isActive, setIsActive] = useState(true);
  const [showApiKey, setShowApiKey] = useState(false);
  const [saving, setSaving] = useState(false);

  // Reset form when dialog opens
  useEffect(() => {
    if (open) {
      if (provider) {
        // Edit mode
        setProviderName(provider.provider_name as ProviderName);
        setDisplayName(provider.display_name);
        setApiKey(""); // Don't populate - we never show the key
        setAuthType(provider.auth_type || "api_key");
        setBaseUrl(provider.base_url || "");
        setIsDefault(provider.is_default);
        setIsActive(provider.is_active);
      } else {
        // Create mode
        const firstProvider = knownProviders[0];
        setProviderName((firstProvider?.name as ProviderName) || "openai");
        setDisplayName("");
        setApiKey("");
        setAuthType("api_key");
        setBaseUrl("");
        setIsDefault(false);
        setIsActive(true);
      }
      setShowApiKey(false);
    }
  }, [open, provider, knownProviders]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);

    try {
      if (isEditing) {
        // Update existing provider by ID
        const updateData: UpdateAIProviderRequest = {
          display_name: displayName || undefined,
          base_url: baseUrl || undefined,
          is_active: isActive,
          is_default: isDefault,
          auth_type: authType,
        };

        // Only include API key if user entered a new one
        if (apiKey) {
          updateData.api_key = apiKey;
        }

        const result = await api.updateAIProvider(provider!.id, updateData);
        if (result) {
          toast.success("Provider updated");
          onOpenChange(false);
          onSuccess();
        } else {
          toast.error("Failed to update provider");
        }
      } else {
        // Create new provider
        if (!apiKey) {
          toast.error("API key is required");
          setSaving(false);
          return;
        }

        const createData: CreateAIProviderRequest = {
          provider_name: providerName,
          api_key: apiKey,
          auth_type: authType,
          display_name: displayName || undefined,
          base_url: baseUrl || undefined,
          is_default: isDefault,
        };

        const result = await api.createAIProvider(createData);
        if (result) {
          toast.success("Provider created");
          onOpenChange(false);
          onSuccess();
        } else {
          toast.error("Failed to create provider");
        }
      }
    } catch (error) {
      toast.error("An error occurred");
    } finally {
      setSaving(false);
    }
  };

  // Get the display name placeholder based on selected provider
  const selectedKnownProvider = knownProviders.find((kp) => kp.name === providerName);
  const displayNamePlaceholder = selectedKnownProvider?.display_name || providerName;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[425px]">
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>
              {isEditing ? "Edit Provider" : "Add AI Provider"}
            </DialogTitle>
            <DialogDescription>
              {isEditing
                ? "Update the provider configuration. Leave API key empty to keep the current key."
                : "Configure a new AI provider with your API key."}
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-4 py-4">
            {/* Provider Selection (only in create mode) */}
            {!isEditing && (
              <div className="grid gap-2">
                <Label htmlFor="provider">Provider</Label>
                <Select
                  value={providerName}
                  onValueChange={(value) => setProviderName(value as ProviderName)}
                >
                  <SelectTrigger id="provider">
                    <SelectValue placeholder="Select provider" />
                  </SelectTrigger>
                  <SelectContent>
                    {knownProviders.map((kp) => (
                      <SelectItem key={kp.name} value={kp.name}>
                        {kp.display_name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {selectedKnownProvider && selectedKnownProvider.models.length > 0 && (
                  <p className="text-xs text-muted-foreground">
                    Models: {selectedKnownProvider.models.slice(0, 3).join(", ")}
                    {selectedKnownProvider.models.length > 3 && "..."}
                  </p>
                )}
              </div>
            )}

            {/* Display Name */}
            <div className="grid gap-2">
              <Label htmlFor="displayName">Display Name</Label>
              <Input
                id="displayName"
                placeholder={displayNamePlaceholder}
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
              />
              <p className="text-xs text-muted-foreground">
                Optional friendly name (e.g., "Production OpenAI")
              </p>
            </div>

            {/* Auth Type */}
            <div className="grid gap-2">
              <Label>Authentication Type</Label>
              <RadioGroup
                value={authType}
                onValueChange={(value) => setAuthType(value as AuthType)}
                className="flex gap-4"
              >
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value="api_key" id="auth-api-key" />
                  <Label htmlFor="auth-api-key" className="font-normal cursor-pointer">
                    API Key
                  </Label>
                </div>
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value="oauth_token" id="auth-oauth" />
                  <Label htmlFor="auth-oauth" className="font-normal cursor-pointer">
                    OAuth Token
                  </Label>
                </div>
              </RadioGroup>
              {authType === "oauth_token" && (
                <p className="text-xs text-muted-foreground">
                  Use an OAuth bearer token (e.g., from Claude Code Max subscription)
                </p>
              )}
            </div>

            {/* API Key / OAuth Token */}
            <div className="grid gap-2">
              <Label htmlFor="apiKey">
                {authType === "oauth_token" ? "OAuth Token" : "API Key"}{" "}
                {!isEditing && <span className="text-destructive">*</span>}
              </Label>
              <div className="relative">
                <Input
                  id="apiKey"
                  type={showApiKey ? "text" : "password"}
                  placeholder={
                    isEditing
                      ? `Enter new ${authType === "oauth_token" ? "token" : "key"} to change`
                      : authType === "oauth_token"
                        ? "eyJ..."
                        : "sk-..."
                  }
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  required={!isEditing}
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="absolute right-0 top-0 h-full px-3 hover:bg-transparent"
                  onClick={() => setShowApiKey(!showApiKey)}
                >
                  {showApiKey ? (
                    <EyeOff className="h-4 w-4 text-muted-foreground" />
                  ) : (
                    <Eye className="h-4 w-4 text-muted-foreground" />
                  )}
                </Button>
              </div>
              <p className="text-xs text-muted-foreground">
                {isEditing
                  ? `Leave empty to keep current ${authType === "oauth_token" ? "token" : "key"}. Credentials are encrypted at rest.`
                  : `Your ${authType === "oauth_token" ? "OAuth token" : "API key"} will be encrypted and stored securely.`}
              </p>
            </div>

            {/* Base URL (for custom providers) */}
            {(providerName === "custom" || baseUrl) && (
              <div className="grid gap-2">
                <Label htmlFor="baseUrl">Base URL</Label>
                <Input
                  id="baseUrl"
                  type="url"
                  placeholder="https://api.example.com/v1"
                  value={baseUrl}
                  onChange={(e) => setBaseUrl(e.target.value)}
                />
                <p className="text-xs text-muted-foreground">
                  Custom API endpoint for self-hosted or proxy setups
                </p>
              </div>
            )}

            {/* Switches */}
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label htmlFor="isDefault">Set as default</Label>
                <p className="text-xs text-muted-foreground">
                  Use this provider when none is specified
                </p>
              </div>
              <Switch
                id="isDefault"
                checked={isDefault}
                onCheckedChange={setIsDefault}
              />
            </div>

            {isEditing && (
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label htmlFor="isActive">Enabled</Label>
                  <p className="text-xs text-muted-foreground">
                    Disable to temporarily stop using this provider
                  </p>
                </div>
                <Switch
                  id="isActive"
                  checked={isActive}
                  onCheckedChange={setIsActive}
                />
              </div>
            )}
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={saving}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={saving}>
              {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {isEditing ? "Save Changes" : "Add Provider"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

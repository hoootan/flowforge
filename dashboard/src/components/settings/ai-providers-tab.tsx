"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Bot,
  Plus,
  RefreshCw,
  CheckCircle,
  XCircle,
  AlertCircle,
  Trash2,
  Edit,
  Key,
  Loader2,
  Star,
} from "lucide-react";
import { toast } from "sonner";
import { usePermissions } from "@/stores/auth-store";
import { ProviderDialog } from "./provider-dialog";
import { AIUsageWidget } from "./ai-usage-widget";
import api from "@/lib/api";
import type { AIProvider, KnownProviderInfo } from "@/lib/api";
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

// Provider icons/colors
const providerStyles: Record<string, { color: string; bgColor: string }> = {
  openai: { color: "text-emerald-600", bgColor: "bg-emerald-500/10" },
  anthropic: { color: "text-orange-600", bgColor: "bg-orange-500/10" },
  google: { color: "text-blue-600", bgColor: "bg-blue-500/10" },
  mistral: { color: "text-purple-600", bgColor: "bg-purple-500/10" },
  cohere: { color: "text-pink-600", bgColor: "bg-pink-500/10" },
  custom: { color: "text-slate-600", bgColor: "bg-slate-500/10" },
};

interface ProviderCardProps {
  provider: AIProvider;
  onTest: (id: string) => Promise<void>;
  onEdit: (provider: AIProvider) => void;
  onDelete: (id: string) => void;
  onSetDefault: (id: string) => void;
  isAdmin: boolean;
  testingProvider: string | null;
}

function ProviderCard({
  provider,
  onTest,
  onEdit,
  onDelete,
  onSetDefault,
  isAdmin,
  testingProvider,
}: ProviderCardProps) {
  const styles = providerStyles[provider.provider_name] || providerStyles.custom;
  const isTesting = testingProvider === provider.id;

  return (
    <div className="flex items-center justify-between rounded-lg border p-4">
      <div className="flex items-center gap-4">
        <div className={`flex h-10 w-10 items-center justify-center rounded-lg ${styles.bgColor}`}>
          <Bot className={`h-5 w-5 ${styles.color}`} />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <span className="font-medium">{provider.display_name}</span>
            {provider.is_default && (
              <Badge variant="secondary" className="gap-1">
                <Star className="h-3 w-3" />
                Default
              </Badge>
            )}
            {!provider.is_active && (
              <Badge variant="outline" className="text-muted-foreground">
                Disabled
              </Badge>
            )}
          </div>
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Key className="h-3 w-3" />
            <span className="font-mono">{provider.api_key_prefix}</span>
            {provider.base_url && (
              <span className="text-xs">({new URL(provider.base_url).host})</span>
            )}
          </div>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => onTest(provider.id)}
          disabled={isTesting}
        >
          {isTesting ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <RefreshCw className="h-4 w-4" />
          )}
          <span className="ml-1 hidden sm:inline">Test</span>
        </Button>

        {isAdmin && (
          <>
            {!provider.is_default && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => onSetDefault(provider.id)}
              >
                <Star className="h-4 w-4" />
              </Button>
            )}
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onEdit(provider)}
            >
              <Edit className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onDelete(provider.id)}
              className="text-destructive hover:text-destructive"
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </>
        )}
      </div>
    </div>
  );
}

export function AIProvidersTab() {
  const { isAdmin } = usePermissions();
  const [providers, setProviders] = useState<AIProvider[]>([]);
  const [knownProviders, setKnownProviders] = useState<KnownProviderInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingProvider, setEditingProvider] = useState<AIProvider | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deletingProviderId, setDeletingProviderId] = useState<string | null>(null);
  const [testingProvider, setTestingProvider] = useState<string | null>(null);

  const loadProviders = async () => {
    setLoading(true);
    try {
      const [providersResponse, knownResponse] = await Promise.all([
        api.getAIProviders({ include_inactive: true }),
        api.getKnownProviders(),
      ]);
      setProviders(providersResponse.providers);
      setKnownProviders(knownResponse.providers);
    } catch (error) {
      toast.error("Failed to load providers");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadProviders();
  }, []);

  const handleTest = async (providerId: string) => {
    setTestingProvider(providerId);
    try {
      const result = await api.testAIProvider(providerId);
      if (result) {
        if (result.status === "healthy") {
          toast.success(result.message, {
            description: result.model_tested ? `Tested with ${result.model_tested}` : undefined,
          });
        } else if (result.status === "error") {
          toast.error(result.message);
        } else {
          toast.info(result.message);
        }
      } else {
        toast.error("Failed to test provider");
      }
    } catch (error) {
      toast.error("Failed to test provider");
    } finally {
      setTestingProvider(null);
    }
  };

  const handleEdit = (provider: AIProvider) => {
    setEditingProvider(provider);
    setDialogOpen(true);
  };

  const handleCreate = () => {
    setEditingProvider(null);
    setDialogOpen(true);
  };

  const handleDelete = async () => {
    if (!deletingProviderId) return;

    const success = await api.deleteAIProvider(deletingProviderId);
    if (success) {
      toast.success("Provider deleted");
      loadProviders();
    } else {
      toast.error("Failed to delete provider");
    }
    setDeleteDialogOpen(false);
    setDeletingProviderId(null);
  };

  const handleSetDefault = async (providerId: string) => {
    const result = await api.updateAIProvider(providerId, { is_default: true });
    if (result) {
      toast.success(`${result.display_name} set as default`);
      loadProviders();
    } else {
      toast.error("Failed to set default provider");
    }
  };

  const handleDialogSuccess = () => {
    loadProviders();
  };

  const confirmDelete = (providerId: string) => {
    setDeletingProviderId(providerId);
    setDeleteDialogOpen(true);
  };

  return (
    <div className="space-y-6">
      <Alert>
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>
          API keys are encrypted at rest using Fernet encryption. They are never displayed after creation.
        </AlertDescription>
      </Alert>

      {/* Configured Providers */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Bot className="h-5 w-5" />
              AI Providers
            </CardTitle>
            <CardDescription>
              Configure API keys for AI model providers. Keys are stored securely on the server.
            </CardDescription>
          </div>
          {isAdmin && (
            <Button size="sm" onClick={handleCreate}>
              <Plus className="mr-2 h-4 w-4" />
              Add Provider
            </Button>
          )}
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : providers.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-8 text-center">
              <Bot className="h-12 w-12 text-muted-foreground/50" />
              <p className="mt-4 text-sm text-muted-foreground">
                No AI providers configured.
              </p>
              {isAdmin && (
                <Button className="mt-4" onClick={handleCreate}>
                  <Plus className="mr-2 h-4 w-4" />
                  Add Your First Provider
                </Button>
              )}
            </div>
          ) : (
            <div className="space-y-3">
              {providers.map((provider) => (
                <ProviderCard
                  key={provider.id}
                  provider={provider}
                  onTest={handleTest}
                  onEdit={handleEdit}
                  onDelete={confirmDelete}
                  onSetDefault={handleSetDefault}
                  isAdmin={isAdmin}
                  testingProvider={testingProvider}
                />
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Usage Statistics */}
      <AIUsageWidget />

      {/* Provider Dialog */}
      <ProviderDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        provider={editingProvider}
        knownProviders={knownProviders}
        onSuccess={handleDialogSuccess}
      />

      {/* Delete Confirmation */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Provider</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete this provider? This will permanently remove the
              encrypted API key. This action cannot be undone.
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

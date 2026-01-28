"use client";

import { useState, useEffect } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
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
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Key,
  Plus,
  Copy,
  Trash2,
  CheckCircle2,
  Loader2,
  Rocket,
  FlaskConical,
  Eye,
  ShieldCheck,
} from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { api, type ApiKey, type ApiKeyCreated, type CreateApiKeyRequest } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

const keyTypeConfig = {
  live: {
    label: "Live",
    variant: "default" as const,
    description: "Full access for production",
    icon: Rocket,
    color: "text-emerald-500",
    bgColor: "bg-emerald-500/10",
    borderColor: "border-emerald-500/30",
  },
  test: {
    label: "Test",
    variant: "secondary" as const,
    description: "Full access for development & testing",
    icon: FlaskConical,
    color: "text-blue-500",
    bgColor: "bg-blue-500/10",
    borderColor: "border-blue-500/30",
  },
  ro: {
    label: "Read Only",
    variant: "outline" as const,
    description: "Read-only access for monitoring",
    icon: Eye,
    color: "text-amber-500",
    bgColor: "bg-amber-500/10",
    borderColor: "border-amber-500/30",
  },
};

type KeyType = keyof typeof keyTypeConfig;

export function ApiKeysTab() {
  const { token } = useAuthStore();
  const [keys, setKeys] = useState<ApiKey[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [newKeyDialogOpen, setNewKeyDialogOpen] = useState(false);
  const [createdKey, setCreatedKey] = useState<ApiKeyCreated | null>(null);
  const [keyName, setKeyName] = useState("");
  const [keyType, setKeyType] = useState<KeyType>("test");
  const [isCreating, setIsCreating] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    api.setTokenProvider(() => token);
  }, [token]);

  const fetchKeys = async () => {
    setIsLoading(true);
    const response = await api.getApiKeys({ include_revoked: false });
    setKeys(response.keys);
    setIsLoading(false);
  };

  useEffect(() => {
    fetchKeys();
  }, []);

  const handleCreate = async () => {
    if (!keyName.trim()) {
      toast.error("Please enter a key name");
      return;
    }

    setIsCreating(true);

    const data: CreateApiKeyRequest = {
      name: keyName,
      key_type: keyType,
    };

    const result = await api.createApiKey(data);

    if (result) {
      setCreatedKey(result);
      setCreateDialogOpen(false);
      setNewKeyDialogOpen(true);
      setKeyName("");
      setKeyType("test");
      fetchKeys();
    } else {
      toast.error("Failed to create API key");
    }

    setIsCreating(false);
  };

  const handleRevoke = async (key: ApiKey) => {
    if (!confirm(`Are you sure you want to revoke "${key.name}"? This cannot be undone.`)) {
      return;
    }

    const result = await api.revokeApiKey(key.id);
    if (result) {
      toast.success("API key revoked");
      fetchKeys();
    } else {
      toast.error("Failed to revoke API key");
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    toast.success("Copied to clipboard");
    setTimeout(() => setCopied(false), 2000);
  };

  const handleCloseCreate = () => {
    setCreateDialogOpen(false);
    setKeyName("");
    setKeyType("test");
  };

  const handleCloseNewKey = () => {
    setNewKeyDialogOpen(false);
    setCreatedKey(null);
    setCopied(false);
  };

  return (
    <>
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Key className="h-5 w-5" />
              API Keys
            </CardTitle>
            <CardDescription>
              Manage API keys for authenticating SDKs and applications.
            </CardDescription>
          </div>
          <Button size="sm" onClick={() => setCreateDialogOpen(true)}>
            <Plus className="mr-2 h-4 w-4" />
            Create Key
          </Button>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-3">
              {[...Array(3)].map((_, i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : keys.length === 0 ? (
            <div className="text-center py-12">
              <Key className="mx-auto h-12 w-12 text-muted-foreground" />
              <h3 className="mt-4 text-lg font-medium">No API keys</h3>
              <p className="mt-2 text-sm text-muted-foreground">
                Create your first API key to authenticate your applications.
              </p>
              <Button className="mt-4" onClick={() => setCreateDialogOpen(true)}>
                <Plus className="mr-2 h-4 w-4" />
                Create API Key
              </Button>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Key</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Last Used</TableHead>
                  <TableHead className="w-[70px]"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {keys.map((key) => {
                  const config = keyTypeConfig[key.key_type as KeyType];

                  return (
                    <TableRow key={key.id}>
                      <TableCell className="font-medium">{key.name}</TableCell>
                      <TableCell>
                        <code className="text-sm text-muted-foreground">
                          {key.key_prefix}...
                        </code>
                      </TableCell>
                      <TableCell>
                        <Badge variant={config?.variant || "secondary"}>
                          {config?.label || key.key_type}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {key.last_used_at
                          ? formatDistanceToNow(new Date(key.last_used_at), {
                              addSuffix: true,
                            })
                          : "Never"}
                      </TableCell>
                      <TableCell>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8 text-destructive hover:text-destructive"
                          onClick={() => handleRevoke(key)}
                        >
                          <Trash2 className="h-4 w-4" />
                          <span className="sr-only">Revoke</span>
                        </Button>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Create Key Dialog */}
      <Dialog open={createDialogOpen} onOpenChange={handleCloseCreate}>
        <DialogContent className="sm:max-w-[480px] gap-0 p-0 overflow-hidden">
          <DialogHeader className="p-6 pb-4">
            <DialogTitle className="flex items-center gap-2 text-xl">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10">
                <Key className="h-5 w-5 text-primary" />
              </div>
              Create API Key
            </DialogTitle>
            <DialogDescription className="text-base">
              Generate a new key to authenticate your applications with FlowForge.
            </DialogDescription>
          </DialogHeader>

          <div className="px-6 pb-6 space-y-6">
            {/* Key Name Input */}
            <div className="space-y-2">
              <Label htmlFor="key-name" className="text-sm font-medium">
                Key Name
              </Label>
              <Input
                id="key-name"
                value={keyName}
                onChange={(e) => setKeyName(e.target.value)}
                placeholder="e.g., Production Backend, CI/CD Pipeline"
                className="h-11"
              />
              <p className="text-xs text-muted-foreground">
                A descriptive name to identify this key
              </p>
            </div>

            {/* Key Type Selection */}
            <div className="space-y-3">
              <Label className="text-sm font-medium">Key Type</Label>
              <div className="grid gap-3">
                {(Object.entries(keyTypeConfig) as [KeyType, typeof keyTypeConfig.live][]).map(
                  ([type, config]) => {
                    const Icon = config.icon;
                    const isSelected = keyType === type;

                    return (
                      <button
                        key={type}
                        type="button"
                        onClick={() => setKeyType(type)}
                        className={cn(
                          "flex items-start gap-4 rounded-lg border-2 p-4 text-left transition-all",
                          "hover:bg-muted/50",
                          isSelected
                            ? `${config.borderColor} ${config.bgColor}`
                            : "border-border"
                        )}
                      >
                        <div
                          className={cn(
                            "flex h-10 w-10 shrink-0 items-center justify-center rounded-lg",
                            config.bgColor
                          )}
                        >
                          <Icon className={cn("h-5 w-5", config.color)} />
                        </div>
                        <div className="flex-1 space-y-1">
                          <div className="flex items-center gap-2">
                            <span className="font-semibold">{config.label}</span>
                            {isSelected && (
                              <CheckCircle2 className={cn("h-4 w-4", config.color)} />
                            )}
                          </div>
                          <p className="text-sm text-muted-foreground">
                            {config.description}
                          </p>
                        </div>
                      </button>
                    );
                  }
                )}
              </div>
            </div>
          </div>

          <DialogFooter className="border-t bg-muted/30 px-6 py-4">
            <Button variant="outline" onClick={handleCloseCreate}>
              Cancel
            </Button>
            <Button onClick={handleCreate} disabled={isCreating || !keyName.trim()}>
              {isCreating ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Creating...
                </>
              ) : (
                <>
                  <Key className="mr-2 h-4 w-4" />
                  Create Key
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* New Key Created Dialog */}
      <Dialog open={newKeyDialogOpen} onOpenChange={handleCloseNewKey}>
        <DialogContent className="sm:max-w-[520px] gap-0 p-0 overflow-hidden">
          <div className="bg-emerald-500/10 px-6 py-8 text-center">
            <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-emerald-500/20">
              <ShieldCheck className="h-8 w-8 text-emerald-500" />
            </div>
            <h2 className="mt-4 text-xl font-semibold">API Key Created</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Your new API key has been generated successfully
            </p>
          </div>

          <div className="p-6 space-y-4">
            {/* Warning Banner */}
            <div className="flex items-start gap-3 rounded-lg border border-amber-500/30 bg-amber-500/10 p-4">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-amber-500/20">
                <Key className="h-4 w-4 text-amber-500" />
              </div>
              <div>
                <p className="font-medium text-amber-600 dark:text-amber-400">
                  Copy your key now
                </p>
                <p className="mt-1 text-sm text-muted-foreground">
                  This key will only be shown once. Store it in a secure location like a
                  password manager or environment variable.
                </p>
              </div>
            </div>

            {/* API Key Display */}
            <div className="space-y-2">
              <Label className="text-sm font-medium">Your API Key</Label>
              <div className="relative">
                <Input
                  value={createdKey?.key || ""}
                  readOnly
                  className="h-12 pr-24 font-mono text-sm bg-muted"
                />
                <Button
                  variant={copied ? "default" : "secondary"}
                  size="sm"
                  className={cn(
                    "absolute right-1.5 top-1.5 h-9",
                    copied && "bg-emerald-500 hover:bg-emerald-600"
                  )}
                  onClick={() => copyToClipboard(createdKey?.key || "")}
                >
                  {copied ? (
                    <>
                      <CheckCircle2 className="mr-2 h-4 w-4" />
                      Copied
                    </>
                  ) : (
                    <>
                      <Copy className="mr-2 h-4 w-4" />
                      Copy
                    </>
                  )}
                </Button>
              </div>
            </div>

            {/* Key Details */}
            {createdKey && (
              <div className="flex items-center gap-4 rounded-lg bg-muted/50 p-3">
                <div className="flex-1">
                  <p className="text-sm font-medium">{createdKey.name}</p>
                  <p className="text-xs text-muted-foreground">
                    {keyTypeConfig[createdKey.key_type as KeyType]?.label || createdKey.key_type} Key
                  </p>
                </div>
                <Badge variant={keyTypeConfig[createdKey.key_type as KeyType]?.variant || "secondary"}>
                  {keyTypeConfig[createdKey.key_type as KeyType]?.label || createdKey.key_type}
                </Badge>
              </div>
            )}
          </div>

          <DialogFooter className="border-t bg-muted/30 px-6 py-4">
            <Button onClick={handleCloseNewKey} className="w-full sm:w-auto">
              Done
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

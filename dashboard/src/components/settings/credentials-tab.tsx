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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { KeyRound, Plus, Trash2, Loader2 } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import {
  api,
  type Credential,
  type CreateCredentialRequest,
} from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";
import { toast } from "sonner";

const credentialTypeLabels: Record<string, string> = {
  api_key: "API Key",
  bearer_token: "Bearer Token",
  basic_auth: "Basic Auth",
  custom: "Custom",
};

export function CredentialsTab() {
  const { token } = useAuthStore();
  const [credentials, setCredentials] = useState<Credential[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [isCreating, setIsCreating] = useState(false);

  // Form state
  const [name, setName] = useState("");
  const [credType, setCredType] = useState("api_key");
  const [value, setValue] = useState("");
  const [description, setDescription] = useState("");

  useEffect(() => {
    api.setTokenProvider(() => token);
  }, [token]);

  const fetchCredentials = async () => {
    setIsLoading(true);
    const response = await api.getCredentials();
    setCredentials(response.credentials);
    setIsLoading(false);
  };

  useEffect(() => {
    fetchCredentials();
  }, []);

  const handleCreate = async () => {
    if (!name.trim()) {
      toast.error("Please enter a credential name");
      return;
    }
    if (!value.trim()) {
      toast.error("Please enter a value");
      return;
    }

    setIsCreating(true);

    const data: CreateCredentialRequest = {
      name: name.trim(),
      credential_type: credType,
      value,
      description: description.trim() || undefined,
    };

    const result = await api.createCredential(data);

    if (result) {
      toast.success("Credential created");
      handleCloseCreate();
      fetchCredentials();
    } else {
      toast.error("Failed to create credential");
    }

    setIsCreating(false);
  };

  const handleDelete = async (cred: Credential) => {
    if (
      !confirm(
        `Are you sure you want to delete "${cred.name}"? This cannot be undone.`
      )
    ) {
      return;
    }

    const result = await api.deleteCredential(cred.name);
    if (result) {
      toast.success("Credential deleted");
      fetchCredentials();
    } else {
      toast.error("Failed to delete credential");
    }
  };

  const handleCloseCreate = () => {
    setCreateDialogOpen(false);
    setName("");
    setCredType("api_key");
    setValue("");
    setDescription("");
  };

  return (
    <>
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <KeyRound className="h-5 w-5" />
              Credentials
            </CardTitle>
            <CardDescription>
              Store encrypted secrets for use in webhook tools via{" "}
              <code className="text-xs">{"{{credential:name}}"}</code>{" "}
              placeholders.
            </CardDescription>
          </div>
          <Button size="sm" onClick={() => setCreateDialogOpen(true)}>
            <Plus className="mr-2 h-4 w-4" />
            Add Credential
          </Button>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-3">
              {[...Array(3)].map((_, i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : credentials.length === 0 ? (
            <div className="text-center py-12">
              <KeyRound className="mx-auto h-12 w-12 text-muted-foreground" />
              <h3 className="mt-4 text-lg font-medium">No credentials</h3>
              <p className="mt-2 text-sm text-muted-foreground">
                Add a credential to securely store API keys and tokens for your
                webhook tools.
              </p>
              <Button
                className="mt-4"
                onClick={() => setCreateDialogOpen(true)}
              >
                <Plus className="mr-2 h-4 w-4" />
                Add Credential
              </Button>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Value</TableHead>
                  <TableHead>Description</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead className="w-[70px]"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {credentials.map((cred) => (
                  <TableRow key={cred.id}>
                    <TableCell className="font-medium font-mono text-sm">
                      {cred.name}
                    </TableCell>
                    <TableCell>
                      <Badge variant="secondary">
                        {credentialTypeLabels[cred.credential_type] ||
                          cred.credential_type}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <code className="text-sm text-muted-foreground">
                        {cred.value_prefix}
                      </code>
                    </TableCell>
                    <TableCell className="text-muted-foreground text-sm max-w-[200px] truncate">
                      {cred.description || "-"}
                    </TableCell>
                    <TableCell className="text-muted-foreground text-sm">
                      {formatDistanceToNow(new Date(cred.created_at), {
                        addSuffix: true,
                      })}
                    </TableCell>
                    <TableCell>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 text-destructive hover:text-destructive"
                        onClick={() => handleDelete(cred)}
                      >
                        <Trash2 className="h-4 w-4" />
                        <span className="sr-only">Delete</span>
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Create Credential Dialog */}
      <Dialog open={createDialogOpen} onOpenChange={handleCloseCreate}>
        <DialogContent className="sm:max-w-[480px]">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <KeyRound className="h-5 w-5" />
              Add Credential
            </DialogTitle>
            <DialogDescription>
              Store an encrypted secret. Reference it in webhook tool headers or
              URLs with <code>{"{{credential:name}}"}</code>.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label htmlFor="cred-name">Name</Label>
              <Input
                id="cred-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g., supabase_key"
              />
              <p className="text-xs text-muted-foreground">
                Used in placeholders:{" "}
                <code>{"{{credential:supabase_key}}"}</code>
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="cred-type">Type</Label>
              <Select value={credType} onValueChange={setCredType}>
                <SelectTrigger id="cred-type">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="api_key">API Key</SelectItem>
                  <SelectItem value="bearer_token">Bearer Token</SelectItem>
                  <SelectItem value="basic_auth">Basic Auth</SelectItem>
                  <SelectItem value="custom">Custom</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="cred-value">Value</Label>
              <Input
                id="cred-value"
                type="password"
                value={value}
                onChange={(e) => setValue(e.target.value)}
                placeholder="sk-proj-..."
              />
              <p className="text-xs text-muted-foreground">
                Encrypted at rest. Only the first 8 characters are stored for
                display.
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="cred-desc">Description (optional)</Label>
              <Input
                id="cred-desc"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="e.g., Supabase project API key"
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={handleCloseCreate}>
              Cancel
            </Button>
            <Button
              onClick={handleCreate}
              disabled={isCreating || !name.trim() || !value.trim()}
            >
              {isCreating ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Creating...
                </>
              ) : (
                "Add Credential"
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

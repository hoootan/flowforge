"use client";

import { useState, useEffect } from "react";
import { useTheme } from "next-themes";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Key,
  KeyRound,
  AlertCircle,
  Settings,
  Bot,
  Palette,
  Shield,
  Server,
  Sun,
  Moon,
  Monitor,
  Users,
  Plus,
  Lock,
  DollarSign,
  FileText,
  Bell,
  Gauge,
} from "lucide-react";
import { toast } from "sonner";
import { useAuthStore, usePermissions } from "@/stores/auth-store";
import { UsersList } from "@/components/settings/users-list";
import { UserDialog } from "@/components/settings/user-dialog";
import { ApiKeysTab } from "@/components/settings/api-keys-tab";
import { AIProvidersTab } from "@/components/settings/ai-providers-tab";
import { SecurityTab } from "@/components/settings/security-tab";
import { ModelPricingTab } from "@/components/settings/model-pricing-tab";
import { AuditLogTab } from "@/components/settings/audit-log-tab";
import { CredentialsTab } from "@/components/settings/credentials-tab";
import { NotificationsTab } from "@/components/settings/notifications-tab";
import { ConcurrencyTab } from "@/components/settings/concurrency-tab";
import type { User } from "@/lib/api";

interface SettingsData {
  endpoint: string;
  maxRetries: number;
  backoffMultiplier: number;
  maxBackoff: number;
}

const DEFAULT_SETTINGS: SettingsData = {
  endpoint: "http://localhost:8000",
  maxRetries: 3,
  backoffMultiplier: 2,
  maxBackoff: 300,
};

const STORAGE_KEY = "flowforge-settings";

export default function SettingsPage() {
  const { theme, setTheme } = useTheme();
  const { isAdmin } = usePermissions();
  const [settings, setSettings] = useState<SettingsData>(DEFAULT_SETTINGS);
  const [isSaving, setIsSaving] = useState(false);
  const [mounted, setMounted] = useState(false);

  // User management state
  const [userDialogOpen, setUserDialogOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [usersKey, setUsersKey] = useState(0);

  // Avoid hydration mismatch
  useEffect(() => {
    setMounted(true);
  }, []);

  // Load settings from localStorage on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        setSettings({ ...DEFAULT_SETTINGS, ...JSON.parse(stored) });
      }
    } catch (e) {
      console.error("Failed to load settings:", e);
    }
  }, []);

  const saveSettings = async (newSettings: Partial<SettingsData>) => {
    setIsSaving(true);
    const updated = { ...settings, ...newSettings };
    setSettings(updated);
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
      toast.success("Settings saved successfully");
    } catch (e) {
      console.error("Failed to save settings:", e);
      toast.error("Failed to save settings");
    } finally {
      setIsSaving(false);
    }
  };

  const handleSaveGeneral = () => {
    saveSettings({
      endpoint: settings.endpoint,
      maxRetries: settings.maxRetries,
      backoffMultiplier: settings.backoffMultiplier,
      maxBackoff: settings.maxBackoff,
    });
  };

  const handleEditUser = (user: User) => {
    setEditingUser(user);
    setUserDialogOpen(true);
  };

  const handleCreateUser = () => {
    setEditingUser(null);
    setUserDialogOpen(true);
  };

  const handleUserDialogSuccess = () => {
    setUsersKey((k) => k + 1);
  };

  // Determine which tabs to show
  const showUsersTab = isAdmin;
  const showAuditTab = isAdmin;

  return (
    <div className="flex h-full flex-col space-y-6 animate-fade-in">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Settings</h1>
        <p className="text-muted-foreground">
          Manage your FlowForge configuration, API keys, and preferences.
        </p>
      </div>

      {/* Tabbed Settings Interface */}
      <Tabs defaultValue="general" className="flex-1">
        <TabsList className={`grid w-full max-w-7xl ${showUsersTab ? "grid-cols-11" : "grid-cols-9"}`}>
          <TabsTrigger value="general" className="gap-1.5">
            <Settings className="h-4 w-4" />
            <span className="hidden sm:inline">General</span>
          </TabsTrigger>
          <TabsTrigger value="security" className="gap-1.5">
            <Lock className="h-4 w-4" />
            <span className="hidden sm:inline">Security</span>
          </TabsTrigger>
          {showUsersTab && (
            <TabsTrigger value="users" className="gap-1.5">
              <Users className="h-4 w-4" />
              <span className="hidden sm:inline">Users</span>
            </TabsTrigger>
          )}
          <TabsTrigger value="api-keys" className="gap-1.5">
            <Key className="h-4 w-4" />
            <span className="hidden sm:inline">API Keys</span>
          </TabsTrigger>
          <TabsTrigger value="credentials" className="gap-1.5">
            <KeyRound className="h-4 w-4" />
            <span className="hidden sm:inline">Credentials</span>
          </TabsTrigger>
          <TabsTrigger value="ai-config" className="gap-1.5">
            <Bot className="h-4 w-4" />
            <span className="hidden sm:inline">Providers</span>
          </TabsTrigger>
          <TabsTrigger value="pricing" className="gap-1.5">
            <DollarSign className="h-4 w-4" />
            <span className="hidden sm:inline">Pricing</span>
          </TabsTrigger>
          {showAuditTab && (
            <TabsTrigger value="audit" className="gap-1.5">
              <FileText className="h-4 w-4" />
              <span className="hidden sm:inline">Audit</span>
            </TabsTrigger>
          )}
          <TabsTrigger value="concurrency" className="gap-1.5">
            <Gauge className="h-4 w-4" />
            <span className="hidden sm:inline">Concurrency</span>
          </TabsTrigger>
          <TabsTrigger value="notifications" className="gap-1.5">
            <Bell className="h-4 w-4" />
            <span className="hidden sm:inline">Notifications</span>
          </TabsTrigger>
          <TabsTrigger value="appearance" className="gap-1.5">
            <Palette className="h-4 w-4" />
            <span className="hidden sm:inline">Theme</span>
          </TabsTrigger>
        </TabsList>

        {/* Security Tab */}
        <TabsContent value="security" className="mt-6 space-y-6">
          <SecurityTab />
        </TabsContent>

        {/* General Tab */}
        <TabsContent value="general" className="mt-6 space-y-6">
          <Alert>
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              Settings are saved to your browser&apos;s local storage. Changes are applied immediately.
            </AlertDescription>
          </Alert>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Server className="h-5 w-5" />
                Server Configuration
              </CardTitle>
              <CardDescription>
                Basic configuration for your FlowForge instance.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="app-id">App ID</Label>
                  <Input id="app-id" placeholder="my-app" disabled />
                  <p className="text-xs text-muted-foreground">
                    Your unique application identifier
                  </p>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="endpoint">Server Endpoint</Label>
                  <Input
                    id="endpoint"
                    value={settings.endpoint}
                    onChange={(e) => setSettings({ ...settings, endpoint: e.target.value })}
                  />
                  <p className="text-xs text-muted-foreground">
                    FlowForge server URL
                  </p>
                </div>
              </div>

              <Separator />

              <div className="space-y-4">
                <div>
                  <h4 className="font-medium">Default Retry Policy</h4>
                  <p className="text-sm text-muted-foreground">
                    Default retry settings for all functions
                  </p>
                </div>
                <div className="grid gap-4 md:grid-cols-3">
                  <div className="space-y-2">
                    <Label htmlFor="max-retries">Max Retries</Label>
                    <Input
                      id="max-retries"
                      type="number"
                      value={settings.maxRetries}
                      onChange={(e) => setSettings({ ...settings, maxRetries: parseInt(e.target.value) || 0 })}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="backoff">Backoff Multiplier</Label>
                    <Input
                      id="backoff"
                      type="number"
                      value={settings.backoffMultiplier}
                      onChange={(e) => setSettings({ ...settings, backoffMultiplier: parseInt(e.target.value) || 0 })}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="max-backoff">Max Backoff (seconds)</Label>
                    <Input
                      id="max-backoff"
                      type="number"
                      value={settings.maxBackoff}
                      onChange={(e) => setSettings({ ...settings, maxBackoff: parseInt(e.target.value) || 0 })}
                    />
                  </div>
                </div>
              </div>

              <div className="flex justify-end">
                <Button onClick={handleSaveGeneral} disabled={isSaving}>
                  {isSaving ? "Saving..." : "Save Changes"}
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Danger Zone */}
          <Card className="border-destructive/50">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-destructive">
                <Shield className="h-5 w-5" />
                Danger Zone
              </CardTitle>
              <CardDescription>
                Irreversible actions. Proceed with caution.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between rounded-lg border border-destructive/50 p-4">
                <div>
                  <h4 className="font-medium">Clear All Data</h4>
                  <p className="text-sm text-muted-foreground">
                    Delete all runs, events, and function data.
                  </p>
                </div>
                <Button variant="destructive">Clear Data</Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Users Tab (Admin only) */}
        {showUsersTab && (
          <TabsContent value="users" className="mt-6 space-y-6">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    <Users className="h-5 w-5" />
                    Team Members
                  </CardTitle>
                  <CardDescription>
                    Manage users who can access the FlowForge dashboard.
                  </CardDescription>
                </div>
                <Button size="sm" onClick={handleCreateUser}>
                  <Plus className="mr-2 h-4 w-4" />
                  Add User
                </Button>
              </CardHeader>
              <CardContent>
                <UsersList key={usersKey} onEditUser={handleEditUser} />
              </CardContent>
            </Card>

            <UserDialog
              open={userDialogOpen}
              onOpenChange={setUserDialogOpen}
              user={editingUser}
              onSuccess={handleUserDialogSuccess}
            />
          </TabsContent>
        )}

        {/* API Keys Tab */}
        <TabsContent value="api-keys" className="mt-6 space-y-6">
          <ApiKeysTab />
        </TabsContent>

        {/* Credentials Tab */}
        <TabsContent value="credentials" className="mt-6 space-y-6">
          <CredentialsTab />
        </TabsContent>

        {/* AI Providers Tab */}
        <TabsContent value="ai-config" className="mt-6 space-y-6">
          <AIProvidersTab />
        </TabsContent>

        {/* Model Pricing Tab */}
        <TabsContent value="pricing" className="mt-6 space-y-6">
          <ModelPricingTab />
        </TabsContent>

        {/* Audit Log Tab (Admin only) */}
        {showAuditTab && (
          <TabsContent value="audit" className="mt-6 space-y-6">
            <AuditLogTab />
          </TabsContent>
        )}

        {/* Concurrency & limits Tab */}
        <TabsContent value="concurrency" className="mt-6 space-y-6">
          <ConcurrencyTab />
        </TabsContent>

        {/* Notifications Tab */}
        <TabsContent value="notifications" className="mt-6 space-y-6">
          <NotificationsTab />
        </TabsContent>

        {/* Appearance Tab */}
        <TabsContent value="appearance" className="mt-6 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Palette className="h-5 w-5" />
                Theme
              </CardTitle>
              <CardDescription>
                Choose your preferred color theme for the dashboard.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {mounted && (
                <RadioGroup
                  value={theme}
                  onValueChange={setTheme}
                  className="grid gap-4 md:grid-cols-3"
                >
                  {/* Light Theme */}
                  <Label
                    htmlFor="light"
                    className="flex flex-col items-center justify-between rounded-lg border-2 border-muted bg-popover p-4 hover:bg-accent hover:text-accent-foreground cursor-pointer [&:has([data-state=checked])]:border-primary"
                  >
                    <RadioGroupItem value="light" id="light" className="sr-only" />
                    <div className="flex h-16 w-full items-center justify-center rounded-md bg-white border shadow-sm">
                      <Sun className="h-6 w-6 text-yellow-500" />
                    </div>
                    <span className="mt-3 font-medium">Light</span>
                    <span className="text-xs text-muted-foreground">
                      Clean, bright interface
                    </span>
                  </Label>

                  {/* Dark Theme */}
                  <Label
                    htmlFor="dark"
                    className="flex flex-col items-center justify-between rounded-lg border-2 border-muted bg-popover p-4 hover:bg-accent hover:text-accent-foreground cursor-pointer [&:has([data-state=checked])]:border-primary"
                  >
                    <RadioGroupItem value="dark" id="dark" className="sr-only" />
                    <div className="flex h-16 w-full items-center justify-center rounded-md bg-slate-900 border border-slate-700">
                      <Moon className="h-6 w-6 text-slate-400" />
                    </div>
                    <span className="mt-3 font-medium">Dark</span>
                    <span className="text-xs text-muted-foreground">
                      Easy on the eyes
                    </span>
                  </Label>

                  {/* System Theme */}
                  <Label
                    htmlFor="system"
                    className="flex flex-col items-center justify-between rounded-lg border-2 border-muted bg-popover p-4 hover:bg-accent hover:text-accent-foreground cursor-pointer [&:has([data-state=checked])]:border-primary"
                  >
                    <RadioGroupItem value="system" id="system" className="sr-only" />
                    <div className="flex h-16 w-full items-center justify-center rounded-md bg-gradient-to-r from-white to-slate-900 border">
                      <Monitor className="h-6 w-6 text-slate-600" />
                    </div>
                    <span className="mt-3 font-medium">System</span>
                    <span className="text-xs text-muted-foreground">
                      Match your OS preference
                    </span>
                  </Label>
                </RadioGroup>
              )}

              {/* Theme preview cards */}
              <div className="mt-8 space-y-4">
                <h4 className="font-medium">Preview</h4>
                <div className="grid gap-4 md:grid-cols-2">
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm">Sample Card</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <p className="text-sm text-muted-foreground">
                        This is how cards appear with your selected theme.
                      </p>
                      <div className="mt-4 flex gap-2">
                        <Button size="sm">Primary</Button>
                        <Button size="sm" variant="outline">Outline</Button>
                        <Button size="sm" variant="secondary">Secondary</Button>
                      </div>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm">Status Badges</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="flex flex-wrap gap-2">
                        <span className="inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold bg-emerald-500/10 text-emerald-600 border-emerald-500/20">
                          Success
                        </span>
                        <span className="inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold bg-amber-500/10 text-amber-600 border-amber-500/20">
                          Warning
                        </span>
                        <span className="inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold bg-red-500/10 text-red-600 border-red-500/20">
                          Error
                        </span>
                        <span className="inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold bg-blue-500/10 text-blue-600 border-blue-500/20">
                          Info
                        </span>
                      </div>
                    </CardContent>
                  </Card>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}

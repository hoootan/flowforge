"use client";

import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Shield, ShieldCheck, ShieldOff, Key, Loader2, AlertCircle, Copy, Check } from "lucide-react";
import { toast } from "sonner";
import { useAuthStore } from "@/stores/auth-store";

type SetupStep = "idle" | "scanning" | "verifying" | "complete";

export function SecurityTab() {
  const { user, setup2FA, confirm2FA, disable2FA, regenerateBackupCodes, refreshUser } = useAuthStore();

  // 2FA Setup state
  const [setupStep, setSetupStep] = useState<SetupStep>("idle");
  const [qrCode, setQrCode] = useState<string | null>(null);
  const [secret, setSecret] = useState<string | null>(null);
  const [verifyCode, setVerifyCode] = useState("");
  const [backupCodes, setBackupCodes] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Disable 2FA state
  const [showDisableDialog, setShowDisableDialog] = useState(false);
  const [disablePassword, setDisablePassword] = useState("");
  const [isDisabling, setIsDisabling] = useState(false);

  // Regenerate backup codes state
  const [showRegenerateDialog, setShowRegenerateDialog] = useState(false);
  const [regeneratePassword, setRegeneratePassword] = useState("");
  const [isRegenerating, setIsRegenerating] = useState(false);
  const [newBackupCodes, setNewBackupCodes] = useState<string[]>([]);

  const [copiedCode, setCopiedCode] = useState<string | null>(null);

  const is2FAEnabled = user?.totp_enabled ?? false;

  const handleStartSetup = async () => {
    setIsLoading(true);
    setError(null);

    const result = await setup2FA();

    if (result.success && result.qrCode && result.secret) {
      setQrCode(result.qrCode);
      setSecret(result.secret);
      setSetupStep("scanning");
    } else {
      setError(result.error || "Failed to start 2FA setup");
    }

    setIsLoading(false);
  };

  const handleVerifyCode = async () => {
    if (verifyCode.length < 6) return;

    setIsLoading(true);
    setError(null);

    const result = await confirm2FA(verifyCode);

    if (result.success && result.backupCodes) {
      setBackupCodes(result.backupCodes);
      setSetupStep("complete");
      await refreshUser();
      toast.success("Two-factor authentication enabled");
    } else {
      setError(result.error || "Invalid verification code");
    }

    setIsLoading(false);
  };

  const handleDisable2FA = async () => {
    if (!disablePassword) return;

    setIsDisabling(true);
    setError(null);

    const result = await disable2FA(disablePassword);

    if (result.success) {
      setShowDisableDialog(false);
      setDisablePassword("");
      await refreshUser();
      toast.success("Two-factor authentication disabled");
    } else {
      setError(result.error || "Failed to disable 2FA");
    }

    setIsDisabling(false);
  };

  const handleRegenerateBackupCodes = async () => {
    if (!regeneratePassword) return;

    setIsRegenerating(true);
    setError(null);

    const result = await regenerateBackupCodes(regeneratePassword);

    if (result.success && result.codes) {
      setNewBackupCodes(result.codes);
      setRegeneratePassword("");
      toast.success("Backup codes regenerated");
    } else {
      setError(result.error || "Failed to regenerate backup codes");
    }

    setIsRegenerating(false);
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedCode(text);
    setTimeout(() => setCopiedCode(null), 2000);
  };

  const copyAllCodes = (codes: string[]) => {
    navigator.clipboard.writeText(codes.join("\n"));
    toast.success("Backup codes copied to clipboard");
  };

  const resetSetup = () => {
    setSetupStep("idle");
    setQrCode(null);
    setSecret(null);
    setVerifyCode("");
    setBackupCodes([]);
    setError(null);
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5" />
            Two-Factor Authentication
          </CardTitle>
          <CardDescription>
            Add an extra layer of security to your account by requiring a verification code in addition to your password.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Status indicator */}
          <div className="flex items-center gap-4 rounded-lg border p-4">
            {is2FAEnabled ? (
              <>
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-emerald-100 dark:bg-emerald-900/30">
                  <ShieldCheck className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
                </div>
                <div className="flex-1">
                  <p className="font-medium">Two-factor authentication is enabled</p>
                  <p className="text-sm text-muted-foreground">
                    Your account is protected with an authenticator app.
                  </p>
                </div>
                <Button
                  variant="outline"
                  onClick={() => setShowDisableDialog(true)}
                >
                  <ShieldOff className="mr-2 h-4 w-4" />
                  Disable 2FA
                </Button>
              </>
            ) : (
              <>
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-amber-100 dark:bg-amber-900/30">
                  <Shield className="h-5 w-5 text-amber-600 dark:text-amber-400" />
                </div>
                <div className="flex-1">
                  <p className="font-medium">Two-factor authentication is not enabled</p>
                  <p className="text-sm text-muted-foreground">
                    Enable 2FA to add an extra layer of security to your account.
                  </p>
                </div>
                {setupStep === "idle" && (
                  <Button onClick={handleStartSetup} disabled={isLoading}>
                    {isLoading ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Setting up...
                      </>
                    ) : (
                      <>
                        <ShieldCheck className="mr-2 h-4 w-4" />
                        Enable 2FA
                      </>
                    )}
                  </Button>
                )}
              </>
            )}
          </div>

          {/* Setup flow */}
          {setupStep === "scanning" && (
            <div className="space-y-4 rounded-lg border p-4">
              <h3 className="font-medium">Step 1: Scan QR Code</h3>
              <p className="text-sm text-muted-foreground">
                Scan this QR code with your authenticator app (Google Authenticator, Authy, 1Password, etc.)
              </p>

              {qrCode && (
                <div className="flex justify-center">
                  <div className="rounded-lg bg-white p-4">
                    <img src={qrCode} alt="2FA QR Code" className="h-48 w-48" />
                  </div>
                </div>
              )}

              {secret && (
                <div className="space-y-2">
                  <Label>Or enter this code manually:</Label>
                  <div className="flex items-center gap-2">
                    <code className="flex-1 rounded bg-muted px-3 py-2 font-mono text-sm">
                      {secret}
                    </code>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => copyToClipboard(secret)}
                    >
                      {copiedCode === secret ? (
                        <Check className="h-4 w-4" />
                      ) : (
                        <Copy className="h-4 w-4" />
                      )}
                    </Button>
                  </div>
                </div>
              )}

              <div className="space-y-2 pt-4">
                <h3 className="font-medium">Step 2: Enter Verification Code</h3>
                <p className="text-sm text-muted-foreground">
                  Enter the 6-digit code from your authenticator app to verify the setup.
                </p>

                {error && (
                  <Alert variant="destructive">
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription>{error}</AlertDescription>
                  </Alert>
                )}

                <div className="flex items-center gap-2">
                  <Input
                    type="text"
                    inputMode="numeric"
                    pattern="[0-9]*"
                    maxLength={6}
                    placeholder="000000"
                    value={verifyCode}
                    onChange={(e) => setVerifyCode(e.target.value.replace(/\D/g, ""))}
                    className="w-32 text-center text-lg tracking-widest"
                    autoComplete="one-time-code"
                  />
                  <Button
                    onClick={handleVerifyCode}
                    disabled={isLoading || verifyCode.length < 6}
                  >
                    {isLoading ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      "Verify"
                    )}
                  </Button>
                  <Button variant="ghost" onClick={resetSetup}>
                    Cancel
                  </Button>
                </div>
              </div>
            </div>
          )}

          {/* Backup codes display after setup */}
          {setupStep === "complete" && backupCodes.length > 0 && (
            <div className="space-y-4 rounded-lg border border-amber-500/50 bg-amber-50 dark:bg-amber-900/10 p-4">
              <div className="flex items-start gap-2">
                <Key className="mt-0.5 h-5 w-5 text-amber-600" />
                <div>
                  <h3 className="font-medium">Save your backup codes</h3>
                  <p className="text-sm text-muted-foreground">
                    Store these codes in a safe place. You can use them to access your account if you lose your authenticator device.
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2">
                {backupCodes.map((code, index) => (
                  <div
                    key={index}
                    className="flex items-center justify-between rounded bg-white dark:bg-zinc-900 px-3 py-2 font-mono text-sm"
                  >
                    <span>{code}</span>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-6 w-6 p-0"
                      onClick={() => copyToClipboard(code)}
                    >
                      {copiedCode === code ? (
                        <Check className="h-3 w-3" />
                      ) : (
                        <Copy className="h-3 w-3" />
                      )}
                    </Button>
                  </div>
                ))}
              </div>

              <div className="flex gap-2">
                <Button variant="outline" onClick={() => copyAllCodes(backupCodes)}>
                  <Copy className="mr-2 h-4 w-4" />
                  Copy all codes
                </Button>
                <Button onClick={resetSetup}>Done</Button>
              </div>
            </div>
          )}

          {/* Backup codes management for users with 2FA enabled */}
          {is2FAEnabled && setupStep === "idle" && (
            <div className="rounded-lg border p-4">
              <div className="flex items-center gap-4">
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-muted">
                  <Key className="h-5 w-5 text-muted-foreground" />
                </div>
                <div className="flex-1">
                  <p className="font-medium">Backup codes</p>
                  <p className="text-sm text-muted-foreground">
                    Use these one-time codes if you lose access to your authenticator app.
                  </p>
                </div>
                <Button variant="outline" onClick={() => setShowRegenerateDialog(true)}>
                  Regenerate codes
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Disable 2FA Dialog */}
      <Dialog open={showDisableDialog} onOpenChange={setShowDisableDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Disable Two-Factor Authentication</DialogTitle>
            <DialogDescription>
              This will remove the extra layer of security from your account. Enter your password to confirm.
            </DialogDescription>
          </DialogHeader>

          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <div className="space-y-2">
            <Label htmlFor="disable-password">Password</Label>
            <Input
              id="disable-password"
              type="password"
              value={disablePassword}
              onChange={(e) => setDisablePassword(e.target.value)}
              placeholder="Enter your password"
            />
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDisableDialog(false)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDisable2FA}
              disabled={!disablePassword || isDisabling}
            >
              {isDisabling ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Disabling...
                </>
              ) : (
                "Disable 2FA"
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Regenerate Backup Codes Dialog */}
      <Dialog open={showRegenerateDialog} onOpenChange={setShowRegenerateDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Regenerate Backup Codes</DialogTitle>
            <DialogDescription>
              This will invalidate all existing backup codes and generate new ones. Enter your password to confirm.
            </DialogDescription>
          </DialogHeader>

          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {newBackupCodes.length === 0 ? (
            <>
              <div className="space-y-2">
                <Label htmlFor="regenerate-password">Password</Label>
                <Input
                  id="regenerate-password"
                  type="password"
                  value={regeneratePassword}
                  onChange={(e) => setRegeneratePassword(e.target.value)}
                  placeholder="Enter your password"
                />
              </div>

              <DialogFooter>
                <Button variant="outline" onClick={() => setShowRegenerateDialog(false)}>
                  Cancel
                </Button>
                <Button
                  onClick={handleRegenerateBackupCodes}
                  disabled={!regeneratePassword || isRegenerating}
                >
                  {isRegenerating ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Regenerating...
                    </>
                  ) : (
                    "Regenerate"
                  )}
                </Button>
              </DialogFooter>
            </>
          ) : (
            <div className="space-y-4">
              <Alert>
                <Key className="h-4 w-4" />
                <AlertDescription>
                  Save these codes in a safe place. Previous codes are no longer valid.
                </AlertDescription>
              </Alert>

              <div className="grid grid-cols-2 gap-2">
                {newBackupCodes.map((code, index) => (
                  <div
                    key={index}
                    className="flex items-center justify-between rounded bg-muted px-3 py-2 font-mono text-sm"
                  >
                    <span>{code}</span>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-6 w-6 p-0"
                      onClick={() => copyToClipboard(code)}
                    >
                      {copiedCode === code ? (
                        <Check className="h-3 w-3" />
                      ) : (
                        <Copy className="h-3 w-3" />
                      )}
                    </Button>
                  </div>
                ))}
              </div>

              <DialogFooter>
                <Button variant="outline" onClick={() => copyAllCodes(newBackupCodes)}>
                  <Copy className="mr-2 h-4 w-4" />
                  Copy all
                </Button>
                <Button onClick={() => {
                  setShowRegenerateDialog(false);
                  setNewBackupCodes([]);
                }}>
                  Done
                </Button>
              </DialogFooter>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

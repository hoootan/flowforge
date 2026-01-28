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
import {
  Loader2,
  UserPlus,
  UserCog,
  Shield,
  Users,
  Eye,
  CheckCircle2,
  Mail,
  Lock,
  User,
} from "lucide-react";
import { api, type User as UserType, type CreateUserRequest, type UpdateUserRequest } from "@/lib/api";
import type { UserRole } from "@/lib/auth/types";
import { useAuthStore } from "@/stores/auth-store";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

const roleConfig = {
  admin: {
    label: "Admin",
    description: "Full access to all features including user management",
    icon: Shield,
    color: "text-amber-500",
    bgColor: "bg-amber-500/10",
    borderColor: "border-amber-500/30",
  },
  member: {
    label: "Member",
    description: "Create and manage functions, tools, and events",
    icon: Users,
    color: "text-blue-500",
    bgColor: "bg-blue-500/10",
    borderColor: "border-blue-500/30",
  },
  viewer: {
    label: "Viewer",
    description: "Read-only access to view runs and configurations",
    icon: Eye,
    color: "text-slate-500",
    bgColor: "bg-slate-500/10",
    borderColor: "border-slate-500/30",
  },
};

interface UserDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  user?: UserType | null;
  onSuccess?: () => void;
}

export function UserDialog({ open, onOpenChange, user, onSuccess }: UserDialogProps) {
  const { token } = useAuthStore();
  const isEditing = !!user;

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<UserRole>("member");
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    api.setTokenProvider(() => token);
  }, [token]);

  useEffect(() => {
    if (open) {
      if (user) {
        setName(user.name);
        setEmail(user.email);
        setRole(user.role as UserRole);
        setPassword("");
      } else {
        setName("");
        setEmail("");
        setPassword("");
        setRole("member");
      }
    }
  }, [open, user]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);

    try {
      if (isEditing && user) {
        const updateData: UpdateUserRequest = {
          name,
          email,
          role,
        };

        const result = await api.updateUser(user.id, updateData);
        if (result) {
          toast.success("User updated successfully");
          onSuccess?.();
          onOpenChange(false);
        } else {
          toast.error("Failed to update user");
        }
      } else {
        const createData: CreateUserRequest = {
          name,
          email,
          password,
          role,
        };

        const result = await api.createUser(createData);
        if (result) {
          toast.success("User created successfully");
          onSuccess?.();
          onOpenChange(false);
        } else {
          toast.error("Failed to create user");
        }
      }
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "An error occurred");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    onOpenChange(false);
  };

  const HeaderIcon = isEditing ? UserCog : UserPlus;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px] gap-0 p-0 overflow-hidden">
        <DialogHeader className="p-6 pb-4">
          <DialogTitle className="flex items-center gap-3 text-xl">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10">
              <HeaderIcon className="h-5 w-5 text-primary" />
            </div>
            {isEditing ? "Edit User" : "Add New User"}
          </DialogTitle>
          <DialogDescription className="text-base">
            {isEditing
              ? "Update user details and permissions."
              : "Invite a new team member to your FlowForge workspace."}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit}>
          <div className="px-6 pb-6 space-y-5">
            {/* Name Input */}
            <div className="space-y-2">
              <Label htmlFor="name" className="text-sm font-medium">
                Full Name
              </Label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  id="name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="John Doe"
                  className="h-11 pl-10"
                  required
                />
              </div>
            </div>

            {/* Email Input */}
            <div className="space-y-2">
              <Label htmlFor="email" className="text-sm font-medium">
                Email Address
              </Label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="john@example.com"
                  className="h-11 pl-10"
                  required
                />
              </div>
            </div>

            {/* Password Input (only for new users) */}
            {!isEditing && (
              <div className="space-y-2">
                <Label htmlFor="password" className="text-sm font-medium">
                  Password
                </Label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    id="password"
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Minimum 8 characters"
                    className="h-11 pl-10"
                    minLength={8}
                    required
                  />
                </div>
                <p className="text-xs text-muted-foreground">
                  Must be at least 8 characters long
                </p>
              </div>
            )}

            {/* Role Selection */}
            <div className="space-y-3">
              <Label className="text-sm font-medium">Role</Label>
              <div className="grid gap-3">
                {(Object.entries(roleConfig) as [UserRole, typeof roleConfig.admin][]).map(
                  ([roleKey, config]) => {
                    const Icon = config.icon;
                    const isSelected = role === roleKey;

                    return (
                      <button
                        key={roleKey}
                        type="button"
                        onClick={() => setRole(roleKey)}
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
            <Button
              type="button"
              variant="outline"
              onClick={handleClose}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  {isEditing ? "Saving..." : "Creating..."}
                </>
              ) : (
                <>
                  {isEditing ? (
                    <>
                      <UserCog className="mr-2 h-4 w-4" />
                      Save Changes
                    </>
                  ) : (
                    <>
                      <UserPlus className="mr-2 h-4 w-4" />
                      Create User
                    </>
                  )}
                </>
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

"use client";

import { useState, useEffect } from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Skeleton } from "@/components/ui/skeleton";
import {
  MoreHorizontal,
  Shield,
  User as UserIcon,
  Eye,
  Pencil,
  Trash2,
  UserX,
} from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { api, type User } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";
import { toast } from "sonner";

interface UsersListProps {
  onEditUser: (user: User) => void;
}

const roleConfig = {
  admin: {
    label: "Admin",
    icon: Shield,
    variant: "default" as const,
  },
  member: {
    label: "Member",
    icon: UserIcon,
    variant: "secondary" as const,
  },
  viewer: {
    label: "Viewer",
    icon: Eye,
    variant: "outline" as const,
  },
};

export function UsersList({ onEditUser }: UsersListProps) {
  const { user: currentUser, token } = useAuthStore();
  const [users, setUsers] = useState<User[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Set token provider for API client
  useEffect(() => {
    api.setTokenProvider(() => token);
  }, [token]);

  const fetchUsers = async () => {
    setIsLoading(true);
    const response = await api.getUsers({ include_inactive: true });
    setUsers(response.users);
    setIsLoading(false);
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  const handleDeactivate = async (user: User) => {
    const result = await api.updateUser(user.id, { is_active: false });
    if (result) {
      toast.success(`User ${user.name} has been deactivated`);
      fetchUsers();
    } else {
      toast.error("Failed to deactivate user");
    }
  };

  const handleActivate = async (user: User) => {
    const result = await api.updateUser(user.id, { is_active: true });
    if (result) {
      toast.success(`User ${user.name} has been activated`);
      fetchUsers();
    } else {
      toast.error("Failed to activate user");
    }
  };

  const handleDelete = async (user: User) => {
    if (!confirm(`Are you sure you want to delete ${user.name}? This cannot be undone.`)) {
      return;
    }

    const result = await api.deleteUser(user.id);
    if (result) {
      toast.success(`User ${user.name} has been deleted`);
      fetchUsers();
    } else {
      toast.error("Failed to delete user");
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-3">
        {[...Array(3)].map((_, i) => (
          <Skeleton key={i} className="h-16 w-full" />
        ))}
      </div>
    );
  }

  if (users.length === 0) {
    return (
      <div className="text-center py-12">
        <UserIcon className="mx-auto h-12 w-12 text-muted-foreground" />
        <h3 className="mt-4 text-lg font-medium">No users yet</h3>
        <p className="mt-2 text-sm text-muted-foreground">
          Create your first user to get started.
        </p>
      </div>
    );
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>User</TableHead>
          <TableHead>Role</TableHead>
          <TableHead>Status</TableHead>
          <TableHead>Last Login</TableHead>
          <TableHead className="w-[70px]"></TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {users.map((user) => {
          const role = roleConfig[user.role as keyof typeof roleConfig];
          const RoleIcon = role?.icon || UserIcon;
          const isCurrentUser = user.id === currentUser?.id;

          return (
            <TableRow key={user.id}>
              <TableCell>
                <div className="flex items-center gap-3">
                  <div className="flex h-9 w-9 items-center justify-center rounded-full bg-muted text-sm font-medium">
                    {user.name
                      .split(" ")
                      .map((n) => n[0])
                      .join("")
                      .toUpperCase()
                      .slice(0, 2)}
                  </div>
                  <div>
                    <div className="font-medium">
                      {user.name}
                      {isCurrentUser && (
                        <span className="ml-2 text-xs text-muted-foreground">(You)</span>
                      )}
                    </div>
                    <div className="text-sm text-muted-foreground">{user.email}</div>
                  </div>
                </div>
              </TableCell>
              <TableCell>
                <Badge variant={role?.variant || "secondary"} className="gap-1">
                  <RoleIcon className="h-3 w-3" />
                  {role?.label || user.role}
                </Badge>
              </TableCell>
              <TableCell>
                {user.is_active ? (
                  <Badge variant="outline" className="text-emerald-600 border-emerald-600/20 bg-emerald-500/10">
                    Active
                  </Badge>
                ) : (
                  <Badge variant="outline" className="text-red-600 border-red-600/20 bg-red-500/10">
                    Inactive
                  </Badge>
                )}
              </TableCell>
              <TableCell className="text-muted-foreground">
                {user.last_login_at
                  ? formatDistanceToNow(new Date(user.last_login_at), { addSuffix: true })
                  : "Never"}
              </TableCell>
              <TableCell>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="ghost" size="icon" className="h-8 w-8">
                      <MoreHorizontal className="h-4 w-4" />
                      <span className="sr-only">Open menu</span>
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem onClick={() => onEditUser(user)}>
                      <Pencil className="mr-2 h-4 w-4" />
                      Edit
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                    {user.is_active ? (
                      <DropdownMenuItem
                        onClick={() => handleDeactivate(user)}
                        disabled={isCurrentUser}
                      >
                        <UserX className="mr-2 h-4 w-4" />
                        Deactivate
                      </DropdownMenuItem>
                    ) : (
                      <DropdownMenuItem onClick={() => handleActivate(user)}>
                        <UserIcon className="mr-2 h-4 w-4" />
                        Activate
                      </DropdownMenuItem>
                    )}
                    <DropdownMenuItem
                      onClick={() => handleDelete(user)}
                      disabled={isCurrentUser}
                      className="text-destructive focus:text-destructive"
                    >
                      <Trash2 className="mr-2 h-4 w-4" />
                      Delete
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </TableCell>
            </TableRow>
          );
        })}
      </TableBody>
    </Table>
  );
}

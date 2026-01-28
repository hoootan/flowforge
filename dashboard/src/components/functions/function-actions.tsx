"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/forms/confirm-dialog";
import { MoreHorizontal, Pencil, Power, Trash2 } from "lucide-react";
import { Function, api } from "@/lib/api";

interface FunctionActionsProps {
  func: Function;
  onRefresh: () => void;
  onError: (message: string) => void;
  onSuccess: (message: string) => void;
}

export function FunctionActions({
  func,
  onRefresh,
  onError,
  onSuccess,
}: FunctionActionsProps) {
  const router = useRouter();
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [toggleLoading, setToggleLoading] = useState(false);

  const handleToggleActive = async () => {
    setToggleLoading(true);
    const result = await api.updateFunction(func.function_id, {
      is_active: !func.is_active,
    });
    setToggleLoading(false);

    if (result) {
      onSuccess(`Function ${func.is_active ? "deactivated" : "activated"}`);
      onRefresh();
    } else {
      onError("Failed to update function status");
    }
  };

  const handleDelete = async () => {
    setDeleteLoading(true);
    const success = await api.deleteFunction(func.function_id);
    setDeleteLoading(false);

    if (success) {
      onSuccess("Function deleted successfully");
      setDeleteOpen(false);
      onRefresh();
    } else {
      onError("Failed to delete function");
    }
  };

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" size="icon" className="h-8 w-8">
            <MoreHorizontal className="h-4 w-4" />
            <span className="sr-only">Open menu</span>
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuItem onClick={() => router.push(`/functions/new?edit=${encodeURIComponent(func.function_id)}`)}>
            <Pencil className="mr-2 h-4 w-4" />
            Edit
          </DropdownMenuItem>
          <DropdownMenuItem
            onClick={handleToggleActive}
            disabled={toggleLoading}
          >
            <Power className="mr-2 h-4 w-4" />
            {func.is_active ? "Deactivate" : "Activate"}
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem
            onClick={() => setDeleteOpen(true)}
            className="text-red-600 focus:text-red-600"
          >
            <Trash2 className="mr-2 h-4 w-4" />
            Delete
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <ConfirmDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        title="Delete Function"
        description={`Are you sure you want to delete "${func.name}"? This action cannot be undone. Any scheduled runs will be cancelled.`}
        confirmText="Delete"
        variant="destructive"
        onConfirm={handleDelete}
        loading={deleteLoading}
      />
    </>
  );
}

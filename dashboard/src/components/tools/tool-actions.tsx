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
import { Tool, api } from "@/lib/api";

interface ToolActionsProps {
  tool: Tool;
  onRefresh: () => void;
  onError: (message: string) => void;
  onSuccess: (message: string) => void;
}

export function ToolActions({
  tool,
  onRefresh,
  onError,
  onSuccess,
}: ToolActionsProps) {
  const router = useRouter();
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [toggleLoading, setToggleLoading] = useState(false);

  const isBuiltIn = tool.is_builtin;

  const handleToggleActive = async () => {
    setToggleLoading(true);
    const result = await api.updateTool(tool.name, {
      is_active: !tool.is_active,
    });
    setToggleLoading(false);

    if (result) {
      onSuccess(`Tool ${tool.is_active ? "deactivated" : "activated"}`);
      onRefresh();
    } else {
      onError("Failed to update tool status");
    }
  };

  const handleDelete = async () => {
    setDeleteLoading(true);
    const success = await api.deleteTool(tool.name);
    setDeleteLoading(false);

    if (success) {
      onSuccess("Tool deleted successfully");
      setDeleteOpen(false);
      onRefresh();
    } else {
      onError("Failed to delete tool");
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
          <DropdownMenuItem
            onClick={() => router.push(`/tools/new?edit=${encodeURIComponent(tool.name)}`)}
            disabled={isBuiltIn}
          >
            <Pencil className="mr-2 h-4 w-4" />
            Edit
          </DropdownMenuItem>
          <DropdownMenuItem
            onClick={handleToggleActive}
            disabled={isBuiltIn || toggleLoading}
          >
            <Power className="mr-2 h-4 w-4" />
            {tool.is_active ? "Deactivate" : "Activate"}
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem
            onClick={() => setDeleteOpen(true)}
            disabled={isBuiltIn}
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
        title="Delete Tool"
        description={`Are you sure you want to delete "${tool.name}"? This action cannot be undone.`}
        confirmText="Delete"
        variant="destructive"
        onConfirm={handleDelete}
        loading={deleteLoading}
      />
    </>
  );
}

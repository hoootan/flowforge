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
import { Textarea } from "@/components/ui/textarea";
import { ConfirmDialog } from "@/components/forms/confirm-dialog";
import { MoreHorizontal, Pencil, Power, Trash2, Sparkles } from "lucide-react";
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
  const [skillOpen, setSkillOpen] = useState(false);
  const [skillLoading, setSkillLoading] = useState(false);
  const [skillForm, setSkillForm] = useState({
    name: "",
    description: "",
    category: "",
    tags: "",
  });

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

  const handleOpenSkillDialog = () => {
    setSkillForm({
      name: func.name,
      description: `Skill template created from "${func.name}" function`,
      category: "",
      tags: func.trigger_type,
    });
    setSkillOpen(true);
  };

  const handleSaveAsSkill = async () => {
    if (!skillForm.name.trim()) return;
    setSkillLoading(true);

    const functionConfig: Record<string, unknown> = {
      trigger_type: func.trigger_type,
      trigger_value: func.trigger_value,
      is_inline: func.is_inline,
      system_prompt: func.system_prompt,
      agent_config: func.agent_config,
      config: func.config,
    };

    const toolsConfig: Record<string, unknown>[] = (func.tools_config || []).map(
      (toolName) => ({ name: toolName })
    );

    const result = await api.createSkill({
      name: skillForm.name,
      description: skillForm.description || undefined,
      category: skillForm.category || undefined,
      function_config: functionConfig,
      tools_config: toolsConfig,
      tags: skillForm.tags
        ? skillForm.tags.split(",").map((t) => t.trim()).filter(Boolean)
        : undefined,
    });

    setSkillLoading(false);

    if (result) {
      onSuccess(`Saved as skill "${result.name}"`);
      setSkillOpen(false);
    } else {
      onError("Failed to save as skill");
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
          <DropdownMenuItem onClick={handleOpenSkillDialog}>
            <Sparkles className="mr-2 h-4 w-4" />
            Save as Skill
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

      {/* Save as Skill Dialog */}
      <Dialog open={skillOpen} onOpenChange={setSkillOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Save as Skill Template</DialogTitle>
            <DialogDescription>
              Save this function&apos;s configuration as a reusable skill
              that can be shared across your workspace.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="skill-name">Skill Name</Label>
              <Input
                id="skill-name"
                value={skillForm.name}
                onChange={(e) =>
                  setSkillForm({ ...skillForm, name: e.target.value })
                }
                placeholder="e.g., Code Review"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="skill-desc">Description</Label>
              <Textarea
                id="skill-desc"
                value={skillForm.description}
                onChange={(e) =>
                  setSkillForm({ ...skillForm, description: e.target.value })
                }
                placeholder="What does this skill do?"
                rows={3}
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="skill-category">Category</Label>
                <Input
                  id="skill-category"
                  value={skillForm.category}
                  onChange={(e) =>
                    setSkillForm({ ...skillForm, category: e.target.value })
                  }
                  placeholder="e.g., development"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="skill-tags">Tags (comma-separated)</Label>
                <Input
                  id="skill-tags"
                  value={skillForm.tags}
                  onChange={(e) =>
                    setSkillForm({ ...skillForm, tags: e.target.value })
                  }
                  placeholder="e.g., review, github"
                />
              </div>
            </div>
            <div className="rounded-lg bg-muted p-3 text-xs text-muted-foreground space-y-1">
              <p className="font-medium text-foreground">Captured configuration:</p>
              <p>Trigger: {func.trigger_type} / {func.trigger_value}</p>
              {func.system_prompt && <p>System prompt: {func.system_prompt.slice(0, 60)}...</p>}
              {func.tools_config && func.tools_config.length > 0 && (
                <p>Tools: {func.tools_config.join(", ")}</p>
              )}
              {func.agent_config && <p>Agent config included</p>}
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setSkillOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleSaveAsSkill} disabled={skillLoading || !skillForm.name.trim()}>
              {skillLoading ? "Saving..." : "Save Skill"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

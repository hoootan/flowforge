"use client";

import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { ScrollArea } from "@/components/ui/scroll-area";
import { ToolForm, ToolFormData } from "./tool-form";
import { api } from "@/lib/api";

interface CreateToolSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
  onError: (message: string) => void;
}

export function CreateToolSheet({
  open,
  onOpenChange,
  onSuccess,
  onError,
}: CreateToolSheetProps) {
  const handleSubmit = async (data: ToolFormData) => {
    const result = await api.createTool({
      name: data.name,
      description: data.description,
      parameters: data.parameters,
      code: data.code || undefined,
      requires_approval: data.requires_approval,
      approval_timeout: data.requires_approval ? data.approval_timeout : undefined,
    });

    if (result) {
      onSuccess();
      onOpenChange(false);
    } else {
      onError("Failed to create tool. Please try again.");
    }
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="sm:max-w-xl">
        <SheetHeader>
          <SheetTitle>Create Tool</SheetTitle>
          <SheetDescription>
            Define a new custom tool for agent functions.
          </SheetDescription>
        </SheetHeader>
        <ScrollArea className="h-[calc(100vh-8rem)] pr-4">
          <div className="py-6">
            <ToolForm
              onSubmit={handleSubmit}
              onCancel={() => onOpenChange(false)}
            />
          </div>
        </ScrollArea>
      </SheetContent>
    </Sheet>
  );
}

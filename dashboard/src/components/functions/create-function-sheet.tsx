"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { ScrollArea } from "@/components/ui/scroll-area";
import { FunctionForm, FunctionFormData } from "./function-form";
import { api, Tool } from "@/lib/api";

interface CreateFunctionSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
  onError: (message: string) => void;
}

export function CreateFunctionSheet({
  open,
  onOpenChange,
  onSuccess,
  onError,
}: CreateFunctionSheetProps) {
  const [tools, setTools] = useState<Tool[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchTools = useCallback(async () => {
    const response = await api.getTools();
    setTools(response.tools);
  }, []);

  useEffect(() => {
    if (open) {
      fetchTools();
    }
  }, [open, fetchTools]);

  const handleSubmit = async (data: FunctionFormData) => {
    setLoading(true);

    let result;
    if (data.mode === "inline") {
      result = await api.createInlineFunction({
        id: data.id,
        name: data.name,
        trigger: {
          type: data.trigger_type,
          value: data.trigger_value,
        },
        system_prompt: data.system_prompt,
        tools: data.tools,
        agent_config: data.agent_config,
      });
    } else {
      result = await api.createWorkerFunction({
        id: data.id,
        name: data.name,
        trigger: {
          type: data.trigger_type,
          value: data.trigger_value,
        },
        endpoint_url: data.endpoint_url,
        config: data.config,
      });
    }

    setLoading(false);

    if (result) {
      onSuccess();
      onOpenChange(false);
    } else {
      onError("Failed to create function. Please try again.");
    }
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="sm:max-w-2xl">
        <SheetHeader>
          <SheetTitle>Create Function</SheetTitle>
          <SheetDescription>
            Define a new workflow function.
          </SheetDescription>
        </SheetHeader>
        <ScrollArea className="h-[calc(100vh-8rem)] pr-4">
          <div className="py-6">
            <FunctionForm
              availableTools={tools}
              onSubmit={handleSubmit}
              onCancel={() => onOpenChange(false)}
              loading={loading}
            />
          </div>
        </ScrollArea>
      </SheetContent>
    </Sheet>
  );
}

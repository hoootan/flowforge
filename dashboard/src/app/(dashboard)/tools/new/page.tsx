"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { ToolWizard } from "@/components/tools/tool-wizard";
import { api, Tool } from "@/lib/api";
import { Loader2 } from "lucide-react";

export default function NewToolPage() {
  const searchParams = useSearchParams();
  const editName = searchParams.get("edit");

  const [initialData, setInitialData] = useState<Tool | null>(null);
  const [loading, setLoading] = useState(!!editName);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (editName) {
      const fetchTool = async () => {
        setLoading(true);
        const tool = await api.getTool(editName);
        if (tool) {
          setInitialData(tool);
        } else {
          setError("Tool not found");
        }
        setLoading(false);
      };
      fetchTool();
    }
  }, [editName]);

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-center">
          <p className="text-muted-foreground">{error}</p>
        </div>
      </div>
    );
  }

  return <ToolWizard initialData={initialData} />;
}

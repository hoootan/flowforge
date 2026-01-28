"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { FunctionWizard } from "@/components/functions/function-wizard";
import { api, Function } from "@/lib/api";
import { Loader2 } from "lucide-react";

export default function NewFunctionPage() {
  const searchParams = useSearchParams();
  const editId = searchParams.get("edit");

  const [initialData, setInitialData] = useState<Function | null>(null);
  const [loading, setLoading] = useState(!!editId);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (editId) {
      const fetchFunction = async () => {
        setLoading(true);
        const func = await api.getFunction(editId);
        if (func) {
          setInitialData(func);
        } else {
          setError("Function not found");
        }
        setLoading(false);
      };
      fetchFunction();
    }
  }, [editId]);

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

  return <FunctionWizard initialData={initialData} />;
}

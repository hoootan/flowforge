"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { AlertTriangle, X } from "lucide-react";
import api from "@/lib/api";

const DISMISS_KEY = "flowforge.no-providers-banner.dismissed";

export default function NoProvidersBanner() {
  const [show, setShow] = useState(false);

  useEffect(() => {
    if (typeof window !== "undefined" && sessionStorage.getItem(DISMISS_KEY)) {
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const res = await api.getAIProviders({ include_inactive: true });
        if (!cancelled && res.providers.length === 0) {
          setShow(true);
        }
      } catch {
        // Silent: auth failures or offline shouldn't spam the UI.
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (!show) return null;

  const dismiss = () => {
    sessionStorage.setItem(DISMISS_KEY, "1");
    setShow(false);
  };

  return (
    <div className="flex items-center gap-3 border-b border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-900 dark:border-amber-900/40 dark:bg-amber-950/30 dark:text-amber-200">
      <AlertTriangle className="h-4 w-4 shrink-0" />
      <div className="flex-1">
        No LLM providers configured. AI steps will fail until you{" "}
        <Link
          href="/settings?tab=ai-providers"
          className="font-medium underline underline-offset-2"
        >
          add a provider
        </Link>
        .
      </div>
      <button
        type="button"
        onClick={dismiss}
        className="rounded p-1 hover:bg-amber-100 dark:hover:bg-amber-900/40"
        aria-label="Dismiss"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  );
}

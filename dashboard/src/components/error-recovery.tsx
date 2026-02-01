"use client";

import { useState, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
  AlertCircle,
  RefreshCw,
  WifiOff,
  ServerCrash,
  Clock,
  XCircle,
} from "lucide-react";
import { toast } from "sonner";

interface RetryConfig {
  maxAttempts?: number;
  baseDelay?: number;
  maxDelay?: number;
}

interface UseRetryOptions<T> extends RetryConfig {
  onSuccess?: (data: T) => void;
  onError?: (error: Error) => void;
  onRetry?: (attempt: number, error: Error) => void;
}

/**
 * Hook for handling retries with exponential backoff.
 */
export function useRetry<T>(
  fn: () => Promise<T>,
  options: UseRetryOptions<T> = {}
) {
  const {
    maxAttempts = 3,
    baseDelay = 1000,
    maxDelay = 30000,
    onSuccess,
    onError,
    onRetry,
  } = options;

  const [isRetrying, setIsRetrying] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [lastError, setLastError] = useState<Error | null>(null);

  const execute = useCallback(async () => {
    setIsRetrying(true);
    setLastError(null);

    for (let i = 0; i < maxAttempts; i++) {
      try {
        setAttempt(i + 1);
        const result = await fn();
        setIsRetrying(false);
        setAttempt(0);
        onSuccess?.(result);
        return result;
      } catch (error) {
        const err = error instanceof Error ? error : new Error(String(error));
        setLastError(err);

        if (i < maxAttempts - 1) {
          onRetry?.(i + 1, err);
          // Exponential backoff with jitter
          const delay = Math.min(
            baseDelay * Math.pow(2, i) * (0.5 + Math.random()),
            maxDelay
          );
          await new Promise((resolve) => setTimeout(resolve, delay));
        } else {
          onError?.(err);
        }
      }
    }

    setIsRetrying(false);
    return null;
  }, [fn, maxAttempts, baseDelay, maxDelay, onSuccess, onError, onRetry]);

  const reset = useCallback(() => {
    setIsRetrying(false);
    setAttempt(0);
    setLastError(null);
  }, []);

  return {
    execute,
    isRetrying,
    attempt,
    lastError,
    reset,
  };
}

/**
 * Categorize errors for better user feedback.
 */
export type ErrorCategory = "network" | "server" | "timeout" | "auth" | "unknown";

export function categorizeError(error: Error | null): ErrorCategory {
  if (!error) return "unknown";

  const message = error.message.toLowerCase();

  if (message.includes("network") || message.includes("fetch")) {
    return "network";
  }
  if (message.includes("timeout") || message.includes("timed out")) {
    return "timeout";
  }
  if (message.includes("401") || message.includes("403") || message.includes("unauthorized")) {
    return "auth";
  }
  if (message.includes("500") || message.includes("502") || message.includes("503")) {
    return "server";
  }

  return "unknown";
}

const ERROR_CONFIG: Record<ErrorCategory, {
  icon: typeof AlertCircle;
  title: string;
  description: string;
  retryable: boolean;
}> = {
  network: {
    icon: WifiOff,
    title: "Connection Lost",
    description: "Unable to reach the server. Please check your internet connection.",
    retryable: true,
  },
  server: {
    icon: ServerCrash,
    title: "Server Error",
    description: "The server encountered an error. Our team has been notified.",
    retryable: true,
  },
  timeout: {
    icon: Clock,
    title: "Request Timeout",
    description: "The request took too long to complete. Please try again.",
    retryable: true,
  },
  auth: {
    icon: XCircle,
    title: "Authentication Error",
    description: "Your session may have expired. Please log in again.",
    retryable: false,
  },
  unknown: {
    icon: AlertCircle,
    title: "Something Went Wrong",
    description: "An unexpected error occurred. Please try again.",
    retryable: true,
  },
};

interface ErrorRecoveryAlertProps {
  error: Error | null;
  onRetry?: () => void;
  isRetrying?: boolean;
  className?: string;
}

/**
 * Error alert component with categorized messages and retry button.
 */
export function ErrorRecoveryAlert({
  error,
  onRetry,
  isRetrying = false,
  className,
}: ErrorRecoveryAlertProps) {
  if (!error) return null;

  const category = categorizeError(error);
  const config = ERROR_CONFIG[category];
  const Icon = config.icon;

  return (
    <Alert variant="destructive" className={className}>
      <Icon className="h-4 w-4" />
      <AlertTitle>{config.title}</AlertTitle>
      <AlertDescription className="flex items-center justify-between">
        <span>{config.description}</span>
        {config.retryable && onRetry && (
          <Button
            variant="outline"
            size="sm"
            onClick={onRetry}
            disabled={isRetrying}
            className="ml-4"
          >
            <RefreshCw className={`mr-2 h-4 w-4 ${isRetrying ? "animate-spin" : ""}`} />
            {isRetrying ? "Retrying..." : "Retry"}
          </Button>
        )}
      </AlertDescription>
    </Alert>
  );
}

interface RetryToastOptions {
  action?: string;
  onRetry: () => void;
}

/**
 * Show an error toast with optional retry button.
 */
export function showErrorToast(error: Error | string, options?: RetryToastOptions) {
  const message = typeof error === "string" ? error : error.message;
  const category = typeof error === "string" ? "unknown" : categorizeError(error);
  const config = ERROR_CONFIG[category];

  if (options?.onRetry && config.retryable) {
    toast.error(config.title, {
      description: message,
      action: {
        label: "Retry",
        onClick: options.onRetry,
      },
      duration: 10000,
    });
  } else {
    toast.error(config.title, {
      description: message,
    });
  }
}

/**
 * Inline retry button for failed items.
 */
interface RetryButtonProps {
  onRetry: () => void;
  isRetrying?: boolean;
  size?: "sm" | "default" | "lg";
  variant?: "default" | "outline" | "ghost";
}

export function RetryButton({
  onRetry,
  isRetrying = false,
  size = "sm",
  variant = "outline",
}: RetryButtonProps) {
  return (
    <Button
      variant={variant}
      size={size}
      onClick={onRetry}
      disabled={isRetrying}
    >
      <RefreshCw className={`mr-2 h-4 w-4 ${isRetrying ? "animate-spin" : ""}`} />
      {isRetrying ? "Retrying..." : "Retry"}
    </Button>
  );
}

/**
 * Wrapper component for data fetching with built-in error recovery.
 */
interface DataFetcherProps<T> {
  fetcher: () => Promise<T>;
  children: (data: T) => React.ReactNode;
  loadingComponent?: React.ReactNode;
  errorComponent?: (error: Error, retry: () => void, isRetrying: boolean) => React.ReactNode;
  onSuccess?: (data: T) => void;
  retryConfig?: RetryConfig;
}

export function DataFetcher<T>({
  fetcher,
  children,
  loadingComponent,
  errorComponent,
  onSuccess,
  retryConfig,
}: DataFetcherProps<T>) {
  const [data, setData] = useState<T | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const { execute, isRetrying, lastError } = useRetry(fetcher, {
    ...retryConfig,
    onSuccess: (result) => {
      setData(result);
      setIsLoading(false);
      onSuccess?.(result);
    },
    onError: () => {
      setIsLoading(false);
    },
    onRetry: (attempt) => {
      toast.info(`Retrying... (attempt ${attempt})`);
    },
  });

  // Initial fetch
  useState(() => {
    execute();
  });

  if (isLoading && !lastError) {
    return loadingComponent || <div>Loading...</div>;
  }

  if (lastError && !data) {
    if (errorComponent) {
      return errorComponent(lastError, execute, isRetrying);
    }
    return (
      <ErrorRecoveryAlert
        error={lastError}
        onRetry={execute}
        isRetrying={isRetrying}
      />
    );
  }

  if (data) {
    return children(data);
  }

  return null;
}

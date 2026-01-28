"use client";

import { Component, type ReactNode } from "react";
import { AlertCircle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error("Error caught by boundary:", error, errorInfo);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <Card className="mx-auto max-w-lg mt-8">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-destructive">
              <AlertCircle className="h-5 w-5" />
              Something went wrong
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-muted-foreground mb-4">
              An unexpected error occurred. Please try refreshing the page.
            </p>
            {process.env.NODE_ENV === "development" && this.state.error && (
              <pre className="bg-muted p-4 rounded-md text-xs overflow-auto max-h-48">
                {this.state.error.message}
                {"\n\n"}
                {this.state.error.stack}
              </pre>
            )}
          </CardContent>
          <CardFooter className="flex gap-2">
            <Button variant="outline" onClick={this.handleReset}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Try Again
            </Button>
            <Button variant="default" onClick={() => window.location.reload()}>
              Reload Page
            </Button>
          </CardFooter>
        </Card>
      );
    }

    return this.props.children;
  }
}

// Functional wrapper for easier use with hooks
interface ErrorBoundaryWrapperProps {
  children: ReactNode;
  fallback?: ReactNode;
}

export function WithErrorBoundary({ children, fallback }: ErrorBoundaryWrapperProps) {
  return <ErrorBoundary fallback={fallback}>{children}</ErrorBoundary>;
}

import { LucideIcon, Inbox, AlertCircle, FileQuestion } from "lucide-react";

interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description?: string;
  children?: React.ReactNode;
}

export function EmptyState({
  icon: Icon = Inbox,
  title,
  description,
  children,
}: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-muted">
        <Icon className="h-6 w-6 text-muted-foreground" />
      </div>
      <h3 className="mt-4 text-lg font-medium">{title}</h3>
      {description && (
        <p className="mt-2 text-sm text-muted-foreground max-w-sm">{description}</p>
      )}
      {children && <div className="mt-4">{children}</div>}
    </div>
  );
}

export function NoDataState({ resource }: { resource: string }) {
  return (
    <EmptyState
      icon={Inbox}
      title={`No ${resource} yet`}
      description={`${resource.charAt(0).toUpperCase() + resource.slice(1)} will appear here once they are created.`}
    />
  );
}

export function ErrorState({ message }: { message?: string }) {
  return (
    <EmptyState
      icon={AlertCircle}
      title="Unable to load data"
      description={message || "Could not connect to the server. Make sure the FlowForge server is running."}
    />
  );
}

export function NotFoundState({ resource }: { resource: string }) {
  return (
    <EmptyState
      icon={FileQuestion}
      title={`${resource} not found`}
      description={`The ${resource.toLowerCase()} you're looking for doesn't exist or has been deleted.`}
    />
  );
}

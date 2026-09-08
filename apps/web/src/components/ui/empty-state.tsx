import { cn } from "@/lib/utils";

interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
  className?: string;
}

export function EmptyState({ icon, title, description, action, className }: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-3 rounded-2xl border border-dashed border-line px-6 py-12 text-center",
        className,
      )}
    >
      {icon ? (
        <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-surface2 text-muted">
          {icon}
        </div>
      ) : null}
      <div>
        <p className="text-sm font-medium text-ink">{title}</p>
        {description ? <p className="mx-auto mt-1 max-w-sm text-xs text-muted">{description}</p> : null}
      </div>
      {action}
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-2xl border border-danger/25 bg-danger/5 px-6 py-10 text-center">
      <p className="text-sm font-medium text-danger">{message}</p>
      {onRetry ? (
        <button
          type="button"
          onClick={onRetry}
          className="rounded-lg border border-line px-3 py-1.5 text-xs text-muted transition hover:text-ink"
        >
          Try again
        </button>
      ) : null}
    </div>
  );
}

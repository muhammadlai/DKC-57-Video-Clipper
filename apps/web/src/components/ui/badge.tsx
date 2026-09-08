import { cn } from "@/lib/utils";

type BadgeVariant = "default" | "ok" | "warn" | "danger" | "accent" | "outline";

const variants: Record<BadgeVariant, string> = {
  default: "bg-surface2 text-muted border-line",
  ok: "bg-ok/15 text-ok border-ok/30",
  warn: "bg-warn/15 text-warn border-warn/30",
  danger: "bg-danger/15 text-danger border-danger/30",
  accent: "bg-accent/15 text-accent border-accent/30",
  outline: "bg-transparent text-muted border-line",
};

export function Badge({
  className,
  variant = "default",
  dot,
  ...props
}: React.HTMLAttributes<HTMLSpanElement> & { variant?: BadgeVariant; dot?: boolean }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11px] font-medium leading-5",
        variants[variant],
        className,
      )}
      {...props}
    >
      {dot ? <span className="h-1.5 w-1.5 rounded-full bg-current" /> : null}
      {props.children}
    </span>
  );
}

export function Spinner({ className }: { className?: string }) {
  return (
    <span
      className={cn(
        "inline-block h-5 w-5 animate-spin rounded-full border-2 border-line border-t-accent",
        className,
      )}
      role="status"
      aria-label="Loading"
    />
  );
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn("animate-pulse-soft rounded-lg bg-surface2/80", className)} />;
}

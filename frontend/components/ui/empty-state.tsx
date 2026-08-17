import type { LucideIcon } from "lucide-react";

import { cn } from "@/lib/utils";

/** One empty state for the whole product shell.
 *  Five places had grown their own ("No requests yet." at py-8 inside tables,
 *  py-12 inside chart cards, nothing at all on the models grid), so the same
 *  condition read differently depending on where you hit it. */
export function EmptyState({
  title,
  hint,
  icon: Icon,
  className,
}: {
  title: string;
  hint?: string;
  icon?: LucideIcon;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-2 px-6 py-12 text-center",
        className,
      )}
    >
      {Icon && (
        <Icon
          className="size-6 text-muted-foreground/60"
          strokeWidth={1.6}
          aria-hidden="true"
        />
      )}
      <p className="text-body-sm text-muted-foreground">{title}</p>
      {hint && (
        <p className="max-w-xs text-caption text-muted-foreground/80">{hint}</p>
      )}
    </div>
  );
}

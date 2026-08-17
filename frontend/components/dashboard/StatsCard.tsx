import type { LucideIcon } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";

export function StatsCard({
  label,
  value,
  icon: Icon,
  note,
}: {
  label: string;
  value: string | number;
  icon?: LucideIcon;
  /** Optional line under the value, for a figure that needs a caveat
   *  (e.g. "estimated vs. a premium model"). */
  note?: string;
}) {
  return (
    <Card>
      <CardContent className="p-5">
        <div className="flex items-center justify-between">
          <div className="text-body-sm text-muted-foreground">{label}</div>
          {Icon && (
            <span className="grid size-8 place-items-center rounded-lg bg-primary/10 text-primary">
              <Icon className="size-4" aria-hidden="true" />
            </span>
          )}
        </div>
        <div className="mt-2 font-display text-3xl font-bold tracking-tight">
          {value}
        </div>
        {note && <p className="mt-1 text-caption text-muted-foreground">{note}</p>}
      </CardContent>
    </Card>
  );
}

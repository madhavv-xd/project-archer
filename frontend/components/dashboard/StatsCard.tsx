import { Card, CardContent } from "@/components/ui/card";

export function StatsCard({
  label,
  value,
  icon: Icon,
  note,
}: {
  label: string;
  value: string | number;
  icon?: React.ElementType;
  /** Optional line under the value, for a figure that needs a caveat
   *  (e.g. "estimated vs. a premium model"). */
  note?: string;
}) {
  return (
    <Card className="relative overflow-hidden hover:-translate-y-0.5 hover:border-(--accent-700)">
      {/* Nocturne corner wash */}
      <span
        aria-hidden
        className="pointer-events-none absolute right-0 top-0 size-11"
        style={{ background: "linear-gradient(225deg, rgba(145,132,217,.22), transparent 70%)" }}
      />
      <CardContent className="p-4">
        <div className="flex items-center justify-between">
          <div className="font-mono text-label uppercase text-(--neutral-600)">{label}</div>
          {Icon && (
            <span className="grid size-8 place-items-center rounded-lg bg-(--accent-900) text-(--accent-300)">
              <Icon size={16} aria-hidden="true" />
            </span>
          )}
        </div>
        <div className="mt-2 text-stat">{value}</div>
        {note && <p className="mt-1 text-caption text-muted-foreground">{note}</p>}
      </CardContent>
    </Card>
  );
}

import { Card, CardContent } from "@/components/ui/card";

// Default free-plan monthly request quota (backend default in rate_limit.py).
const MONTHLY_QUOTA = 10000;

export function QuotaMeter({ used }: { used: number }) {
  const rawPct = (used / MONTHLY_QUOTA) * 100;
  const pct = Math.min(100, Math.round(rawPct));
  const state = rawPct >= 100 ? "over" : rawPct >= 80 ? "warn" : "normal";
  const barColor =
    state === "over" ? "bg-destructive" : state === "warn" ? "bg-amber-500" : "bg-primary";
  const note =
    state === "over"
      ? "Quota reached — new requests are rejected until it resets on the 1st."
      : state === "warn"
        ? `${pct}% used · approaching your monthly limit`
        : `${pct}% used · resets on the 1st`;

  return (
    <Card>
      <CardContent className="p-5">
        <div className="flex items-baseline justify-between">
          <div className="text-sm text-muted-foreground">Monthly quota</div>
          <div className="text-sm text-muted-foreground">
            {used.toLocaleString()} / {MONTHLY_QUOTA.toLocaleString()}
          </div>
        </div>
        <div className="mt-3 h-2.5 w-full overflow-hidden rounded-full bg-muted">
          <div
            className={`h-full rounded-full transition-[width] ${barColor}`}
            style={{ width: `${pct}%` }}
          />
        </div>
        <p className={`mt-2 text-xs ${state === "over" ? "text-destructive" : "text-muted-foreground"}`}>
          {note}
        </p>
      </CardContent>
    </Card>
  );
}

import { Card, CardContent } from "@/components/ui/card";

// Default free-plan monthly request quota (backend default in rate_limit.py).
const MONTHLY_QUOTA = 10000;

export function QuotaMeter({ used }: { used: number }) {
  const pct = Math.min(100, Math.round((used / MONTHLY_QUOTA) * 100));
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
            className="h-full rounded-full bg-primary transition-[width]"
            style={{ width: `${pct}%` }}
          />
        </div>
        <p className="mt-2 text-xs text-muted-foreground">{pct}% used · resets on the 1st</p>
      </CardContent>
    </Card>
  );
}

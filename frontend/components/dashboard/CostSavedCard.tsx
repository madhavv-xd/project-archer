import { PiggyBank } from "lucide-react";

import { estimateCostSaved } from "@/lib/pricing";
import { Card, CardContent } from "@/components/ui/card";

export function CostSavedCard({ totalTokens }: { totalTokens: number }) {
  const saved = estimateCostSaved(totalTokens);
  return (
    <Card>
      <CardContent className="p-5">
        <div className="flex items-center justify-between">
          <div className="text-sm text-muted-foreground">Est. cost saved</div>
          <span className="grid size-8 place-items-center rounded-lg bg-primary/10 text-primary">
            <PiggyBank className="size-4" />
          </span>
        </div>
        <div className="mt-2 font-display text-3xl font-bold tracking-tight">
          ${saved.toFixed(2)}
        </div>
        <p className="mt-1 text-xs text-muted-foreground">
          estimated vs. a premium model, on {totalTokens.toLocaleString()} tokens
        </p>
      </CardContent>
    </Card>
  );
}

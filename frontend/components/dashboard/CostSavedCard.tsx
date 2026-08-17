import { PiggyBank } from "lucide-react";

import { estimateCostSaved } from "@/lib/pricing";
import { StatsCard } from "@/components/dashboard/StatsCard";

/** Was a hand-rolled copy of StatsCard's markup plus a footnote, so the two
 *  drifted apart on spacing and type. Now just StatsCard with a `note`. */
export function CostSavedCard({ totalTokens }: { totalTokens: number }) {
  return (
    <StatsCard
      label="Est. cost saved"
      value={`$${estimateCostSaved(totalTokens).toFixed(2)}`}
      icon={PiggyBank}
      note={`estimated vs. a premium model, on ${totalTokens.toLocaleString()} tokens`}
    />
  );
}

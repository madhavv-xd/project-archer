import { Target } from "lucide-react";

import { cn } from "@/lib/utils";

/** Archer wordmark — gold target glyph + display-face name. */
export function Brandmark({
  className,
  iconSize = 20,
}: {
  className?: string;
  iconSize?: number;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-2 font-display font-extrabold tracking-wide",
        className,
      )}
    >
      <Target size={iconSize} className="text-primary" strokeWidth={2.2} />
      ARCHER
    </span>
  );
}

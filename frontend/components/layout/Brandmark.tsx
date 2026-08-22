import { cn } from "@/lib/utils";

/** Archer brand mark — gold arrow piercing a broken target ring (handoff
 * README §The logo), in a gold-tinted badge. Wordmark stays light: gold mark,
 * light text. The only warm colour in the product besides Fletch. */
export function Brandmark({
  className,
  iconSize = 20,
}: {
  className?: string;
  iconSize?: number;
}) {
  const badge = Math.round(iconSize * 1.5); // 20px glyph → 30px badge
  return (
    <span
      className={cn("inline-flex items-center gap-2 font-semibold tracking-[.02em]", className)}
    >
      <span
        className="inline-flex items-center justify-center rounded-[10px]"
        style={{
          width: badge,
          height: badge,
          background: "rgba(233,185,73,.12)",
          border: "1px solid rgba(233,185,73,.42)",
          boxShadow: "0 0 18px -6px rgba(233,185,73,.6)",
        }}
      >
        <svg viewBox="0 0 32 32" aria-hidden="true" width={iconSize} height={iconSize}>
          <circle
            cx="16"
            cy="16"
            r="12.6"
            fill="none"
            stroke="#E9B949"
            strokeWidth="2.6"
            strokeLinecap="round"
            strokeDasharray="58 22"
            transform="rotate(-180 16 16)"
          />
          <circle cx="16" cy="16" r="7.4" fill="none" stroke="#CE9524" strokeWidth="2.2" />
          <line x1="4.2" y1="27.8" x2="13" y2="19" stroke="#E9B949" strokeWidth="3.2" strokeLinecap="round" />
          <line x1="4" y1="23.8" x2="8.2" y2="28" stroke="#F7DFA0" strokeWidth="2.2" strokeLinecap="round" />
          <polygon points="20.8,11.2 12.4,14.2 17.8,19.6" fill="#F7DFA0" />
        </svg>
      </span>
      ARCHER
    </span>
  );
}

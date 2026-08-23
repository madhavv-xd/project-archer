/** Fletch — the Archer mascot. A gold character whose single eye is a bullseye,
    holding a recurve bow that draws back on hover. Pure inline SVG.

    Nocturne recolour: outlines are indigo (#2b2741, was near-black), the
    bowstring is accent-300, and everything that used to be vermilion —
    fletching, blush, pupil ring — is now the accent. Fletch's gold is the only
    warm colour left in the product, so it stays untouched. Geometry unchanged. */
export function Mascot({ className = "" }: { className?: string }) {
  return (
    <svg
      className={`lp-mascot lp-mascot-wrap ${className}`.trim()}
      viewBox="0 0 220 248"
      role="img"
      aria-label="Fletch, the Archer mascot, drawing a bow"
      xmlns="http://www.w3.org/2000/svg"
    >
      <defs>
        <linearGradient id="fletch-body" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#F7DFA0" />
          <stop offset="0.55" stopColor="#E9B949" />
          <stop offset="1" stopColor="#CE9524" />
        </linearGradient>
      </defs>

      {/* ground shadow */}
      <ellipse cx="110" cy="232" rx="58" ry="9" fill="rgba(0,0,0,0.4)" />

      <g className="lp-mascot-bob">
        {/* recurve bow + nocked arrow (behind the body, to the right) */}
        <g className="lp-mascot-bow">
          <path
            d="M160 60 Q210 124 160 188"
            fill="none"
            stroke="#2b2741"
            strokeWidth="8"
            strokeLinecap="round"
          />
          <path d="M160 62 L160 186" fill="none" stroke="#d2cefd" strokeWidth="2" />
        </g>
        {/* The shaft runs past the bow (x>168) so the draw-back on hover is
            actually visible — it used to end at 160, fully behind the body. */}
        <g className="lp-mascot-arrow">
          <line x1="92" y1="124" x2="206" y2="124" stroke="#2b2741" strokeWidth="5" strokeLinecap="round" />
          <polygon points="92,124 104,118 104,130" fill="#9184d9" />
          <polygon points="204,117 216,124 204,131" fill="#e9e9ed" />
        </g>

        {/* fletching crest */}
        <g>
          <path d="M100 60 C96 36 86 30 78 30 C84 42 86 52 96 62 Z" fill="#9184d9" />
          <path d="M110 56 C110 30 110 22 110 18 C116 30 116 44 116 58 Z" fill="#F7DFA0" />
          <path d="M120 60 C124 36 134 30 142 30 C136 42 134 52 124 62 Z" fill="#9184d9" />
        </g>

        {/* body */}
        <rect
          x="52"
          y="64"
          width="116"
          height="130"
          rx="52"
          fill="url(#fletch-body)"
          stroke="#2b2741"
          strokeWidth="4"
        />
        <ellipse cx="86" cy="100" rx="20" ry="13" fill="rgba(255,255,255,0.3)" />

        {/* little arm to the bow */}
        <rect x="146" y="120" width="20" height="11" rx="5.5" fill="#CE9524" stroke="#2b2741" strokeWidth="3" />

        {/* blush */}
        <circle cx="74" cy="150" r="7" fill="#9184d9" opacity="0.4" />
        <circle cx="134" cy="150" r="7" fill="#9184d9" opacity="0.4" />

        {/* bullseye eye */}
        <g className="lp-mascot-eye">
          <circle cx="104" cy="126" r="23" fill="#f3f5fe" stroke="#2b2741" strokeWidth="3.5" />
          <circle cx="104" cy="126" r="15" fill="#262a60" />
          <circle cx="104" cy="126" r="9" fill="#f3f5fe" />
          <circle cx="104" cy="126" r="4.5" fill="#9184d9" />
          <circle cx="99" cy="120" r="2.4" fill="#ffffff" opacity="0.95" />
        </g>

        {/* feet */}
        <ellipse cx="88" cy="196" rx="14" ry="9" fill="#CE9524" stroke="#2b2741" strokeWidth="3" />
        <ellipse cx="124" cy="196" rx="14" ry="9" fill="#CE9524" stroke="#2b2741" strokeWidth="3" />
      </g>
    </svg>
  );
}

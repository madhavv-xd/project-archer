/** Fletch — the Archer mascot. A gold character whose single eye is a bullseye,
    holding a recurve bow that draws back on hover. Pure inline SVG. */
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
          <stop offset="0" stopColor="#F4D27A" />
          <stop offset="0.55" stopColor="#E9B949" />
          <stop offset="1" stopColor="#D49B2C" />
        </linearGradient>
      </defs>

      {/* ground shadow */}
      <ellipse cx="110" cy="232" rx="58" ry="9" fill="rgba(0,0,0,0.34)" />

      <g className="lp-mascot-bob">
        {/* recurve bow + nocked arrow (behind the body, to the right) */}
        <path
          d="M160 60 Q210 124 160 188"
          fill="none"
          stroke="#0c120f"
          strokeWidth="7"
          strokeLinecap="round"
        />
        <path
          className="lp-mascot-string"
          d="M160 62 L160 186"
          fill="none"
          stroke="#ECE7D7"
          strokeWidth="2"
        />
        <g className="lp-mascot-arrow">
          <line x1="92" y1="124" x2="160" y2="124" stroke="#0c120f" strokeWidth="4" strokeLinecap="round" />
          <polygon points="92,124 104,118 104,130" fill="#E2533B" />
          <polygon points="158,116 168,124 158,132" fill="#8AA593" />
        </g>

        {/* fletching crest */}
        <g>
          <path d="M100 60 C96 36 86 30 78 30 C84 42 86 52 96 62 Z" fill="#E2533B" />
          <path d="M110 56 C110 30 110 22 110 18 C116 30 116 44 116 58 Z" fill="#F4D27A" />
          <path d="M120 60 C124 36 134 30 142 30 C136 42 134 52 124 62 Z" fill="#E2533B" />
        </g>

        {/* body */}
        <rect x="52" y="64" width="116" height="130" rx="52" fill="url(#fletch-body)" />
        <ellipse cx="86" cy="100" rx="20" ry="13" fill="rgba(255,255,255,0.22)" />

        {/* little arm to the bow */}
        <rect x="146" y="120" width="20" height="11" rx="5.5" fill="#D49B2C" />

        {/* blush */}
        <circle cx="74" cy="150" r="6.5" fill="#E2533B" opacity="0.45" />
        <circle cx="134" cy="150" r="6.5" fill="#E2533B" opacity="0.45" />

        {/* bullseye eye */}
        <g className="lp-mascot-eye">
          <circle cx="104" cy="126" r="23" fill="#ECE7D7" />
          <circle cx="104" cy="126" r="15" fill="#0e1512" />
          <circle cx="104" cy="126" r="9" fill="#ECE7D7" />
          <circle cx="104" cy="126" r="4.5" fill="#E2533B" />
          <circle cx="99" cy="120" r="2.4" fill="#ffffff" opacity="0.9" />
        </g>

        {/* feet */}
        <ellipse cx="88" cy="196" rx="14" ry="9" fill="#C98F26" />
        <ellipse cx="124" cy="196" rx="14" ry="9" fill="#C98F26" />
      </g>
    </svg>
  );
}

/** The signature: an archery target whose bullseye is `archer-auto`, ringed by
    the five real models, with arrows that land dead center. */
const MODELS = [
  { name: "llama-3.3-70b", cls: "m1" },
  { name: "gpt-oss-120b", cls: "m2" },
  { name: "qwen-2.5-72b", cls: "m3" },
  { name: "llama-3.1-8b", cls: "m4" },
  { name: "gpt-oss-20b", cls: "m5" },
];

function Arrow({ className = "" }: { className?: string }) {
  return (
    <g className={className}>
      <line x1="96" y1="200" x2="196" y2="200" stroke="#0c120f" strokeWidth="4" strokeLinecap="round" />
      <polygon points="196,200 184,194 184,206" fill="#ECE7D7" />
      <g stroke="#E2533B" strokeWidth="3" strokeLinecap="round">
        <line x1="96" y1="200" x2="106" y2="192" />
        <line x1="96" y1="200" x2="106" y2="208" />
        <line x1="103" y1="200" x2="113" y2="192" />
        <line x1="103" y1="200" x2="113" y2="208" />
      </g>
    </g>
  );
}

export function TargetShot() {
  return (
    <div className="lp-target-rel">
      <svg
        className="lp-target-svg"
        viewBox="0 0 400 400"
        role="img"
        aria-label="An archery target: arrows land in the archer-auto bullseye, ringed by five models"
        xmlns="http://www.w3.org/2000/svg"
      >
        <defs>
          <radialGradient id="verm-bull" cx="0.42" cy="0.38" r="0.7">
            <stop offset="0" stopColor="#F2704F" />
            <stop offset="1" stopColor="#C5402B" />
          </radialGradient>
        </defs>

        {/* filled bands */}
        <circle cx="200" cy="200" r="190" fill="#15211a" />
        <circle cx="200" cy="200" r="152" fill="#18271e" />
        <circle cx="200" cy="200" r="114" fill="#1d3025" />
        <circle cx="200" cy="200" r="76" fill="#243b2c" />

        {/* drawn-on hairline rings */}
        <g fill="none" stroke="rgba(233,185,73,0.5)" strokeWidth="1.5">
          <circle className="lp-ring-draw" pathLength={1} cx="200" cy="200" r="190" />
          <circle className="lp-ring-draw r2" pathLength={1} cx="200" cy="200" r="152" />
          <circle className="lp-ring-draw r3" pathLength={1} cx="200" cy="200" r="114" />
          <circle className="lp-ring-draw r4" pathLength={1} cx="200" cy="200" r="76" />
        </g>

        {/* landed arrows (already on target) */}
        <g transform="rotate(20 200 200)" opacity="0.9">
          <Arrow />
        </g>
        <g transform="rotate(-32 200 200)" opacity="0.9">
          <Arrow />
        </g>

        {/* bullseye */}
        <g className="lp-bull-pulse">
          <circle cx="200" cy="200" r="46" fill="url(#verm-bull)" />
          <circle cx="200" cy="200" r="46" fill="none" stroke="rgba(255,255,255,0.25)" strokeWidth="1.5" />
          <text className="lp-bull-label" x="200" y="204" textAnchor="middle">
            archer-auto
          </text>
        </g>

        {/* the live shot */}
        <Arrow className="lp-fly" />
      </svg>

      {MODELS.map((m) => (
        <span key={m.name} className={`lp-mtag ${m.cls}`}>
          <i className="lp-mtag-dot" />
          {m.name}
        </span>
      ))}
    </div>
  );
}

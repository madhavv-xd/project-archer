"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import {
  ArrowRight,
  ArrowsClockwise,
  ArrowUpRight,
  CheckCircle,
  Crosshair,
  CrosshairSimple,
  Key,
  Lightning,
  Plug,
  PlugsConnected,
  Plus,
  PlayCircle,
  Scroll,
  TerminalWindow,
} from "@phosphor-icons/react";

import "./landing.css";
import { Reveal } from "./Reveal";
import { Mascot } from "./Mascot";
import { HeroScene } from "./HeroScene";
import { Brandmark } from "@/components/layout/Brandmark";
import { decide, tokens, DOMAIN_MODEL, type Decision } from "./routeRules";

/** Display copy for the active catalog (migration 007). Model names live in the
 *  DB everywhere else; this list is marketing display only. */
const MODELS = [
  { name: "gpt-oss-120b", provider: "Groq", ctx: "131K", best: "Code, math, and the default shot" },
  { name: "qwen3.6-27b", provider: "Groq", ctx: "131K", best: "Fast replies to short, simple asks" },
  { name: "gpt-oss-20b", provider: "Groq", ctx: "131K", best: "Quick conversational turns" },
  { name: "nemotron-3-nano", provider: "Ollama", ctx: "131K", best: "Light general-purpose work" },
  { name: "nemotron-3-ultra", provider: "Ollama", ctx: "262K", best: "Analysis and step-by-step reasoning" },
  { name: "nemotron-3-super", provider: "Ollama", ctx: "262K", best: "Deep reasoning, held in reserve" },
  { name: "minimax-m3", provider: "Ollama", ctx: "524K", best: "Very long-context analysis" },
  { name: "gemma4-31b", provider: "Ollama", ctx: "131K", best: "Writing and long-form drafting" },
];

/** Chain order is `models.fallback_priority` from migration 007 — Groq holds
 *  0-2, the slowest model sits last. Not the same thing as domain ownership. */
const CHAIN = [
  { name: "gpt-oss-120b", provider: "Groq" },
  { name: "qwen3.6-27b", provider: "Groq" },
  { name: "gpt-oss-20b", provider: "Groq" },
  { name: "nemotron-3-nano", provider: "Ollama Cloud" },
  { name: "nemotron-3-ultra", provider: "Ollama Cloud" },
  { name: "nemotron-3-super", provider: "Ollama Cloud" },
  { name: "minimax-m3", provider: "Ollama Cloud" },
  { name: "gemma4-31b", provider: "Ollama Cloud" },
];

const PRESETS = [
  "Write a binary search in Rust and explain the invariant",
  "Derive the integral of x·ln(x)",
  "Draft a launch email for our new pricing",
  "hi",
];

const API_BASE = "https://api.project-archer.online/v1";

const SNIPPETS = {
  python: {
    file: "quickstart.py",
    code: `from openai import OpenAI

client = OpenAI(
    api_key="arch_sk_...",
    base_url="${API_BASE}",
)

resp = client.chat.completions.create(
    model="archer-auto",   # accepted, then ignored
    messages=[{
        "role": "user",
        "content": "Write a binary search in Rust",
    }],
)
print(resp.choices[0].message.content)`,
  },
  javascript: {
    file: "quickstart.ts",
    code: `import OpenAI from "openai";

const client = new OpenAI({
  apiKey: "arch_sk_...",
  baseURL: "${API_BASE}",
});

const resp = await client.chat.completions.create({
  model: "archer-auto",  // accepted, then ignored
  messages: [
    { role: "user", content: "Write a binary search in Rust" },
  ],
});
console.log(resp.choices[0].message.content);`,
  },
  curl: {
    file: "shell",
    code: `curl ${API_BASE}/chat/completions \\
  -H "Authorization: Bearer arch_sk_..." \\
  -H "Content-Type: application/json" \\
  -d '{
    "model": "archer-auto",
    "messages": [{"role": "user", "content": "Write a binary search in Rust"}]
  }'`,
  },
} as const;

type Tab = keyof typeof SNIPPETS;

const FEATURES = [
  { Icon: Crosshair, title: "Intent routing", body: "Each prompt is read and sent to the model that fits it — code, math, analysis, or a quick reply." },
  { Icon: ArrowsClockwise, title: "Automatic fallback", body: "Rate-limited or down? Archer retries down a fixed chain until a model lands the shot." },
  { Icon: PlugsConnected, title: "OpenAI-compatible", body: "A drop-in /v1/chat/completions endpoint. Keep your SDK — just swap the base URL." },
  { Icon: Key, title: "One key for all", body: "A single arch_sk_ key stands in for the wallet of provider keys you'd otherwise juggle." },
  { Icon: Scroll, title: "Every shot logged", body: "See which model answered, why it routed there, plus tokens and latency, on your dashboard." },
  { Icon: Lightning, title: "Normalized replies", body: "Whoever answers, the response always comes back in the same archer-auto shape." },
];

const FAQS = [
  { q: "Do I have to change my code?", a: "Only the base URL and the key. Archer speaks the OpenAI chat-completions protocol, streaming included, so any OpenAI SDK works unchanged. The model field is accepted and then ignored." },
  { q: "How does it decide which model answers?", a: "An embedding pass compares your last user message to six precomputed domain centroids. Above the similarity threshold it decides; below it — or if the embedding provider is unreachable — the keyword rules above take over. Both engines pick a domain, and the domain-to-model mapping lives in the catalog." },
  { q: "What happens when a provider fails?", a: "Retryable failures (rate limit, server error, timeout) walk the fallback chain until a model answers. Client errors are never retried — a bad request fails identically everywhere. If every model fails you get a 503." },
  { q: "Does streaming still work?", a: "Yes, standard SSE chunks. Fallback applies until the first byte reaches you; after that the response is committed, so a mid-stream provider failure ends the stream rather than silently swapping models under a client that is already rendering tokens." },
  { q: "Can I see which model actually answered?", a: "Not from the API — every response reports archer-auto by design. The dashboard's Logs page shows the real model, the routing reason, whether it fell back, time-to-first-token, tokens and latency." },
  { q: "What are the limits?", a: "30 requests per minute and 10,000 requests per month on the free tier, with X-RateLimit headers on every /v1 response. If the limiter's Redis is unavailable, requests are allowed through rather than rejected." },
];

export function Landing({ isAuthed, modelCount }: { isAuthed: boolean; modelCount: number }) {
  const primaryHref = isAuthed ? "/dashboard" : "/register";
  const primaryLabel = isAuthed ? "Open dashboard" : "Get your API key";

  return (
    <div className="lp">
      <div className="lp-grid" aria-hidden />
      <div className="lp-glow" aria-hidden />

      <nav className="lp-nav">
        <div className="lp-wrap lp-nav-inner">
          <Link href="/">
            <Brandmark iconSize={20} />
          </Link>
          <div className="lp-nav-links">
            <a href="#route">Routing</a>
            <a href="#chain">Fallback</a>
            <a href="#models">Models</a>
            <a href="#api">API</a>
            <a href="#faq">FAQ</a>
          </div>
          <div className="lp-nav-cta">
            {!isAuthed && (
              <Link href="/login" className="lp-signin">
                Sign in
              </Link>
            )}
            <Link href={primaryHref} className="lp-btn lp-btn--primary">
              {primaryLabel} <ArrowRight size={14} />
            </Link>
          </div>
        </div>
      </nav>

      <header id="top" className="lp-wrap lp-hero">
        <div>
          <span className="lp-eyebrow">Orchestration-as-a-Service</span>
          <h1 className="lp-h1">
            Every prompt
            <br />
            finds <span className="lp-h1-em">its mark.</span>
          </h1>
          <p className="lp-sub">
            One OpenAI-compatible endpoint that reads each request and sends it to the model
            best suited for it. One key, no model-picking — every answer comes back as{" "}
            <code>archer-auto</code>.
          </p>
          <div className="lp-hero-cta">
            <Link href={primaryHref} className="lp-btn lp-btn--primary">
              {primaryLabel} <ArrowRight size={15} />
            </Link>
            <a href="#route" className="lp-btn lp-btn--ghost">
              <PlayCircle size={16} /> Try the router
            </a>
          </div>
          <div className="lp-pills">
            <span className="lp-pill">
              <span className="lp-blip" />
              {modelCount} models · 2 providers
            </span>
            <span className="lp-pill">POST /v1/chat/completions</span>
            <span className="lp-pill">SSE streaming</span>
          </div>
        </div>

        <div className="lp-stage-wrap">
          <HeroScene />
          <Mascot className="lp-hero-mascot" />
        </div>
      </header>

      <RouteDemo />

      <FallbackChain />

      <section id="models" className="lp-wrap lp-section">
        <Reveal className="lp-split-head">
          <div style={{ maxWidth: "36em" }}>
            <span className="lp-eyebrow">The quiver</span>
            <h2 className="lp-h2">{modelCount} models. One target.</h2>
            <p className="lp-lede">
              A curated pool sits behind your key. You never pick from it — Archer draws the
              right one for every request.
            </p>
          </div>
          <a href="#api" className="lp-api-link">
            GET /v1/models <ArrowUpRight size={13} />
          </a>
        </Reveal>

        <Reveal className="lp-pool">
          <div className="lp-pool-row lp-pool-head">
            <span>Model</span>
            <span>Provider</span>
            <span>Context</span>
            <span>Drawn for</span>
          </div>
          {MODELS.map((m) => (
            <div className="lp-pool-row" key={m.name}>
              <span className="lp-pool-name">{m.name}</span>
              <span className="lp-pool-provider">{m.provider}</span>
              <span className="lp-pool-ctx">{m.ctx}</span>
              <span className="lp-pool-for">{m.best}</span>
            </div>
          ))}
        </Reveal>
        <p className="lp-pool-note">
          Whoever answers, your response always comes back as <b>archer-auto</b>. The client
          never learns which provider served it.
        </p>
      </section>

      <ApiSection />

      <section className="lp-wrap lp-section">
        <Reveal style={{ maxWidth: "34em" }}>
          <span className="lp-eyebrow">Built to never miss</span>
          <h2 className="lp-h2">What the layer actually does.</h2>
        </Reveal>
        <Reveal className="lp-features">
          {FEATURES.map(({ Icon, title, body }) => (
            <div className="lp-feature" key={title}>
              <span className="lp-ico-chip">
                <Icon size={19} />
              </span>
              <h3>{title}</h3>
              <p>{body}</p>
            </div>
          ))}
        </Reveal>
      </section>

      <section id="faq" className="lp-wrap lp-section lp-faq">
        <Reveal>
          <span className="lp-eyebrow">FAQ</span>
          <h2 className="lp-h2">The questions developers actually ask.</h2>
        </Reveal>
        <Reveal className="lp-faq-panel">
          {FAQS.map(({ q, a }) => (
            <details key={q}>
              <summary>
                {q}
                <Plus size={14} />
              </summary>
              <p>{a}</p>
            </details>
          ))}
        </Reveal>
      </section>

      <section className="lp-wrap">
        <Reveal className="lp-cta">
          <div className="lp-cta-inner">
            <div>
              <h2>Ready to let it fly?</h2>
              <p>
                Sign up, generate a key, and point your first request at Archer. The right
                model is already waiting on the line.
              </p>
              <div className="lp-cta-actions">
                <Link href={primaryHref} className="lp-btn lp-btn--onband">
                  {primaryLabel} <ArrowRight size={15} />
                </Link>
                <Link href="/docs" className="lp-btn lp-btn--ghost">
                  Read the docs
                </Link>
              </div>
            </div>
            <Mascot className="lp-cta-mascot" />
          </div>
        </Reveal>
      </section>

      <footer className="lp-footer">
        <div className="lp-wrap lp-footer-inner">
          <Brandmark iconSize={18} />
          <span>Orchestration-as-a-Service · routes every prompt to its best model.</span>
          <span className="lp-mono">api.project-archer.online</span>
        </div>
      </footer>
    </div>
  );
}

/** The routing demo. Steps advance on a 420ms timer so the order of the rules
 *  is readable rather than instantaneous; auto-runs once after mount. */
function RouteDemo() {
  const [input, setInput] = useState(PRESETS[0]);
  const [stage, setStage] = useState(0);
  const [result, setResult] = useState<Decision | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  const run = useCallback((text: string) => {
    const trimmed = text.trim();
    if (!trimmed) return;
    clearTimeout(timer.current);
    setResult(decide(trimmed));
    setStage(1);
    const advance = (n: number) => {
      timer.current = setTimeout(() => {
        setStage(n);
        if (n < 4) advance(n + 1);
      }, 420);
    };
    advance(2);
  }, []);

  useEffect(() => {
    const t = setTimeout(() => run(PRESETS[0]), 900);
    return () => {
      clearTimeout(t);
      clearTimeout(timer.current);
    };
  }, [run]);

  const chosen = result ? DOMAIN_MODEL[result.domain] : null;
  const toks = result ? tokens(input.trim()) : [];

  const steps = [
    {
      n: "01",
      label: "Tokenize the last user message",
      detail:
        result && stage >= 1
          ? toks.slice(0, 12).join(" · ") + (toks.length > 12 ? " …" : "")
          : "waiting for a prompt",
    },
    {
      n: "02",
      label: "Check the rules in priority order",
      detail:
        result && stage >= 2
          ? `rule ${result.rule}  ←  matched "${result.match}"`
          : "coding → math → writing → simple → analysis → default",
    },
    {
      n: "03",
      label: "Resolve the domain to a model",
      detail:
        result && stage >= 3 && chosen
          ? `${result.domain} → ${chosen.model}  ·  ${chosen.provider}`
          : "domain → model comes from the DB catalog",
    },
    {
      n: "04",
      label: "Normalize and log",
      detail:
        result && stage >= 4
          ? `routing_reason=${result.reason}  ·  logged fire-and-forget`
          : "every response is stamped archer-auto",
    },
  ];

  return (
    <section id="route" className="lp-wrap lp-section">
      <Reveal style={{ maxWidth: "44em" }}>
        <span className="lp-eyebrow">The router, in the open</span>
        <h2 className="lp-h2">Type a prompt. Watch it get aimed.</h2>
        <p className="lp-lede" style={{ maxWidth: "36em" }}>
          This runs Archer&apos;s real keyword rules — the same sets and the same priority
          order as <code>app/core/router.py</code>. In production an embedding pass gets first
          say, and these rules catch whatever it isn&apos;t sure about.
        </p>
      </Reveal>

      <Reveal className="lp-demo">
        <div className="lp-card lp-demo-card">
          <div className="lp-demo-bar">
            <TerminalWindow size={14} />
            <span>messages[-1].content</span>
          </div>
          <div className="lp-demo-body">
            <label className="sr-only" htmlFor="lp-demo-input">
              Prompt to route
            </label>
            <textarea
              id="lp-demo-input"
              className="lp-demo-input"
              rows={3}
              value={input}
              placeholder="Write a binary search in Rust"
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
                  e.preventDefault();
                  run(input);
                }
              }}
            />
            <div className="lp-presets">
              {PRESETS.map((p) => (
                <button
                  key={p}
                  type="button"
                  className="lp-preset"
                  onClick={() => {
                    setInput(p);
                    run(p);
                  }}
                >
                  {p.length > 34 ? p.slice(0, 32) + "…" : p}
                </button>
              ))}
            </div>
            <div className="lp-demo-run">
              <button type="button" className="lp-btn lp-btn--primary" onClick={() => run(input)}>
                <CrosshairSimple size={15} /> Route it
              </button>
              <span className="lp-demo-hint">
                {stage >= 4 && result ? `routed in 4 steps · ${result.reason}` : "⌘↵ to route"}
              </span>
            </div>
          </div>
        </div>

        <div className="lp-steps">
          {steps.map((s, i) => (
            <div key={s.n} className={`lp-step ${stage === i + 1 ? "is-active" : ""}`}>
              <span className="lp-step-n">{s.n}</span>
              <div>
                <div className="lp-step-label">{s.label}</div>
                <div className="lp-step-detail">{s.detail}</div>
              </div>
              {stage > i + 1 && <CheckCircle size={16} weight="fill" color="var(--accent-400)" />}
            </div>
          ))}
          <dl className="lp-summary">
            <div>
              <dt>response.model</dt>
              <dd className="lp-summary-auto">archer-auto</dd>
            </div>
            <div style={{ textAlign: "right" }}>
              <dt>served by</dt>
              <dd>{result && stage >= 3 && chosen ? chosen.model : "—"}</dd>
            </div>
          </dl>
        </div>
      </Reveal>
    </section>
  );
}

/** Walks the first three links of the chain on a 620ms timer: two rate limits,
 *  then a landing. Illustrative only — nothing here calls the backend. */
function FallbackChain() {
  const [step, setStep] = useState(-1);
  const [running, setRunning] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  useEffect(() => () => clearTimeout(timer.current), []);

  const run = () => {
    if (running) return;
    clearTimeout(timer.current);
    setRunning(true);
    setStep(0);
    const walk = (i: number) => {
      timer.current = setTimeout(() => {
        setStep(i);
        if (i >= 2) setRunning(false);
        else walk(i + 1);
      }, 620);
    };
    walk(1);
  };

  return (
    <section id="chain" className="lp-band">
      <div className="lp-wrap">
        <Reveal className="lp-band-head">
          <div style={{ maxWidth: "34em" }}>
            <span className="lp-eyebrow">Fallback chain</span>
            <h2 className="lp-h2">A miss never reaches you.</h2>
            <p className="lp-lede">
              Rate limit, server error or timeout, and Archer walks the chain until one model
              lands. Client errors stop it dead — a bad request fails the same way on every
              model.
            </p>
          </div>
          <button type="button" className="lp-btn lp-btn--onband" onClick={run}>
            <Lightning size={15} /> {running ? "walking the chain…" : "Simulate a rate limit"}
          </button>
        </Reveal>

        <Reveal className="lp-chain">
          {CHAIN.map((c, i) => {
            const failed = step >= 0 && i < Math.min(step, 2);
            const landed = step >= 2 && i === 2;
            return (
              <div
                key={c.name}
                className={`lp-chain-card ${failed ? "is-failed" : ""} ${landed ? "is-landed" : ""}`}
              >
                <div className="lp-chain-top">
                  <span>{String(i + 1).padStart(2, "0")}</span>
                  {failed && <span className="lp-chain-tag lp-chain-tag--fail">rate_limit</span>}
                  {landed && <span className="lp-chain-tag lp-chain-tag--ok">200 ok</span>}
                </div>
                <div className="lp-chain-name">{c.name}</div>
                <div className="lp-chain-provider">{c.provider}</div>
              </div>
            );
          })}
        </Reveal>
        <p className="lp-chain-note">
          {step >= 2
            ? "gpt-oss-120b and qwen3.6-27b returned rate_limit — retryable, so the chain advanced. gpt-oss-20b answered; the caller saw one 200 and the reason logged as coding_keywords_fallback."
            : "Order is the catalog's fallback_priority. The faster Groq models hold the head of the chain; the larger, slower Ollama Cloud models sit behind them."}
        </p>
      </div>
    </section>
  );
}

function ApiSection() {
  const [tab, setTab] = useState<Tab>("python");

  return (
    <section id="api" className="lp-wrap lp-section">
      <div className="lp-api">
        <Reveal>
          <span className="lp-eyebrow">Drop-in</span>
          <h2 className="lp-h2">Same code. New aim.</h2>
          <p className="lp-lede">
            If you&apos;ve called OpenAI, you&apos;ve already written Archer. Point the client
            at our base URL, use your key, and route.
          </p>
          <div className="lp-points">
            <div className="lp-point">
              <span className="lp-ico-chip">
                <Plug size={14} />
              </span>
              <div>
                <div className="lp-point-title">One endpoint</div>
                <div className="lp-point-body">
                  Swap the base URL. Nothing else in your call changes.
                </div>
              </div>
            </div>
            <div className="lp-point">
              <span className="lp-ico-chip">
                <Key size={14} />
              </span>
              <div>
                <div className="lp-point-title">One key</div>
                <div className="lp-point-body">
                  A single arch_sk_ key replaces the wallet of provider keys.
                </div>
              </div>
            </div>
            <div className="lp-point">
              <span className="lp-ico-chip">
                <Crosshair size={14} />
              </span>
              <div>
                <div className="lp-point-title">Zero model-picking</div>
                <div className="lp-point-body">
                  The model field is accepted, then ignored. Routing and fallback are automatic.
                </div>
              </div>
            </div>
          </div>
        </Reveal>

        <Reveal className="lp-code">
          <div className="lp-code-bar">
            {(Object.keys(SNIPPETS) as Tab[]).map((k) => (
              <button
                key={k}
                type="button"
                className={`lp-tab ${tab === k ? "is-on" : ""}`}
                onClick={() => setTab(k)}
              >
                {k}
              </button>
            ))}
            <span className="lp-code-file">{SNIPPETS[tab].file}</span>
          </div>
          <pre>
            <code>{SNIPPETS[tab].code}</code>
          </pre>
        </Reveal>
      </div>
    </section>
  );
}

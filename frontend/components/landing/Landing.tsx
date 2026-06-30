"use client";

import { useEffect, useRef } from "react";
import Link from "next/link";
import {
  Target,
  Repeat,
  Plug,
  KeyRound,
  ScrollText,
  Zap,
  ArrowRight,
} from "lucide-react";

import "./landing.css";
import { Reveal } from "./Reveal";
import { Mascot } from "./Mascot";
import { TargetShot } from "./TargetShot";
import { CodeBlock } from "./CodeBlock";

const MODELS = [
  { name: "llama-3.3-70b", provider: "Groq", best: "Coding, reasoning & the default shot" },
  { name: "gpt-oss-120b", provider: "Groq", best: "Math and hard, multi-step problems" },
  { name: "llama-3.1-8b", provider: "Groq", best: "Fast replies to short, simple asks" },
  { name: "qwen-2.5-72b", provider: "OpenRouter", best: "Analysis, comparison & deep dives" },
  { name: "gpt-oss-20b", provider: "Groq", best: "Writing and conversational turns" },
];

const FEATURES = [
  { Icon: Target, title: "Intent routing", body: "Each prompt is read and sent to the model that fits it — code, math, analysis, or a quick reply." },
  { Icon: Repeat, title: "Automatic fallback", body: "Rate-limited or down? Archer retries down a fixed chain until a model lands the shot." },
  { Icon: Plug, title: "OpenAI-compatible", body: "A drop-in /v1/chat/completions endpoint. Keep your SDK — just swap the base URL." },
  { Icon: KeyRound, title: "One key for all", body: "A single arch_sk_ key stands in for the wallet of provider keys you'd otherwise juggle." },
  { Icon: ScrollText, title: "Every shot logged", body: "See which model answered, why it routed there, plus tokens and latency, on your dashboard." },
  { Icon: Zap, title: "Normalized replies", body: "Whoever answers, the response always comes back in the same archer-auto shape." },
];

const CODE = `from openai import OpenAI

client = OpenAI(
    api_key="arch_sk_...",
    base_url="https://your-archer.app/v1",
)

resp = client.chat.completions.create(
    model="archer-auto",   # ignored — Archer picks
    messages=[{"role": "user",
               "content": "Write a binary search in Rust"}],
)
print(resp.choices[0].message.content)`;

export function Landing({ isAuthed }: { isAuthed: boolean }) {
  const targetRef = useRef<HTMLDivElement>(null);

  // Subtle scroll parallax on the hero target (skipped under reduced motion).
  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    let raf = 0;
    const onScroll = () => {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(() => {
        if (targetRef.current) {
          targetRef.current.style.transform = `translateY(${Math.min(window.scrollY * 0.05, 44)}px)`;
        }
      });
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => {
      window.removeEventListener("scroll", onScroll);
      cancelAnimationFrame(raf);
    };
  }, []);

  const primaryHref = isAuthed ? "/dashboard" : "/register";
  const primaryLabel = isAuthed ? "Open dashboard" : "Get your API key";

  return (
    <div className="lp">
      {/* nav */}
      <nav className="lp-nav">
        <div className="lp-wrap lp-nav-inner">
          <Link href="/" className="lp-brand">
            <Target size={20} color="#e9b949" strokeWidth={2.2} />
            ARCHER
          </Link>
          <div className="lp-nav-links">
            <a href="#shot">How it works</a>
            <a href="#models">Models</a>
            <a href="#api">API</a>
          </div>
          <div className="lp-nav-cta">
            {!isAuthed && (
              <Link href="/login" className="lp-signin">
                Sign in
              </Link>
            )}
            <Link href={primaryHref} className="lp-btn lp-btn--primary">
              {primaryLabel}
              <ArrowRight className="lp-arrow-ico" size={16} />
            </Link>
          </div>
        </div>
      </nav>

      {/* hero */}
      <header className="lp-hero">
        <div className="lp-wrap lp-hero-grid">
          <div>
            <span className="lp-eyebrow lp-rise lp-d1">Orchestration-as-a-Service</span>
            <h1 className="lp-h1 lp-display lp-rise lp-d2">
              Every prompt
              <br />
              finds <span className="lp-h1-em">its mark.</span>
            </h1>
            <p className="lp-sub lp-rise lp-d3">
              Archer is one OpenAI-compatible endpoint that routes each request to the
              model best suited for it. One key, no model-picking — every answer comes
              back as <code>archer-auto</code>.
            </p>
            <div className="lp-hero-cta lp-rise lp-d4">
              <Link href={primaryHref} className="lp-btn lp-btn--primary">
                {primaryLabel}
                <ArrowRight className="lp-arrow-ico" size={16} />
              </Link>
              <a href="#shot" className="lp-btn lp-btn--ghost">
                See how it routes
              </a>
            </div>
            <div className="lp-hero-meta lp-rise lp-d5">
              <span>
                <b>OpenAI-compatible</b> /v1
              </span>
              <span>
                <b>5</b> models, one target
              </span>
              <span>
                <b>Automatic</b> fallback
              </span>
            </div>
          </div>

          <div className="lp-target-stage">
            <div ref={targetRef} style={{ position: "relative", width: "100%", display: "grid", placeItems: "center" }}>
              <TargetShot />
              <Mascot className="lp-hero-mascot" />
            </div>
          </div>
        </div>
      </header>

      {/* the shot — 3 beats */}
      <section className="lp-section" id="shot">
        <div className="lp-wrap">
          <Reveal className="lp-section-head">
            <span className="lp-eyebrow">The shot</span>
            <h2 className="lp-h2 lp-display">Three movements, one release.</h2>
            <p className="lp-section-sub">
              A request travels like an arrow — nocked, aimed, loosed. Here is exactly
              what happens between your call and the answer.
            </p>
          </Reveal>

          <Reveal as="div" base="lp-shot-track">
            <div className="lp-beat">
              <div className="lp-beat-dot lp-display">01</div>
              <h3>Nock</h3>
              <p>
                You send a standard chat request — the same JSON you'd send OpenAI. Your{" "}
                <code>model</code> field is accepted, then ignored.
              </p>
            </div>
            <div className="lp-beat">
              <div className="lp-beat-dot lp-display">02</div>
              <h3>Aim</h3>
              <p>
                Archer reads the intent of your prompt and selects the model matched to
                it — coding, math, analysis, or a fast simple reply.
              </p>
            </div>
            <div className="lp-beat">
              <div className="lp-beat-dot lp-display">03</div>
              <h3>Loose</h3>
              <p>
                The chosen model answers. If it's rate-limited or errors, Archer falls
                through the chain until one lands — you never see the miss.
              </p>
            </div>
          </Reveal>
        </div>
      </section>

      <hr className="lp-rule" />

      {/* models */}
      <section className="lp-section" id="models">
        <div className="lp-wrap">
          <Reveal className="lp-section-head">
            <span className="lp-eyebrow">The quiver</span>
            <h2 className="lp-h2 lp-display">Five models. One target.</h2>
            <p className="lp-section-sub">
              A curated pool sits behind your key. You never pick from it — Archer draws
              the right one for every request.
            </p>
          </Reveal>

          <Reveal className="lp-models" base="lp-reveal lp-models">
            {MODELS.map((m) => (
              <div className="lp-model" key={m.name}>
                <p className="lp-model-provider">{m.provider}</p>
                <p className="lp-model-name lp-mono">{m.name}</p>
                <p className="lp-model-for">{m.best}</p>
              </div>
            ))}
          </Reveal>
          <p className="lp-models-note">
            Whoever answers, your response always comes back as <b>archer-auto</b>.
          </p>
        </div>
      </section>

      <hr className="lp-rule" />

      {/* api / code */}
      <section className="lp-section" id="api">
        <div className="lp-wrap">
          <Reveal className="lp-section-head">
            <span className="lp-eyebrow">The aim</span>
            <h2 className="lp-h2 lp-display">Same code. New aim.</h2>
            <p className="lp-section-sub">
              If you've called OpenAI, you've already written Archer. Point the client at
              our URL, use your key, and route.
            </p>
          </Reveal>

          <div className="lp-code-grid">
            <ul className="lp-code-points">
              <Reveal as="li">
                <strong>One endpoint</strong>
                <span>Aim your existing OpenAI client at Archer's base URL — that's the only change.</span>
              </Reveal>
              <Reveal as="li">
                <strong>One key</strong>
                <span>A single arch_sk_ key replaces every provider key you'd otherwise manage.</span>
              </Reveal>
              <Reveal as="li">
                <strong>Zero model-picking</strong>
                <span>The model field is ignored; routing and fallback are automatic.</span>
              </Reveal>
            </ul>

            <Reveal>
              <CodeBlock file="quickstart.py" copyText={CODE}>
                <span className="lp-tok-com">from</span> openai{" "}
                <span className="lp-tok-com">import</span> OpenAI{"\n\n"}
                client = <span className="lp-tok-fn">OpenAI</span>({"\n"}
                {"    "}api_key=<span className="lp-tok-str">&quot;arch_sk_...&quot;</span>,{"\n"}
                {"    "}base_url=<span className="lp-tok-str">&quot;https://your-archer.app/v1&quot;</span>,{"\n"}
                ){"\n\n"}
                resp = client.chat.completions.<span className="lp-tok-fn">create</span>({"\n"}
                {"    "}model=<span className="lp-tok-str">&quot;archer-auto&quot;</span>,{"   "}
                <span className="lp-tok-com"># ignored — Archer picks</span>
                {"\n"}
                {"    "}messages=[{"{"}<span className="lp-tok-str">&quot;role&quot;</span>:{" "}
                <span className="lp-tok-str">&quot;user&quot;</span>,{"\n"}
                {"               "}<span className="lp-tok-str">&quot;content&quot;</span>:{" "}
                <span className="lp-tok-str">&quot;Write a binary search in Rust&quot;</span>{"}"}],{"\n"}
                ){"\n"}
                <span className="lp-tok-fn">print</span>(resp.choices[<span className="lp-tok-key">0</span>].message.content)
              </CodeBlock>
            </Reveal>
          </div>
        </div>
      </section>

      <hr className="lp-rule" />

      {/* features */}
      <section className="lp-section">
        <div className="lp-wrap">
          <Reveal className="lp-section-head">
            <span className="lp-eyebrow">Why Archer</span>
            <h2 className="lp-h2 lp-display">Built to never miss.</h2>
          </Reveal>
          <Reveal className="lp-features" base="lp-reveal lp-features">
            {FEATURES.map(({ Icon, title, body }) => (
              <div className="lp-feature" key={title}>
                <Icon className="lp-feature-ico" strokeWidth={1.6} />
                <h3>{title}</h3>
                <p>{body}</p>
              </div>
            ))}
          </Reveal>
        </div>
      </section>

      {/* final cta */}
      <section className="lp-cta">
        <div className="lp-wrap">
          <Reveal>
            <Mascot className="lp-cta-mascot" />
            <h2 className="lp-display">Ready to let it fly?</h2>
            <p>
              Sign up, generate a key, and point your first request at Archer. The right
              model is already waiting on the line.
            </p>
            <div className="lp-cta-actions">
              <Link href={primaryHref} className="lp-btn lp-btn--primary">
                {primaryLabel}
                <ArrowRight className="lp-arrow-ico" size={16} />
              </Link>
              {!isAuthed && (
                <Link href="/login" className="lp-btn lp-btn--ghost">
                  Sign in
                </Link>
              )}
            </div>
          </Reveal>
        </div>
      </section>

      <footer className="lp-footer">
        <div className="lp-wrap lp-footer-inner">
          <span className="lp-brand">
            <Target size={16} color="#e9b949" strokeWidth={2.2} />
            ARCHER
          </span>
          <span>Orchestration-as-a-Service · routes every prompt to its best model.</span>
          <span>© {new Date().getFullYear()} Archer</span>
        </div>
      </footer>
    </div>
  );
}

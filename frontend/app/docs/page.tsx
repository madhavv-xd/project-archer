import type { Metadata } from "next";
import Link from "next/link";
import { Target } from "lucide-react";

import { DocsCodeBlock } from "@/components/docs/DocsCodeBlock";

export const metadata: Metadata = {
  title: "Docs — Archer",
  description: "Quickstart, SDK examples, streaming, rate limits, and the model catalog.",
};

const BASE_URL = "https://api.project-archer.online/v1";

// NOTE: static catalog table — not fetched (GET /v1/models only exposes the
// virtual `archer-auto` entry by design). Keep in sync BY HAND with the active
// rows of the latest catalog migration (backend/alembic/versions/007_*.py).
const CATALOG = [
  { name: "GPT-OSS 120B", speed: "fast", ctx: "131K" },
  { name: "Qwen3.6 27B", speed: "fast", ctx: "131K" },
  { name: "GPT-OSS 20B", speed: "very fast", ctx: "131K" },
  { name: "Nemotron 3 Nano 30B", speed: "fast", ctx: "131K" },
  { name: "Nemotron 3 Ultra", speed: "medium", ctx: "262K" },
  { name: "Nemotron 3 Super", speed: "medium", ctx: "262K" },
  { name: "MiniMax M3", speed: "medium", ctx: "524K" },
  { name: "Gemma 4 31B", speed: "slow", ctx: "131K" },
];

const CURL = `curl ${BASE_URL}/chat/completions \\
  -H "Authorization: Bearer arch_sk_..." \\
  -H "Content-Type: application/json" \\
  -d '{
    "model": "archer-auto",
    "messages": [{"role": "user", "content": "Write a binary search in Rust"}]
  }'`;

const PYTHON = `from openai import OpenAI

client = OpenAI(
    api_key="arch_sk_...",
    base_url="${BASE_URL}",
)

resp = client.chat.completions.create(
    model="archer-auto",  # accepted but ignored — Archer routes for you
    messages=[{"role": "user", "content": "Write a binary search in Rust"}],
)
print(resp.choices[0].message.content)`;

const JS = `import OpenAI from "openai";

const client = new OpenAI({
  apiKey: "arch_sk_...",
  baseURL: "${BASE_URL}",
});

const resp = await client.chat.completions.create({
  model: "archer-auto", // accepted but ignored — Archer routes for you
  messages: [{ role: "user", content: "Write a binary search in Rust" }],
});
console.log(resp.choices[0].message.content);`;

const STREAM = `stream = client.chat.completions.create(
    model="archer-auto",
    messages=[{"role": "user", "content": "Explain quicksort"}],
    stream=True,
)
for chunk in stream:
    print(chunk.choices[0].delta.content or "", end="")`;

const ERROR_429 = `{
  "error": {
    "message": "Rate limit exceeded. Try again in 12s.",
    "type": "rate_limit_error",
    "code": "rate_limit_exceeded"
  }
}`;

/** Inline literal — key prefixes, header names, JSON fields. The same five
 *  classes were repeated at fourteen call sites on this page. */
function C({ children }: { children: React.ReactNode }) {
  return (
    <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-[0.9em] text-foreground">
      {children}
    </code>
  );
}

function Section({
  id,
  title,
  children,
}: {
  id: string;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section id={id} className="scroll-mt-20">
      <h2 className="font-display text-title">{title}</h2>
      <div className="mt-4 space-y-4 text-body text-muted-foreground">{children}</div>
    </section>
  );
}

export default function DocsPage() {
  return (
    <div className="min-h-full">
      <header className="sticky top-0 z-10 border-b border-border bg-background/80 backdrop-blur">
        <div className="mx-auto flex max-w-3xl items-center justify-between px-gutter py-4">
          <Link href="/" className="flex items-center gap-2 font-display font-bold">
            <Target size={18} className="text-primary" strokeWidth={2.2} />
            ARCHER
          </Link>
          <Link
            href="/register"
            className="rounded-lg bg-primary px-3 py-1.5 text-body-sm font-medium text-primary-foreground transition-colors hover:bg-accent-foreground"
          >
            Get your API key
          </Link>
        </div>
      </header>

      {/* space-y-12, not spacing-section: that token is landing-scale (64-128px)
          and these sections are short — a document reads tighter than a pitch. */}
      <main className="mx-auto max-w-3xl space-y-12 px-gutter py-12">
        <div>
          <h1 className="font-display text-display">Docs</h1>
          <p className="mt-4 text-lead text-muted-foreground">
            Archer is an OpenAI-compatible endpoint. Point any OpenAI client at{" "}
            <C>{BASE_URL}</C>,
            use your <C>arch_sk_</C>{" "}
            key, and every request is routed to the model best suited for it. The{" "}
            <C>model</C> field is
            accepted but ignored — every response comes back as{" "}
            <C>archer-auto</C>.
          </p>
        </div>

        <Section id="quickstart" title="Quickstart">
          <ol className="list-decimal space-y-2 pl-5">
            <li>
              <Link href="/register" className="text-primary hover:underline">
                Register
              </Link>{" "}
              for an account.
            </li>
            <li>
              Create an API key on the{" "}
              <Link href="/api-keys" className="text-primary hover:underline">
                API Keys
              </Link>{" "}
              page — copy it once; it starts with{" "}
              <C>arch_sk_</C>.
            </li>
            <li>Make your first call with the examples below.</li>
          </ol>
        </Section>

        <Section id="curl" title="curl">
          <DocsCodeBlock code={CURL} lang="shell" />
        </Section>

        <Section id="python" title="Python (OpenAI SDK)">
          <DocsCodeBlock code={PYTHON} lang="python" />
        </Section>

        <Section id="javascript" title="JavaScript / TypeScript (OpenAI SDK)">
          <DocsCodeBlock code={JS} lang="javascript" />
        </Section>

        <Section id="streaming" title="Streaming">
          <p>
            Pass <C>stream: true</C>{" "}
            to receive OpenAI-format server-sent events, terminated by{" "}
            <C>data: [DONE]</C>.
          </p>
          <DocsCodeBlock code={STREAM} lang="python" />
        </Section>

        <Section id="rate-limits" title="Rate limits & quotas">
          <p>
            Every <C>/v1/*</C>{" "}
            response carries rate-limit headers:
          </p>
          <ul className="list-disc space-y-1 pl-5">
            <li>
              <C>
                X-RateLimit-Limit-Requests
              </C>{" "}
              — per-minute request limit
            </li>
            <li>
              <C>
                X-RateLimit-Remaining-Requests
              </C>{" "}
              — requests left in the current window
            </li>
            <li>
              <C>
                X-RateLimit-Reset-Requests
              </C>{" "}
              — seconds until the window resets
            </li>
          </ul>
          <p>
            Exceed a limit and you get a{" "}
            <C>429</C> with a{" "}
            <C>Retry-After</C>{" "}
            header (seconds) and this body:
          </p>
          <DocsCodeBlock code={ERROR_429} lang="json" />
        </Section>

        <Section id="models" title="Model catalog">
          <p>
            You never pick from these — Archer draws the right one per request. Listed for
            reference only; the API always presents a single{" "}
            <C>archer-auto</C>{" "}
            model.
          </p>
          <div className="overflow-x-auto rounded-lg border border-border">
            <table className="w-full text-body-sm">
              <thead className="border-b border-border text-left text-caption tracking-wide text-muted-foreground uppercase">
                <tr>
                  <th className="px-4 py-2.5 font-medium">Model</th>
                  <th className="px-4 py-2.5 font-medium">Speed</th>
                  <th className="px-4 py-2.5 font-medium">Context</th>
                </tr>
              </thead>
              <tbody>
                {CATALOG.map((m) => (
                  <tr key={m.name} className="border-b border-border last:border-0">
                    <td className="px-4 py-2.5 font-mono text-foreground">{m.name}</td>
                    <td className="px-4 py-2.5">{m.speed}</td>
                    <td className="px-4 py-2.5 font-mono">{m.ctx}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Section>
      </main>
    </div>
  );
}

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
// virtual `archer-auto` entry by design). Keep in sync BY HAND when the model
// seed migrations change (backend/alembic/versions/*_expand_catalog.py).
const CATALOG = [
  { name: "Llama 3.3 70B", speed: "fast", ctx: "128K" },
  { name: "Llama 3.1 8B", speed: "very fast", ctx: "128K" },
  { name: "GPT-OSS 120B", speed: "fast", ctx: "131K" },
  { name: "GPT-OSS 20B", speed: "very fast", ctx: "131K" },
  { name: "Llama 4 Scout 17B", speed: "fast", ctx: "131K" },
  { name: "Qwen3 Coder 480B", speed: "medium", ctx: "262K" },
  { name: "GLM 4.7", speed: "medium", ctx: "203K" },
  { name: "MiniMax M3", speed: "medium", ctx: "524K" },
  { name: "Nemotron 3 Super", speed: "medium", ctx: "262K" },
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
      <h2 className="font-display text-2xl font-bold tracking-tight">{title}</h2>
      <div className="mt-4 space-y-4 text-sm leading-relaxed text-muted-foreground">
        {children}
      </div>
    </section>
  );
}

export default function DocsPage() {
  return (
    <div className="min-h-full">
      <header className="sticky top-0 z-10 border-b border-border bg-background/80 backdrop-blur">
        <div className="mx-auto flex max-w-3xl items-center justify-between px-6 py-4">
          <Link href="/" className="flex items-center gap-2 font-display font-bold">
            <Target size={18} color="#e9b949" strokeWidth={2.2} />
            ARCHER
          </Link>
          <Link
            href="/register"
            className="rounded-lg bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground"
          >
            Get your API key
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-3xl space-y-12 px-6 py-12">
        <div>
          <h1 className="font-display text-4xl font-bold tracking-tight">Docs</h1>
          <p className="mt-3 text-muted-foreground">
            Archer is an OpenAI-compatible endpoint. Point any OpenAI client at{" "}
            <code className="rounded bg-muted px-1.5 py-0.5 text-foreground">{BASE_URL}</code>,
            use your <code className="rounded bg-muted px-1.5 py-0.5 text-foreground">arch_sk_</code>{" "}
            key, and every request is routed to the model best suited for it. The{" "}
            <code className="rounded bg-muted px-1.5 py-0.5 text-foreground">model</code> field is
            accepted but ignored — every response comes back as{" "}
            <code className="rounded bg-muted px-1.5 py-0.5 text-foreground">archer-auto</code>.
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
              <code className="rounded bg-muted px-1.5 py-0.5 text-foreground">arch_sk_</code>.
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
            Pass <code className="rounded bg-muted px-1.5 py-0.5 text-foreground">stream: true</code>{" "}
            to receive OpenAI-format server-sent events, terminated by{" "}
            <code className="rounded bg-muted px-1.5 py-0.5 text-foreground">data: [DONE]</code>.
          </p>
          <DocsCodeBlock code={STREAM} lang="python" />
        </Section>

        <Section id="rate-limits" title="Rate limits & quotas">
          <p>
            Every <code className="rounded bg-muted px-1.5 py-0.5 text-foreground">/v1/*</code>{" "}
            response carries rate-limit headers:
          </p>
          <ul className="list-disc space-y-1 pl-5">
            <li>
              <code className="rounded bg-muted px-1.5 py-0.5 text-foreground">
                X-RateLimit-Limit-Requests
              </code>{" "}
              — per-minute request limit
            </li>
            <li>
              <code className="rounded bg-muted px-1.5 py-0.5 text-foreground">
                X-RateLimit-Remaining-Requests
              </code>{" "}
              — requests left in the current window
            </li>
            <li>
              <code className="rounded bg-muted px-1.5 py-0.5 text-foreground">
                X-RateLimit-Reset-Requests
              </code>{" "}
              — seconds until the window resets
            </li>
          </ul>
          <p>
            Exceed a limit and you get a{" "}
            <code className="rounded bg-muted px-1.5 py-0.5 text-foreground">429</code> with a{" "}
            <code className="rounded bg-muted px-1.5 py-0.5 text-foreground">Retry-After</code>{" "}
            header (seconds) and this body:
          </p>
          <DocsCodeBlock code={ERROR_429} lang="json" />
        </Section>

        <Section id="models" title="Model catalog">
          <p>
            You never pick from these — Archer draws the right one per request. Listed for
            reference only; the API always presents a single{" "}
            <code className="rounded bg-muted px-1.5 py-0.5 text-foreground">archer-auto</code>{" "}
            model.
          </p>
          <div className="overflow-x-auto rounded-lg border border-border">
            <table className="w-full text-sm">
              <thead className="border-b border-border text-left text-muted-foreground">
                <tr>
                  <th className="px-4 py-2 font-medium">Model</th>
                  <th className="px-4 py-2 font-medium">Speed</th>
                  <th className="px-4 py-2 font-medium">Context</th>
                </tr>
              </thead>
              <tbody>
                {CATALOG.map((m) => (
                  <tr key={m.name} className="border-b border-border last:border-0">
                    <td className="px-4 py-2 font-mono text-foreground">{m.name}</td>
                    <td className="px-4 py-2">{m.speed}</td>
                    <td className="px-4 py-2">{m.ctx}</td>
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

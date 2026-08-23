"use client";

import { useEffect, useRef, useState } from "react";
import { useSession } from "next-auth/react";
import { Brain, CaretRight, PaperPlaneRight } from "@phosphor-icons/react";

import { api } from "@/lib/api";
import { Header } from "@/components/layout/Header";
import { Markdown } from "@/components/playground/Markdown";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { Model } from "@/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// Floor for the typing-speed reveal (see `send`). The reveal is only cosmetic:
// a fast provider hands fetch one coalesced chunk, so painting per-token would
// batch into a single frame. But a *fixed* rate makes a long reply that already
// arrived take len/rate seconds to finish — so the rate also scales with the
// backlog, clearing whatever is outstanding within CATCHUP_SECONDS.
const REVEAL_CHARS_PER_SEC = 55;
const CATCHUP_SECONDS = 1.5;

type Effort = "low" | "medium" | "high";

type Meta = {
  model: string | null;
  routing_reason: string | null;
  fallback_used: boolean;
  time_to_first_token_ms: number | null;
  total_tokens: number | null;
};

type Msg = {
  id: string;
  role: "user" | "assistant";
  content: string;
  reasoning?: string;
  meta?: Meta;
};

export default function PlaygroundPage() {
  const { data: session } = useSession();
  const token = session?.accessToken;
  const [models, setModels] = useState<Model[]>([]);
  const [selectedModel, setSelectedModel] = useState("archer-auto");
  const [reasoning, setReasoning] = useState(false);
  const [effort, setEffort] = useState<Effort>("medium");
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Msg[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!token) return;
    api.models(token).then((list) => setModels(list.filter((m) => m.is_active)));
  }, [token]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [messages]);

  // Effort only means something where the answering model can grade it. For
  // archer-auto the model isn't known until after routing, so leave it enabled.
  const picked = models.find((m) => m.name === selectedModel);
  const effortApplies = !picked || picked.reasoning_mode === "effort" || picked.reasoning_mode === "effort_optional";

  async function send() {
    if (!input.trim() || busy || !token) return;
    setError(null);
    const userMsg: Msg = { id: crypto.randomUUID(), role: "user", content: input.trim() };
    const history = [...messages, userMsg];
    const assistantId = crypto.randomUUID();
    setMessages([...history, { id: assistantId, role: "assistant", content: "" }]);
    setInput("");
    setBusy(true);

    const patch = (fields: Partial<Msg>) =>
      setMessages((prev) => {
        const next = [...prev];
        next[next.length - 1] = { ...next[next.length - 1], ...fields };
        return next;
      });

    // The reader fills `full`; this loop paints it. Decoupled so the pace is
    // ours, not the provider's chunk boundaries'.
    let full = "";
    let shown = 0;
    let streaming = true;
    let lastTick = performance.now();
    const pacer = (async () => {
      while (streaming || shown < full.length) {
        const now = performance.now();
        const dt = (now - lastTick) / 1000;
        lastTick = now;
        if (shown < full.length) {
          const backlog = full.length - shown;
          const rate = Math.max(REVEAL_CHARS_PER_SEC, backlog / CATCHUP_SECONDS);
          shown = Math.min(full.length, shown + rate * dt);
          patch({ content: full.slice(0, Math.floor(shown)) });
        }
        await new Promise((r) => requestAnimationFrame(r));
      }
    })();

    try {
      const res = await fetch(`${API_URL}/v1/playground/chat/completions`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          model: selectedModel,
          messages: history.map((m) => ({ role: m.role, content: m.content })),
          stream: true,
          reasoning,
          reasoning_effort: effort,
        }),
      });
      if (res.status === 429) {
        const retry = res.headers.get("Retry-After");
        const code = (await res.json().catch(() => null))?.error?.code;
        throw new Error(
          code === "monthly_quota_exceeded"
            ? "You've used up your monthly quota — it resets on the 1st."
            : `You're sending requests too fast.${retry ? ` Try again in ${retry}s.` : ""}`,
        );
      }
      if (!res.ok || !res.body) {
        const detail = await res.json().catch(() => null);
        throw new Error(detail?.error?.message ?? detail?.detail ?? `Request failed (${res.status})`);
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let thoughts = "";
      let meta: Meta | undefined;
      let done = false;
      while (!done) {
        const { done: streamDone, value } = await reader.read();
        if (streamDone) break;
        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split("\n\n");
        buffer = parts.pop() ?? "";
        for (const part of parts) {
          const line = part.trim();
          if (!line.startsWith("data:")) continue;
          const data = line.slice(5).trim();
          if (data === "[DONE]") {
            done = true;
            break;
          }
          try {
            const obj = JSON.parse(data);
            // The playground endpoint closes with one archer.metadata line
            // naming the model that actually served the request — the public
            // /v1 stream never carries it.
            if (obj.archer) {
              meta = obj.archer;
              continue;
            }
            const delta = obj.choices?.[0]?.delta;
            if (delta?.reasoning) {
              thoughts += delta.reasoning;
              patch({ reasoning: thoughts });
            }
            if (delta?.content) full += delta.content;
          } catch {
            /* skip malformed chunk */
          }
        }
      }
      streaming = false;
      await pacer; // let the reveal catch up to the full text
      patch({ content: full, meta });
    } catch (e) {
      streaming = false;
      await pacer; // stop it writing before we remove the bubble
      setError(e instanceof Error ? e.message : "Something went wrong");
      setMessages((prev) => prev.slice(0, -1)); // drop the empty assistant bubble
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <Header title="Playground" subtitle="Watch a request route and stream, live." />
      <main className="flex flex-1 flex-col overflow-hidden p-gutter">
        <div className="mb-3 flex flex-wrap items-center gap-x-3 gap-y-2">
          <span id="model-label" className="font-mono text-label uppercase text-(--neutral-600)">
            Model
          </span>
          <Select value={selectedModel} onValueChange={setSelectedModel} disabled={busy}>
            <SelectTrigger aria-labelledby="model-label" className="w-[248px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="archer-auto">archer-auto · let the router pick</SelectItem>
              {models.map((m) => (
                <SelectItem key={m.id} value={m.name}>
                  {m.display_name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <button
            type="button"
            onClick={() => setReasoning((r) => !r)}
            disabled={busy}
            aria-pressed={reasoning}
            title={
              reasoning
                ? "The model reasons before answering — slower, shown separately."
                : "Answer straight away. Reasoning tokens are most of the latency."
            }
            className={`flex h-8 items-center gap-1.5 rounded-full border px-3 font-mono text-caption transition-colors outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/15 disabled:cursor-not-allowed disabled:opacity-50 ${
              reasoning
                ? "border-(--accent-800) bg-primary/15 text-(--accent-300)"
                : "border-(--neutral-800) text-(--neutral-500) hover:text-foreground"
            }`}
          >
            <Brain size={13} weight={reasoning ? "fill" : "regular"} />
            think {reasoning ? "on" : "off"}
          </button>

          {reasoning && (
            <Select
              value={effort}
              onValueChange={(v) => setEffort(v as Effort)}
              disabled={busy || !effortApplies}
            >
              <SelectTrigger
                aria-label="Reasoning effort"
                className="w-[124px]"
                title={
                  effortApplies
                    ? "How much the model deliberates."
                    : `${picked?.display_name} can only switch thinking on or off.`
                }
              >
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="low">low effort</SelectItem>
                <SelectItem value="medium">medium effort</SelectItem>
                <SelectItem value="high">high effort</SelectItem>
              </SelectContent>
            </Select>
          )}

          <span className="ml-auto hidden font-mono text-caption text-(--neutral-600) sm:block">
            POST /v1/chat/completions
          </span>
        </div>

        <div
          ref={scrollRef}
          className="flex-1 space-y-4 overflow-y-auto rounded-lg border border-border bg-card p-4"
        >
          {messages.length === 0 && (
            <EmptyState
              icon={PaperPlaneRight}
              title="Send a message and watch Archer route it."
              hint="The real model that answered shows up under each reply."
            />
          )}
          {messages.map((m) => {
            const live =
              busy && m.id === messages[messages.length - 1]?.id && m.role === "assistant";
            return (
              <div
                key={m.id}
                className={m.role === "user" ? "flex justify-end" : "flex justify-start"}
              >
                <div
                  className={
                    m.role === "user"
                      ? "max-w-[76%] rounded-[14px] rounded-br-[4px] border border-(--accent-800) bg-primary/15 px-3 py-2 text-body-sm"
                      : "max-w-[86%] rounded-[14px] rounded-bl-[4px] border border-(--neutral-800) bg-[rgba(22,24,38,.75)] px-3 py-2 text-body-sm"
                  }
                >
                  {m.role === "user" ? (
                    <p className="whitespace-pre-wrap">{m.content}</p>
                  ) : (
                    <>
                      {m.reasoning && <ReasoningPanel text={m.reasoning} open={live && !m.content} />}
                      {m.content ? (
                        <>
                          <Markdown>{m.content}</Markdown>
                          {live && <span className="stream-cursor" aria-hidden />}
                        </>
                      ) : (
                        /* Before the first token there is nothing to put a
                           caret after — a bare blinking block just reads as a
                           glitch. Say what is happening instead. */
                        live && <Working label={m.reasoning ? "thinking" : "routing"} />
                      )}
                    </>
                  )}
                  {m.role === "assistant" && m.meta && <MetaRow meta={m.meta} />}
                </div>
              </div>
            );
          })}
        </div>

        {error && (
          <p role="alert" className="mt-2 text-body-sm text-destructive">
            {error}
          </p>
        )}

        <div className="mt-3 flex gap-2">
          <textarea
            rows={2}
            placeholder="Ask anything — code, math, a quick question… (Shift+Enter for a new line)"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                send();
              }
            }}
            disabled={busy}
            className="w-full resize-none rounded-[10px] border border-(--neutral-800) bg-background px-3 py-2 text-sm transition-colors outline-none placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/15 disabled:cursor-not-allowed disabled:opacity-50"
          />
          <Button onClick={send} disabled={busy || !input.trim()} className="self-end">
            <PaperPlaneRight size={16} />
            Send
          </Button>
        </div>
      </main>
    </>
  );
}

function Working({ label }: { label: string }) {
  return (
    <p className="flex items-center gap-2 font-mono text-caption text-(--neutral-500)">
      <span className="stream-pulse" aria-hidden />
      {label}…
    </p>
  );
}

function ReasoningPanel({ text, open }: { text: string; open: boolean }) {
  return (
    <details open={open} className="group mb-2 rounded-[8px] border border-(--neutral-800) bg-background/40">
      <summary className="flex cursor-pointer list-none items-center gap-1.5 px-2 py-1 font-mono text-caption text-(--neutral-500) hover:text-foreground">
        <CaretRight size={11} className="transition-transform group-open:rotate-90" />
        thinking
      </summary>
      <p className="max-h-48 overflow-y-auto px-2 pb-2 text-caption whitespace-pre-wrap text-(--neutral-500)">
        {text}
      </p>
    </details>
  );
}

function MetaRow({ meta }: { meta: Meta }) {
  return (
    <div className="mt-2 flex flex-wrap items-center gap-1.5 border-t border-[rgba(233,233,237,.06)] pt-2 text-caption">
      <span className="rounded-[6px] bg-primary/10 px-1.5 py-0.5 text-(--accent-300)">
        answered by <span className="font-mono">{meta.model ?? "unknown"}</span>
        {meta.fallback_used ? " (fallback)" : ""}
      </span>
      {meta.routing_reason && (
        <span className="rounded-[6px] border border-border px-1.5 py-0.5 font-mono text-(--neutral-500)">
          {meta.routing_reason}
        </span>
      )}
      {meta.time_to_first_token_ms != null && (
        <span className="rounded-[6px] border border-border px-1.5 py-0.5 font-mono text-(--neutral-500)">
          ttft {meta.time_to_first_token_ms}ms
        </span>
      )}
      {meta.total_tokens != null && (
        <span className="rounded-[6px] border border-border px-1.5 py-0.5 font-mono text-(--neutral-500)">
          {meta.total_tokens} tok
        </span>
      )}
    </div>
  );
}

"use client";

import { useEffect, useRef, useState } from "react";
import { useSession } from "next-auth/react";
import { PaperPlaneRight } from "@phosphor-icons/react";

import { api } from "@/lib/api";
import { Header } from "@/components/layout/Header";
import { Markdown } from "@/components/playground/Markdown";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import type { Model } from "@/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// Typing-speed reveal for the synthetic streaming effect (see `send` below) —
// independent of how fast the upstream provider actually responds.
const REVEAL_CHARS_PER_SEC = 55;

type Msg = {
  id: string;
  role: "user" | "assistant";
  content: string;
  model?: string; // real routed model, resolved from /logs after streaming
  fallback?: boolean;
  resolving?: boolean;
  routingReason?: string;
  ttftMs?: number | null;
  totalTokens?: number | null;
};

// Read the served model + metadata back from the just-written log row. The log
// write is fire-and-forget, so retry once if the newest row predates our send.
async function resolveModel(token: string, sentAt: number) {
  for (let attempt = 0; attempt < 2; attempt++) {
    const { items } = await api.logs(token, 1, 1);
    const row = items[0];
    if (row && new Date(row.created_at).getTime() >= sentAt - 2000) {
      return {
        model: row.model ?? "unknown",
        fallback: row.fallback_used,
        routingReason: row.routing_reason,
        ttftMs: row.time_to_first_token_ms,
        totalTokens: row.total_tokens,
      };
    }
    await new Promise((r) => setTimeout(r, 400));
  }
  return null;
}

export default function PlaygroundPage() {
  const { data: session } = useSession();
  const token = session?.accessToken;
  const [models, setModels] = useState<Model[]>([]);
  const [selectedModel, setSelectedModel] = useState("archer-auto");
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

  async function send() {
    if (!input.trim() || busy || !token) return;
    setError(null);
    const userMsg: Msg = { id: crypto.randomUUID(), role: "user", content: input.trim() };
    const history = [...messages, userMsg];
    const assistantId = crypto.randomUUID();
    setMessages([...history, { id: assistantId, role: "assistant", content: "" }]);
    setInput("");
    setBusy(true);
    const sentAt = Date.now();

    const setAssistant = (content: string, extra: Partial<Msg> = {}) =>
      setMessages((prev) => {
        const next = [...prev];
        next[next.length - 1] = { id: assistantId, role: "assistant", content, ...extra };
        return next;
      });

    // A fast upstream (Groq) is delivered by fetch as one coalesced chunk, so
    // reacting per-token would batch into a single paint. Decouple the reveal:
    // the reader just fills `full`; this loop paints it at a constant typing
    // pace (REVEAL_CHARS_PER_SEC) regardless of how fast the provider replied.
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
          shown = Math.min(full.length, shown + REVEAL_CHARS_PER_SEC * dt);
          setAssistant(full.slice(0, Math.floor(shown)));
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
            const delta = JSON.parse(data).choices?.[0]?.delta?.content;
            if (delta) full += delta;
          } catch {
            /* skip malformed chunk */
          }
        }
      }
      streaming = false;
      await pacer; // let the reveal catch up to the full text

      // Reveal the real routed model once the log row lands.
      setAssistant(full, { resolving: true });
      const resolved = await resolveModel(token, sentAt);
      setAssistant(full, resolved ?? { model: undefined });
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
        <div className="mb-3 flex items-center gap-3">
          <label
            htmlFor="model-select"
            className="font-mono text-label uppercase text-(--neutral-600)"
          >
            Model
          </label>
          <select
            id="model-select"
            value={selectedModel}
            onChange={(e) => setSelectedModel(e.target.value)}
            disabled={busy}
            className="h-8 rounded-full border border-(--accent-800) bg-primary/10 px-3 font-mono text-caption text-(--accent-300) outline-none focus-visible:border-ring"
          >
            <option value="archer-auto">archer-auto · let the router pick</option>
            {models.map((m) => (
              <option key={m.id} value={m.name}>
                {m.display_name}
              </option>
            ))}
          </select>
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
            // The last assistant bubble is "live" (gets the cursor) until the
            // model reveal starts — the one piece of motion the product shell
            // allows (design.md motion budget).
            const streaming =
              busy &&
              m.id === messages[messages.length - 1]?.id &&
              m.role === "assistant" &&
              !m.resolving &&
              !m.model;
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
                  ) : m.content ? (
                    <Markdown>{m.content}</Markdown>
                  ) : !streaming ? (
                    <p className="text-muted-foreground">…</p>
                  ) : null}
                  {streaming && <span className="stream-cursor" aria-hidden />}
                  {m.role === "assistant" && (m.resolving || m.model) && (
                    <div className="mt-2 flex flex-wrap items-center gap-1.5 border-t border-[rgba(233,233,237,.06)] pt-2 text-caption">
                      {m.resolving && !m.model ? (
                        <span className="text-muted-foreground">confirming model…</span>
                      ) : (
                        <>
                          <span className="rounded-[6px] bg-primary/10 px-1.5 py-0.5 text-(--accent-300)">
                            answered by <span className="font-mono">{m.model}</span>
                            {m.fallback ? " (fallback)" : ""}
                          </span>
                          {m.routingReason && (
                            <span className="rounded-[6px] border border-border px-1.5 py-0.5 font-mono text-(--neutral-500)">
                              {m.routingReason}
                            </span>
                          )}
                          {m.ttftMs != null && (
                            <span className="rounded-[6px] border border-border px-1.5 py-0.5 font-mono text-(--neutral-500)">
                              ttft {m.ttftMs}ms
                            </span>
                          )}
                          {m.totalTokens != null && (
                            <span className="rounded-[6px] border border-border px-1.5 py-0.5 font-mono text-(--neutral-500)">
                              {m.totalTokens} tok
                            </span>
                          )}
                        </>
                      )}
                    </div>
                  )}
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

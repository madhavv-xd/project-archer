"use client";

import { useEffect, useRef, useState } from "react";
import { useSession } from "next-auth/react";
import Link from "next/link";
import { KeyRound, Send } from "lucide-react";

import { api } from "@/lib/api";
import { Header } from "@/components/layout/Header";
import { Markdown } from "@/components/playground/Markdown";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type Msg = {
  role: "user" | "assistant";
  content: string;
  model?: string; // real routed model, resolved from /logs after streaming
  fallback?: boolean;
  resolving?: boolean;
};

// Read the served model + fallback back from the just-written log row. The log
// write is fire-and-forget, so retry once if the newest row predates our send.
async function resolveModel(token: string, sentAt: number) {
  for (let attempt = 0; attempt < 2; attempt++) {
    const { items } = await api.logs(token, 1, 1);
    const row = items[0];
    if (row && new Date(row.created_at).getTime() >= sentAt - 2000) {
      return { model: row.model ?? "unknown", fallback: row.fallback_used };
    }
    await new Promise((r) => setTimeout(r, 400));
  }
  return null;
}

export default function PlaygroundPage() {
  const { data: session } = useSession();
  const token = session?.accessToken;
  const [hasKeys, setHasKeys] = useState<boolean | null>(null);
  const [apiKey, setApiKey] = useState("");
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Msg[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!token) return;
    api.listKeys(token).then((keys) => setHasKeys(keys.length > 0));
  }, [token]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [messages]);

  async function send() {
    if (!input.trim() || !apiKey.trim() || busy || !token) return;
    setError(null);
    const userMsg: Msg = { role: "user", content: input.trim() };
    const history = [...messages, userMsg];
    setMessages([...history, { role: "assistant", content: "" }]);
    setInput("");
    setBusy(true);
    const sentAt = Date.now();

    const setAssistant = (content: string, extra: Partial<Msg> = {}) =>
      setMessages((prev) => {
        const next = [...prev];
        next[next.length - 1] = { role: "assistant", content, ...extra };
        return next;
      });

    // A fast upstream (Groq) is delivered by fetch as one coalesced chunk, so
    // reacting per-token would batch into a single paint. Decouple the reveal:
    // the reader just fills `full`; this loop paints a slice of it per frame,
    // draining any backlog so the reply always appears token-by-token.
    let full = "";
    let shown = 0;
    let streaming = true;
    const pacer = (async () => {
      while (streaming || shown < full.length) {
        if (shown < full.length) {
          shown += Math.max(2, Math.ceil((full.length - shown) / 10));
          setAssistant(full.slice(0, shown));
        }
        await new Promise((r) => requestAnimationFrame(r));
      }
    })();

    try {
      const res = await fetch(`${API_URL}/v1/chat/completions`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${apiKey.trim()}`,
        },
        body: JSON.stringify({
          model: "archer-auto",
          messages: history.map((m) => ({ role: m.role, content: m.content })),
          stream: true,
        }),
      });
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
      setAssistant(full, { model: resolved?.model, fallback: resolved?.fallback });
    } catch (e) {
      streaming = false;
      await pacer; // stop it writing before we remove the bubble
      setError(e instanceof Error ? e.message : "Something went wrong");
      setMessages((prev) => prev.slice(0, -1)); // drop the empty assistant bubble
    } finally {
      setBusy(false);
    }
  }

  if (hasKeys === false) {
    return (
      <>
        <Header title="Playground" subtitle="Watch a request route and stream, live." />
        <main className="flex flex-1 items-center justify-center p-6">
          <Card className="max-w-md text-center">
            <CardContent className="p-8">
              <KeyRound className="mx-auto size-8 text-primary" />
              <h2 className="mt-4 font-display text-lg font-semibold">You need an API key</h2>
              <p className="mt-2 text-sm text-muted-foreground">
                The playground sends real requests with your own key. Create one to get started.
              </p>
              <Link href="/api-keys" className="mt-4 inline-block">
                <Button>Create an API key</Button>
              </Link>
            </CardContent>
          </Card>
        </main>
      </>
    );
  }

  return (
    <>
      <Header title="Playground" subtitle="Watch a request route and stream, live." />
      <main className="flex flex-1 flex-col overflow-hidden p-6">
        <div className="mb-3">
          <Input
            type="password"
            placeholder="Paste an arch_sk_ key (shown once at creation, not retrievable here)"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            className="font-mono"
          />
        </div>

        <div
          ref={scrollRef}
          className="flex-1 space-y-4 overflow-y-auto rounded-lg border border-border bg-card p-4"
        >
          {messages.length === 0 && (
            <p className="py-12 text-center text-sm text-muted-foreground">
              Send a message and watch Archer route it — the real model that answered shows up
              under each reply.
            </p>
          )}
          {messages.map((m, i) => (
            <div
              key={i}
              className={m.role === "user" ? "flex justify-end" : "flex justify-start"}
            >
              <div
                className={
                  m.role === "user"
                    ? "max-w-[80%] rounded-lg bg-primary/10 px-3 py-2 text-sm"
                    : "max-w-[85%] rounded-lg bg-muted px-3 py-2 text-sm"
                }
              >
                {m.role === "user" ? (
                  <p className="whitespace-pre-wrap">{m.content}</p>
                ) : m.content ? (
                  <Markdown>{m.content}</Markdown>
                ) : (
                  <p className="text-muted-foreground">…</p>
                )}
                {m.role === "assistant" && (m.resolving || m.model) && (
                  <p className="mt-1.5 text-xs text-muted-foreground">
                    {m.resolving && !m.model
                      ? "confirming model…"
                      : `answered by ${m.model}${m.fallback ? " (fallback)" : ""}`}
                  </p>
                )}
              </div>
            </div>
          ))}
        </div>

        {error && <p className="mt-2 text-sm text-destructive">{error}</p>}

        <div className="mt-3 flex gap-2">
          <Input
            placeholder="Ask anything — code, math, a quick question…"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                send();
              }
            }}
            disabled={busy}
          />
          <Button onClick={send} disabled={busy || !input.trim() || !apiKey.trim()}>
            <Send className="size-4" />
            Send
          </Button>
        </div>
      </main>
    </>
  );
}

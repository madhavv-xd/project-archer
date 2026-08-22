"use client";

import { useEffect, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type Health = { status: string; routing_mode: string };

/** Top-bar status pills, read from GET /health (public). Renders nothing until
 * the fetch lands; renders an unhealthy state if it fails. */
function HealthPills() {
  const [health, setHealth] = useState<Health | null | "error">(null);

  useEffect(() => {
    fetch(`${API_URL}/health`)
      .then((r) => r.json())
      .then(setHealth)
      .catch(() => setHealth("error"));
  }, []);

  if (health === null) return null;
  const ok = health !== "error" && health.status === "ok";
  return (
    <div className="flex items-center gap-2 font-mono text-[11px]">
      <span className="inline-flex items-center gap-1.5 rounded-full border border-border px-2.5 py-1 text-(--neutral-500)">
        <span
          className={
            ok
              ? "size-1.5 animate-pulse rounded-full bg-(--success)"
              : "size-1.5 rounded-full bg-(--danger)"
          }
        />
        api · {ok ? "healthy" : "down"}
      </span>
      {ok && (
        <span className="rounded-full border border-(--accent-800) bg-primary/10 px-2.5 py-1 text-(--accent-300)">
          routing: {(health as Health).routing_mode}
        </span>
      )}
    </div>
  );
}

export function Header({
  title,
  subtitle,
  actions,
}: {
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
}) {
  return (
    <header className="flex h-[58px] shrink-0 items-center justify-between border-b border-border px-6">
      <div>
        <h1 className="text-title">{title}</h1>
        {subtitle && <p className="text-caption text-(--neutral-600)">{subtitle}</p>}
      </div>
      <div className="flex items-center gap-3">
        {actions}
        <HealthPills />
      </div>
    </header>
  );
}

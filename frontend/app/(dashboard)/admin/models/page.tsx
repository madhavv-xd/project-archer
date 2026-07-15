"use client";

import { useCallback, useEffect, useState } from "react";
import { useSession } from "next-auth/react";

import { adminApi } from "@/lib/api";
import type { AdminModel } from "@/types";
import { Header } from "@/components/layout/Header";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

function ModelRow({
  model,
  token,
  onChanged,
}: {
  model: AdminModel;
  token: string;
  onChanged: () => void;
}) {
  const [domains, setDomains] = useState(model.routing_domains.join(", "));
  const [priority, setPriority] = useState(String(model.fallback_priority));
  const [busy, setBusy] = useState(false);

  const dirty =
    domains !== model.routing_domains.join(", ") ||
    priority !== String(model.fallback_priority);

  async function save() {
    setBusy(true);
    await adminApi.updateModel(token, model.id, {
      routing_domains: domains.split(",").map((d) => d.trim()).filter(Boolean),
      fallback_priority: Number(priority),
    });
    setBusy(false);
    onChanged();
  }

  async function toggleActive() {
    setBusy(true);
    await adminApi.updateModel(token, model.id, { is_active: !model.is_active });
    setBusy(false);
    onChanged();
  }

  return (
    <tr className={`border-b border-border ${model.is_active ? "" : "opacity-50"}`}>
      <td className="px-3 py-2">
        <div className="font-mono text-xs text-foreground">{model.name}</div>
        <div className="text-xs text-muted-foreground">{model.provider}</div>
      </td>
      <td className="px-3 py-2">
        <Input
          value={domains}
          onChange={(e) => setDomains(e.target.value)}
          placeholder="coding, general"
          className="h-8 text-xs"
        />
      </td>
      <td className="px-3 py-2 w-20">
        <Input
          type="number"
          value={priority}
          onChange={(e) => setPriority(e.target.value)}
          className="h-8 w-16 text-xs"
        />
      </td>
      <td className="px-3 py-2">
        <span className={model.is_active ? "text-primary" : "text-muted-foreground"}>
          {model.is_active ? "active" : "disabled"}
        </span>
      </td>
      <td className="px-3 py-2">
        <div className="flex gap-2">
          <Button size="sm" onClick={save} disabled={busy || !dirty}>
            Save
          </Button>
          <Button size="sm" variant="ghost" onClick={toggleActive} disabled={busy}>
            {model.is_active ? "Disable" : "Enable"}
          </Button>
        </div>
      </td>
    </tr>
  );
}

export default function AdminModelsPage() {
  const { data: session } = useSession();
  const token = session?.accessToken;
  const [models, setModels] = useState<AdminModel[]>([]);

  const load = useCallback(() => {
    if (token) adminApi.models(token).then(setModels);
  }, [token]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <>
      <Header
        title="Manage Models"
        subtitle="Toggle a model, repoint a domain, or reorder fallback — live, no deploy."
      />
      <main className="flex-1 overflow-y-auto p-6">
        <div className="overflow-x-auto rounded-lg border border-border">
          <table className="w-full text-sm">
            <thead className="border-b border-border text-left text-muted-foreground">
              <tr>
                <th className="px-3 py-2 font-medium">Model</th>
                <th className="px-3 py-2 font-medium">Routing domains</th>
                <th className="px-3 py-2 font-medium">Priority</th>
                <th className="px-3 py-2 font-medium">State</th>
                <th className="px-3 py-2 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {token &&
                models.map((m) => (
                  <ModelRow key={m.id} model={m} token={token} onChanged={load} />
                ))}
            </tbody>
          </table>
        </div>
        <p className="mt-3 text-xs text-muted-foreground">
          Domains are comma-separated (the 6 buckets: coding, math, writing, simple, analysis,
          general). Lower priority = tried earlier in the fallback chain. Changes take effect on
          the next request.
        </p>
      </main>
    </>
  );
}

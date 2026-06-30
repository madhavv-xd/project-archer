"use client";

import { useEffect, useState } from "react";
import { useSession } from "next-auth/react";

import { api } from "@/lib/api";
import type { Model } from "@/types";
import { Header } from "@/components/layout/Header";
import { ModelCard } from "@/components/models/ModelCard";

export default function ModelsPage() {
  const { data: session } = useSession();
  const token = session?.accessToken;
  const [models, setModels] = useState<Model[]>([]);

  useEffect(() => {
    if (!token) return;
    api.models(token).then(setModels);
  }, [token]);

  return (
    <>
      <Header title="Models" subtitle="The pool Archer draws from for every request." />
      <main className="flex-1 overflow-y-auto p-6">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {models.map((model) => (
            <ModelCard key={model.id} model={model} />
          ))}
        </div>
      </main>
    </>
  );
}

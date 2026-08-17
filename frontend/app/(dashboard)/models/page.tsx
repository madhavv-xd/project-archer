"use client";

import { useEffect, useState } from "react";
import { useSession } from "next-auth/react";
import { Boxes } from "lucide-react";

import { api } from "@/lib/api";
import type { Model } from "@/types";
import { Header } from "@/components/layout/Header";
import { PageBody } from "@/components/layout/PageBody";
import { EmptyState } from "@/components/ui/empty-state";
import { ModelCard } from "@/components/models/ModelCard";

export default function ModelsPage() {
  const { data: session } = useSession();
  const token = session?.accessToken;
  // null = not fetched yet; [] = fetched and genuinely empty. Collapsing the
  // two flashes a false "nothing here" before the first response lands.
  const [models, setModels] = useState<Model[] | null>(null);

  useEffect(() => {
    if (!token) return;
    api.models(token).then(setModels);
  }, [token]);

  return (
    <>
      <Header title="Models" subtitle="The pool Archer draws from for every request." />
      <PageBody>
        {models === null ? null : models.length === 0 ? (
          <EmptyState
            title="No models to show."
            hint="The catalog loads from the backend — if this stays empty, check that the API is reachable."
            icon={Boxes}
          />
        ) : (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
            {models.map((model) => (
              <ModelCard key={model.id} model={model} />
            ))}
          </div>
        )}
      </PageBody>
    </>
  );
}

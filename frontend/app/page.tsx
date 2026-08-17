import { getServerSession } from "next-auth";

import { authOptions } from "@/lib/auth";
import { Landing } from "@/components/landing/Landing";

// Shown if /health is unreachable at render time. Only a floor for the copy to
// stand on — the real number comes from the backend below.
const FALLBACK_MODEL_COUNT = 8;

/** Live active-catalog size, straight from the backend's in-memory cache.
 *  This used to be a hardcoded constant and it drifted: the catalog dropped to
 *  8 active models while the page still advertised 9. `/health` is public and
 *  already reports `models_loaded`, so there's nothing to keep in sync. */
async function getModelCount(): Promise<number> {
  try {
    const res = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/health`,
      { next: { revalidate: 3600 } },
    );
    if (!res.ok) return FALLBACK_MODEL_COUNT;
    const { models_loaded } = await res.json();
    return typeof models_loaded === "number" && models_loaded > 0
      ? models_loaded
      : FALLBACK_MODEL_COUNT;
  } catch {
    return FALLBACK_MODEL_COUNT;
  }
}

export default async function Home() {
  const [session, modelCount] = await Promise.all([
    getServerSession(authOptions),
    getModelCount(),
  ]);
  return <Landing isAuthed={!!session} modelCount={modelCount} />;
}

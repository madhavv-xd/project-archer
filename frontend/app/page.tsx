import { getServerSession } from "next-auth";

import { authOptions } from "@/lib/auth";
import { Landing } from "@/components/landing/Landing";

// Active catalog size (5 Groq + 4 Ollama). Update alongside catalog migrations.
const ACTIVE_MODEL_COUNT = 9;

export default async function Home() {
  const session = await getServerSession(authOptions);
  return <Landing isAuthed={!!session} modelCount={ACTIVE_MODEL_COUNT} />;
}

import { getServerSession } from "next-auth";

import { authOptions } from "@/lib/auth";
import { Landing } from "@/components/landing/Landing";

export default async function Home() {
  const session = await getServerSession(authOptions);
  return <Landing isAuthed={!!session} />;
}

import { Header } from "@/components/layout/Header";
import { ApiKeyList } from "@/components/api-keys/ApiKeyList";

export default function ApiKeysPage() {
  return (
    <>
      <Header title="API Keys" subtitle="Create and manage your arch_sk_ keys." />
      <main className="flex-1 overflow-y-auto p-6">
        <ApiKeyList />
      </main>
    </>
  );
}

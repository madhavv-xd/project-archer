import { Header } from "@/components/layout/Header";
import { PageBody } from "@/components/layout/PageBody";
import { ApiKeyList } from "@/components/api-keys/ApiKeyList";

export default function ApiKeysPage() {
  return (
    <>
      <Header title="API Keys" subtitle="Create and manage your arch_sk_ keys." />
      <PageBody>
        <ApiKeyList />
      </PageBody>
    </>
  );
}

"use client";

import { useEffect, useState } from "react";
import { useSession } from "next-auth/react";

import { api } from "@/lib/api";
import type { Paginated, RequestLog } from "@/types";
import { Header } from "@/components/layout/Header";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { RequestsTable } from "@/components/logs/RequestsTable";

export default function LogsPage() {
  const { data: session } = useSession();
  const token = session?.accessToken;
  const [page, setPage] = useState(1);
  const [data, setData] = useState<Paginated<RequestLog> | null>(null);

  useEffect(() => {
    if (!token) return;
    api.logs(token, page, 20).then(setData);
  }, [token, page]);

  const totalPages = data?.total_pages ?? 1;

  return (
    <>
      <Header title="Logs" subtitle="Every request, and the model that answered it." />
      <main className="flex-1 overflow-y-auto p-6">
        <Card>
          <CardContent className="px-0">
            <RequestsTable logs={data?.items ?? []} />
          </CardContent>
        </Card>
        <div className="mt-4 flex items-center justify-between text-sm text-muted-foreground">
          <span>
            {data ? `${data.total} requests` : ""}
          </span>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
            >
              Previous
            </Button>
            <span>
              Page {page} / {totalPages}
            </span>
            <Button
              variant="outline"
              size="sm"
              disabled={page >= totalPages}
              onClick={() => setPage((p) => p + 1)}
            >
              Next
            </Button>
          </div>
        </div>
      </main>
    </>
  );
}

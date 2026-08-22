import Link from "next/link";

import type { RequestLog } from "@/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { RequestsTable } from "@/components/logs/RequestsTable";

export function RecentRequests({ logs }: { logs: RequestLog[] | null }) {
  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between">
        <CardTitle>Recent Requests</CardTitle>
        <Link
          href="/logs"
          className="font-mono text-caption text-(--accent-300) hover:text-(--accent-200)"
        >
          view all →
        </Link>
      </CardHeader>
      <CardContent className="px-0">
        <RequestsTable logs={logs} showFallback={false} />
      </CardContent>
    </Card>
  );
}

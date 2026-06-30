import type { RequestLog } from "@/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { RequestsTable } from "@/components/logs/RequestsTable";

export function RecentRequests({ logs }: { logs: RequestLog[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Recent Requests</CardTitle>
      </CardHeader>
      <CardContent className="px-0">
        <RequestsTable logs={logs} showFallback={false} />
      </CardContent>
    </Card>
  );
}

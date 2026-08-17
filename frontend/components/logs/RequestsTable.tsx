import type { RequestLog } from "@/types";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

function StatusBadge({ status }: { status: string }) {
  const variant =
    status === "success" ? "success" : status === "timeout" ? "muted" : "destructive";
  return <Badge variant={variant}>{status}</Badge>;
}

export function RequestsTable({
  logs,
  showFallback = true,
}: {
  /** null = not fetched yet (render nothing); [] = fetched and empty. */
  logs: RequestLog[] | null;
  showFallback?: boolean;
}) {
  if (logs === null) return null;
  if (logs.length === 0) {
    return (
      <EmptyState
        title="No requests yet."
        hint="Point your first call at /v1/chat/completions and it will show up here."
      />
    );
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Time</TableHead>
          <TableHead>Model</TableHead>
          <TableHead>Routing</TableHead>
          <TableHead>Prompt</TableHead>
          <TableHead>Completion</TableHead>
          <TableHead>Latency</TableHead>
          <TableHead>Status</TableHead>
          {showFallback && <TableHead>Fallback</TableHead>}
        </TableRow>
      </TableHeader>
      <TableBody>
        {logs.map((log) => (
          <TableRow key={log.id}>
            <TableCell className="whitespace-nowrap text-muted-foreground">
              {new Date(log.created_at).toLocaleString()}
            </TableCell>
            <TableCell className="font-mono text-body-sm">{log.model ?? "—"}</TableCell>
            <TableCell>
              <Badge variant="outline" className="font-mono">{log.routing_reason}</Badge>
            </TableCell>
            <TableCell>{log.prompt_tokens ?? "—"}</TableCell>
            <TableCell>{log.completion_tokens ?? "—"}</TableCell>
            <TableCell className="whitespace-nowrap">{log.latency_ms} ms</TableCell>
            <TableCell>
              <StatusBadge status={log.status} />
            </TableCell>
            {showFallback && (
              <TableCell>
                {log.fallback_used ? (
                  <Badge variant="muted">fallback</Badge>
                ) : (
                  <span className="text-muted-foreground">—</span>
                )}
              </TableCell>
            )}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

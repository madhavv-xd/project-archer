"use client";

import { useCallback, useEffect, useState } from "react";
import { useSession } from "next-auth/react";
import { Plus, Trash2 } from "lucide-react";

import { api } from "@/lib/api";
import type { ApiKey } from "@/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { CreateKeyModal } from "@/components/api-keys/CreateKeyModal";

export function ApiKeyList() {
  const { data: session } = useSession();
  const token = session?.accessToken;
  const [keys, setKeys] = useState<ApiKey[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);

  const load = useCallback(async () => {
    if (!token) return;
    setKeys(await api.listKeys(token));
    setLoading(false);
  }, [token]);

  useEffect(() => {
    load();
  }, [load]);

  async function remove(id: string) {
    if (!token) return;
    await api.deleteKey(token, id);
    setKeys((prev) => prev.filter((k) => k.id !== id));
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex justify-end">
        <Button onClick={() => setModalOpen(true)} disabled={!token}>
          <Plus className="size-4" />
          Create New Key
        </Button>
      </div>

      <Card>
        <CardContent className="px-0">
          {loading ? (
            <div className="px-3 py-8 text-center text-sm text-muted-foreground">
              Loading…
            </div>
          ) : keys.length === 0 ? (
            <div className="px-3 py-8 text-center text-sm text-muted-foreground">
              No API keys yet. Create one to start calling the API.
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Prefix</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead>Last used</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {keys.map((k) => (
                  <TableRow key={k.id}>
                    <TableCell className="font-medium">{k.name}</TableCell>
                    <TableCell className="font-mono text-xs text-muted-foreground">
                      {k.key_prefix}…
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {new Date(k.created_at).toLocaleDateString()}
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {k.last_used_at
                        ? new Date(k.last_used_at).toLocaleString()
                        : "Never"}
                    </TableCell>
                    <TableCell>
                      <Badge variant={k.is_active ? "success" : "muted"}>
                        {k.is_active ? "active" : "inactive"}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        variant="ghost"
                        size="icon-sm"
                        onClick={() => remove(k.id)}
                        aria-label="Delete key"
                      >
                        <Trash2 className="size-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {modalOpen && token && (
        <CreateKeyModal
          token={token}
          onClose={() => setModalOpen(false)}
          onCreated={load}
        />
      )}
    </div>
  );
}

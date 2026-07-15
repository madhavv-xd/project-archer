"use client";

import { useCallback, useEffect, useState } from "react";
import { useSession } from "next-auth/react";

import { adminApi } from "@/lib/api";
import type { AdminUser } from "@/types";
import { Header } from "@/components/layout/Header";
import { Button } from "@/components/ui/button";

export default function AdminUsersPage() {
  const { data: session } = useSession();
  const token = session?.accessToken;
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [busy, setBusy] = useState<string | null>(null);

  const load = useCallback(() => {
    if (token) adminApi.users(token).then((res) => setUsers(res.items));
  }, [token]);

  useEffect(() => {
    load();
  }, [load]);

  async function toggle(u: AdminUser) {
    if (!token) return;
    setBusy(u.id);
    await adminApi.setUserActive(token, u.id, !u.is_active);
    setBusy(null);
    load();
  }

  return (
    <>
      <Header title="Users" subtitle="Deactivate an abuser and their keys stop working immediately." />
      <main className="flex-1 overflow-y-auto p-6">
        <div className="overflow-x-auto rounded-lg border border-border">
          <table className="w-full text-sm">
            <thead className="border-b border-border text-left text-muted-foreground">
              <tr>
                <th className="px-3 py-2 font-medium">Email</th>
                <th className="px-3 py-2 font-medium">Plan</th>
                <th className="px-3 py-2 font-medium">Role</th>
                <th className="px-3 py-2 font-medium">Requests</th>
                <th className="px-3 py-2 font-medium">State</th>
                <th className="px-3 py-2 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} className={`border-b border-border ${u.is_active ? "" : "opacity-50"}`}>
                  <td className="px-3 py-2">{u.email}</td>
                  <td className="px-3 py-2">{u.plan}</td>
                  <td className="px-3 py-2">
                    {u.role === "admin" ? (
                      <span className="text-primary">admin</span>
                    ) : (
                      "user"
                    )}
                  </td>
                  <td className="px-3 py-2">{u.request_count.toLocaleString()}</td>
                  <td className="px-3 py-2">
                    <span className={u.is_active ? "text-primary" : "text-destructive"}>
                      {u.is_active ? "active" : "deactivated"}
                    </span>
                  </td>
                  <td className="px-3 py-2">
                    <Button
                      size="sm"
                      variant={u.is_active ? "ghost" : "default"}
                      onClick={() => toggle(u)}
                      disabled={busy === u.id || u.role === "admin"}
                    >
                      {u.is_active ? "Deactivate" : "Reactivate"}
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </main>
    </>
  );
}

"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { signOut, useSession } from "next-auth/react";
import {
  KeyRound,
  LayoutDashboard,
  LogOut,
  ScrollText,
  Boxes,
  MessagesSquare,
  ShieldCheck,
  Gauge,
  Users,
} from "lucide-react";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Brandmark } from "@/components/layout/Brandmark";

const NAV = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/playground", label: "Playground", icon: MessagesSquare },
  { href: "/api-keys", label: "API Keys", icon: KeyRound },
  { href: "/models", label: "Models", icon: Boxes },
  { href: "/logs", label: "Logs", icon: ScrollText },
];

const ADMIN_NAV = [
  { href: "/admin/overview", label: "Overview", icon: Gauge },
  { href: "/admin/models", label: "Manage Models", icon: ShieldCheck },
  { href: "/admin/users", label: "Users", icon: Users },
];

export function Sidebar() {
  const pathname = usePathname();
  const { data: session } = useSession();

  const renderLink = ({
    href,
    label,
    icon: Icon,
  }: {
    href: string;
    label: string;
    icon: typeof LayoutDashboard;
  }) => {
    const active = pathname === href || pathname.startsWith(`${href}/`);
    return (
      <Link
        key={href}
        href={href}
        className={cn(
          "relative flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
          active
            ? "bg-primary/10 text-primary before:absolute before:inset-y-1.5 before:left-0 before:w-0.5 before:rounded-full before:bg-primary"
            : "text-muted-foreground hover:bg-muted hover:text-foreground",
        )}
      >
        <Icon className="size-4" />
        {label}
      </Link>
    );
  };

  return (
    <aside className="flex w-60 shrink-0 flex-col border-r border-sidebar-border bg-sidebar">
      <Link href="/" className="flex h-16 items-center px-5">
        <Brandmark iconSize={20} className="text-lg" />
      </Link>
      <nav className="flex flex-1 flex-col gap-1 px-3 pt-2">
        {NAV.map(renderLink)}
        {session?.user?.role === "admin" && (
          <>
            <div className="mt-4 px-3 pb-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Admin
            </div>
            {ADMIN_NAV.map(renderLink)}
          </>
        )}
      </nav>
      <div className="border-t border-border p-3">
        <div className="mb-2 truncate px-2 text-xs text-muted-foreground">
          {session?.user?.email}
        </div>
        <Button
          variant="ghost"
          size="sm"
          className="w-full justify-start"
          onClick={() => signOut({ callbackUrl: "/login" })}
        >
          <LogOut className="size-4" />
          Logout
        </Button>
      </div>
    </aside>
  );
}

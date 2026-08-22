"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { signOut, useSession } from "next-auth/react";
import {
  BookOpenText,
  ChatsCircle,
  Cube,
  Gauge,
  Key,
  Scroll,
  SignOut,
  SlidersHorizontal,
  SquaresFour,
  UsersThree,
  type Icon,
} from "@phosphor-icons/react";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Brandmark } from "@/components/layout/Brandmark";

const NAV = [
  { href: "/dashboard", label: "Dashboard", icon: SquaresFour },
  { href: "/playground", label: "Playground", icon: ChatsCircle },
  { href: "/api-keys", label: "API Keys", icon: Key },
  { href: "/models", label: "Models", icon: Cube },
  { href: "/logs", label: "Logs", icon: Scroll },
];

const ADMIN_NAV = [
  { href: "/admin/overview", label: "Overview", icon: Gauge },
  { href: "/admin/models", label: "Manage Models", icon: SlidersHorizontal },
  { href: "/admin/users", label: "Users", icon: UsersThree },
];

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div className="mt-4 px-3 pb-1 font-mono text-[10px] uppercase tracking-[.16em] text-(--neutral-600)">
      {children}
    </div>
  );
}

export function Sidebar() {
  const pathname = usePathname();
  const { data: session } = useSession();

  const renderLink = ({
    href,
    label,
    icon: IconComp,
  }: {
    href: string;
    label: string;
    icon: Icon;
  }) => {
    const active = pathname === href || pathname.startsWith(`${href}/`);
    return (
      <Link
        key={href}
        href={href}
        className={cn(
          "relative flex items-center gap-2.5 rounded-[10px] border border-transparent px-3 py-2 text-body-sm font-medium transition-colors",
          active
            ? "border-(--accent-800) bg-primary/15 text-(--accent-200) after:absolute after:right-2.5 after:top-1/2 after:size-[5px] after:-translate-y-1/2 after:rounded-full after:bg-primary after:shadow-[0_0_8px_1px_var(--ring)]"
            : "text-(--neutral-500) hover:bg-muted hover:text-foreground",
        )}
      >
        <IconComp size={16} />
        {label}
      </Link>
    );
  };

  return (
    <aside className="flex w-56 shrink-0 flex-col border-r border-sidebar-border bg-sidebar">
      <Link href="/" className="flex h-[58px] items-center border-b border-sidebar-border px-4">
        <Brandmark iconSize={18} className="text-sm" />
      </Link>
      <nav className="flex flex-1 flex-col gap-1 px-3 pt-3">
        {NAV.map(renderLink)}
        {session?.user?.role === "admin" && (
          <>
            <SectionLabel>Admin</SectionLabel>
            {ADMIN_NAV.map(renderLink)}
          </>
        )}
        <SectionLabel>Public</SectionLabel>
        {renderLink({ href: "/docs", label: "Docs", icon: BookOpenText })}
      </nav>
      <div className="border-t border-sidebar-border p-3">
        <div className="mb-2 rounded-[10px] border border-border bg-card/60 px-3 py-2">
          <div className="truncate text-caption text-foreground">{session?.user?.email}</div>
          <div className="font-mono text-[10px] uppercase tracking-[.12em] text-(--neutral-600)">
            free plan
          </div>
        </div>
        <Button
          variant="ghost"
          size="sm"
          className="w-full justify-start text-(--neutral-500)"
          onClick={() => signOut({ callbackUrl: "/login" })}
        >
          <SignOut size={16} />
          Log out
        </Button>
      </div>
    </aside>
  );
}

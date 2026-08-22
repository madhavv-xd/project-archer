import Link from "next/link";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Brandmark } from "@/components/layout/Brandmark";
import { Mascot } from "@/components/landing/Mascot";

/** The shared frame behind /login and /register — accent radial, Fletch +
 *  brandmark home link, and the card header. Both pages carried an identical
 *  copy of it, so a spacing or type tweak had to be made twice to stay in sync. */
export function AuthShell({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle: string;
  children: React.ReactNode;
}) {
  return (
    <div className="relative flex min-h-screen flex-col items-center justify-center gap-6 p-gutter">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0"
        style={{
          backgroundImage:
            "radial-gradient(55% 45% at 50% 0%, rgba(145,132,217,0.2), transparent 70%)",
        }}
      />
      <Link href="/" className="relative flex flex-col items-center gap-3">
        <Mascot className="w-[76px]" />
        <Brandmark iconSize={20} className="text-xl" />
      </Link>
      <Card className="relative w-full max-w-[392px] rounded-2xl">
        <CardHeader className="gap-2 text-center">
          <CardTitle className="font-display text-title">{title}</CardTitle>
          <p className="text-body-sm text-muted-foreground">{subtitle}</p>
        </CardHeader>
        <CardContent>{children}</CardContent>
      </Card>
    </div>
  );
}

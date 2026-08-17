import { cn } from "@/lib/utils";

/** The scrollable body every dashboard page renders under its <Header>.
 *  Was `<main className="flex-1 overflow-y-auto p-6">` copy-pasted across eight
 *  routes; centralised so page padding tracks the spacing scale in one place. */
export function PageBody({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <main className={cn("flex-1 overflow-y-auto p-gutter", className)}>{children}</main>
  );
}

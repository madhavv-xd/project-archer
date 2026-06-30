export function Header({ title }: { title: string }) {
  return (
    <header className="flex h-14 shrink-0 items-center border-b border-border px-6">
      <h1 className="text-base font-semibold">{title}</h1>
    </header>
  );
}

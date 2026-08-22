import type { Model } from "@/types";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function ModelCard({ model }: { model: Model }) {
  return (
    <Card className="relative overflow-hidden hover:-translate-y-0.5 hover:border-(--accent-700)">
      {/* Nocturne corner wash */}
      <span
        aria-hidden
        className="pointer-events-none absolute right-0 top-0 size-11"
        style={{ background: "linear-gradient(225deg, rgba(145,132,217,.22), transparent 70%)" }}
      />
      <CardHeader className="flex-row items-start justify-between gap-2">
        <div>
          <CardTitle>{model.display_name}</CardTitle>
          <div className="mt-1 font-mono text-xs text-muted-foreground">
            {model.model_id}
          </div>
        </div>
        <Badge variant={model.is_active ? "success" : "muted"}>
          {model.is_active ? "active" : "inactive"}
        </Badge>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <div className="flex flex-wrap gap-1.5">
          <Badge className="uppercase">{model.provider}</Badge>
          <Badge variant="outline">{model.speed_tier.replace("_", " ")}</Badge>
          <Badge variant="outline">free</Badge>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {model.best_for.map((tag) => (
            <Badge key={tag} className="bg-[rgba(233,233,237,.06)] text-muted-foreground">
              {tag}
            </Badge>
          ))}
        </div>
        <div className="flex items-baseline justify-between border-t border-[rgba(233,233,237,.06)] pt-2.5">
          <span className="font-mono text-label uppercase text-(--neutral-600)">context</span>
          <span className="font-mono text-caption text-foreground">
            {model.context_window.toLocaleString()}
          </span>
        </div>
      </CardContent>
    </Card>
  );
}

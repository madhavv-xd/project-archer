import type { Model } from "@/types";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function ModelCard({ model }: { model: Model }) {
  return (
    <Card>
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
          <Badge variant="secondary">{model.provider}</Badge>
          <Badge variant="outline">{model.speed_tier.replace("_", " ")}</Badge>
          <Badge>Free</Badge>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {model.best_for.map((tag) => (
            <Badge key={tag} variant="muted">
              {tag}
            </Badge>
          ))}
        </div>
        <div className="text-xs text-muted-foreground">
          Context window: {model.context_window.toLocaleString()} tokens
        </div>
      </CardContent>
    </Card>
  );
}

"""Health check."""

from fastapi import APIRouter, Request

from app.config import settings
from app.core.embeddings import embedding_health
from app.core.proxy import model_cache

router = APIRouter()

VERSION = "0.1.0"


# HEAD is kept for uptime probes but excluded from the schema: one shared
# operation id across both methods collides in the generated OpenAPI.
@router.get("/health")
@router.head("/health", include_in_schema=False)
async def health(request: Request) -> dict:
    redis_client = getattr(request.app.state, "redis", None)
    if redis_client is None:
        redis_status = "disabled"
    else:
        try:
            await redis_client.ping()
            redis_status = "ok"
        except Exception:
            redis_status = "degraded"

    try:
        embedding_status = await embedding_health()
    except Exception:
        embedding_status = "degraded"

    return {
        "status": "ok",
        "version": VERSION,
        "models_loaded": len(model_cache),
        "redis": redis_status,
        "embedding": embedding_status,
        "routing_mode": settings.ROUTING_MODE,
    }

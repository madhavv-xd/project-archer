"""Health check."""

from fastapi import APIRouter, Request

from app.core.proxy import model_cache

router = APIRouter()

VERSION = "0.1.0"


@router.api_route("/health", methods=["GET", "HEAD"])
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
    return {
        "status": "ok",
        "version": VERSION,
        "models_loaded": len(model_cache),
        "redis": redis_status,
    }

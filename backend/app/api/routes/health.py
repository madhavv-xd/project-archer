"""Health check."""

from fastapi import APIRouter

from app.core.proxy import model_cache

router = APIRouter()

VERSION = "0.1.0"


@router.api_route("/health", methods=["GET", "HEAD"])
async def health() -> dict:
    return {"status": "ok", "version": VERSION, "models_loaded": len(model_cache)}

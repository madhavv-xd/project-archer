"""Health check."""

from fastapi import APIRouter

from app.core.proxy import model_cache

router = APIRouter()

VERSION = "0.1.0"


@router.get("/health")
async def health() -> dict:
    return {"status": "ok", "version": VERSION, "models_loaded": len(model_cache)}

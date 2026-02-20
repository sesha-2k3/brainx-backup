# API: Health check and readiness endpoints

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.db import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """Basic liveness probe."""
    return {"status": "ok"}


@router.get("/ready")
async def readiness_check(db: AsyncSession = Depends(get_db)):
    """Readiness probe - checks database connectivity."""
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ready", "database": "connected"}
    except Exception as e:
        return {"status": "not_ready", "database": "disconnected", "error": str(e)}

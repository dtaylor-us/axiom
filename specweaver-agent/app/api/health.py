"""Health routes for SpecWeaver agent."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/health")
async def health():
    """Return liveness status."""
    return JSONResponse({"status": "UP", "service": "specweaver-agent"})

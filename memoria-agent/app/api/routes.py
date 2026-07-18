import os

from fastapi import APIRouter, Header, HTTPException

from app.models.contracts import DistillRequest, DistillResponse
from app.pipeline.distiller import distill as run_distill

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "healthy", "service": "memoria-agent"}


@router.post("/distill", response_model=DistillResponse)
async def distill_endpoint(
    request: DistillRequest,
    x_internal_secret: str = Header(None),
):
    """Distil a completed pillar session into memory candidates."""
    expected = os.getenv("INTERNAL_SECRET", "")
    if not expected or x_internal_secret != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")

    return await run_distill(request)

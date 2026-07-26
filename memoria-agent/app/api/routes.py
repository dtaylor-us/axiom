import logging
import os

from fastapi import APIRouter, Header, HTTPException

from app.models.contracts import DistillRequest, DistillResponse
from app.pipeline.distiller import distill as run_distill

router = APIRouter()
logger = logging.getLogger(__name__)


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

    response = await run_distill(request)
    logger.info(
        "distill: session=%s pillar=%s candidates=%d conflicts=%d msg=%s",
        request.session_id,
        request.pillar,
        len(response.candidates),
        len(response.conflicts),
        response.message[:100],
    )
    return response

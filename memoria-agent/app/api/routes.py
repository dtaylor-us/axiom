import os
from fastapi import APIRouter, Header, HTTPException
from app.models.contracts import DistillRequest, DistillResponse

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "healthy", "service": "memoria-agent"}


@router.post("/distill", response_model=DistillResponse)
async def distill(
    request: DistillRequest,
    x_internal_secret: str = Header(None),
):
    """
    Phase 1 stub — distillation pipeline not yet implemented.
    Returns empty candidate list. Real implementation in Phase 3.
    """
    expected = os.getenv("INTERNAL_SECRET", "")
    if not expected or x_internal_secret != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return DistillResponse(
        session_id=request.session_id,
        candidates=[],
        conflicts=[],
        message="Distillation pipeline not yet active (Phase 1 stub)",
    )

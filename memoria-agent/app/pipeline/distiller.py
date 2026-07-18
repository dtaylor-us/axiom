"""Phase 1 stub. Real distillation pipeline implemented in Phase 3."""
from app.models.contracts import DistillRequest, DistillResponse


async def distill(request: DistillRequest) -> DistillResponse:
    return DistillResponse(
        session_id=request.session_id,
        candidates=[],
        conflicts=[],
        message="Distillation not yet active",
    )

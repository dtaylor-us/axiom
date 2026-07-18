"""Automatic distillation pipeline."""
from app.models.contracts import DistillRequest, DistillResponse
from app.tools.conflict_detector import detect_conflicts
from app.tools.fact_extractor import extract_facts


async def distill(request: DistillRequest) -> DistillResponse:
    candidates = await extract_facts(request.session_summary, request.session_payload)
    conflicts = await detect_conflicts(candidates, request.existing_entries)
    return DistillResponse(
        session_id=request.session_id,
        candidates=candidates,
        conflicts=conflicts,
        message=f"Distilled {len(candidates)} candidate memories and {len(conflicts)} conflict flags",
    )

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.pipeline.graph import build_graph
from app.models.contracts import ReviewContext
from app.tools.gap_analyzer import generate_gap_questions
from app.tools.gap_assessor import assess_gap_resolution

router = APIRouter()


@router.post("/gaps/generate")
async def gaps_generate(request: dict):
    return generate_gap_questions(
        session_id=request["session_id"],
        evidence=request.get("evidence", []),
        previous_questions=request.get("previous_questions", []),
        answers=request.get("answers", []),
        round=request.get("round", 1),
    )


@router.post("/gaps/assess")
async def gaps_assess(request: dict):
    return await assess_gap_resolution(
        session_id=request["session_id"],
        questions=request.get("questions", []),
        answers=request.get("answers", []),
        round=request.get("round", 1),
        max_rounds=request.get("max_rounds", 5),
    )


@router.post("/review")
async def review(request: dict):
    context = ReviewContext(
        session_id=request["session_id"],
        system_description=request.get("system_description", ""),
        evidence=request.get("evidence", []),
        gap_questions=request.get("gap_questions", []),
        gap_answers=request.get("gap_answers", []),
        insufficient_info_gaps=request.get("insufficient_info_gaps", []),
    )
    graph = build_graph()
    final_context = await graph.ainvoke(context)
    return StreamingResponse(iter([str(final_context.review_report)]), media_type="application/x-ndjson")

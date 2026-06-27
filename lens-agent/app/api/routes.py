"""FastAPI routes for the Lens agent service.

Exposes three endpoints:
  POST /gaps/generate  - generate gap questions from evidence
  POST /gaps/assess    - assess whether gaps are resolved
  POST /review         - run the full 10-stage review pipeline

All endpoints return JSON. The /review endpoint returns the full
report as a JSON response (not streamed) for simplicity. Streaming
SSE can be added in a later phase once the pipeline is stable.
"""
from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.pipeline.graph import build_graph
from app.tools.gap_analyzer import generate_gap_questions
from app.tools.gap_assessor import assess_gap_resolution

logger = logging.getLogger(__name__)
router = APIRouter()

# Minimum combined characters of evidence content required to proceed.
# Below this threshold the pipeline cannot produce a meaningful review.
MIN_EVIDENCE_CHARS = 50

# Minimum number of populated analysis sections for a report to be
# considered substantive. If fewer than this many core sections have
# content, the response signals an incomplete report rather than HTTP 200.
MIN_POPULATED_SECTIONS = 2


def _validate_review_request(request: dict) -> str | None:
    """
    Validate a /review request and return an error message if invalid.

    Args:
        request: Raw request dict.

    Returns:
        Error message string if invalid, None if valid.
    """
    session_id = request.get("session_id", "").strip()
    if not session_id:
        return "session_id is required and must not be empty."

    evidence = request.get("evidence", [])
    system_description = request.get("system_description", "").strip()

    total_content = len(system_description)
    for item in evidence:
        total_content += len(item.get("content", ""))

    if total_content < MIN_EVIDENCE_CHARS:
        return (
            f"Insufficient evidence to conduct a review. "
            f"Please provide at least {MIN_EVIDENCE_CHARS} characters of "
            f"architecture description or evidence. "
            f"Received {total_content} characters."
        )

    return None


def _report_is_substantive(report: dict) -> bool:
    """
    Check whether a report has enough populated sections to be useful.

    A report where most LLM stages failed silently should not be returned
    as HTTP 200 — it would mislead the caller into treating an empty
    shell as a successful review.

    Args:
        report: Assembled review report dict.

    Returns:
        True if the report meets minimum substantiveness threshold.
    """
    core_sections = [
        report.get("azureWafScorecard"),
        report.get("atamAnalysis"),
        report.get("seiAnalysis"),
        report.get("risks"),
        report.get("recommendations"),
    ]
    populated = sum(1 for s in core_sections if s)
    return populated >= MIN_POPULATED_SECTIONS


@router.post("/gaps/generate")
async def gaps_generate(request: dict):
    """
    Generate gap questions from submitted architecture evidence.

    Adds a stable UUID id to each returned question so downstream
    callers can correlate answers by question ID.

    Returns:
        List of gap question objects with id, category, question, rationale.
    """
    questions = generate_gap_questions(
        session_id=request["session_id"],
        evidence=request.get("evidence", []),
        previous_questions=request.get("previous_questions", []),
        answers=request.get("answers", []),
        round=request.get("round", 1),
    )
    for q in questions:
        if not q.get("id"):
            q["id"] = str(uuid.uuid4())
    return questions


@router.post("/gaps/assess")
async def gaps_assess(request: dict):
    """
    Assess whether the gathered evidence and answers are sufficient
    to proceed with a review.

    Returns:
        GapAssessmentResult with resolved, canProceed, remainingCount,
        unresolvableGaps, summary.
    """
    return await assess_gap_resolution(
        session_id=request["session_id"],
        evidence=request.get("evidence", []),
        questions=request.get("questions", []),
        answers=request.get("answers", []),
        round=request.get("round", 1),
        max_rounds=request.get("max_rounds", 5),
    )


@router.post("/review")
async def review(request: dict):
    """
    Run the full 10-stage Lens review pipeline.

    Validates that sufficient evidence has been provided before running.
    Returns 400 if evidence is insufficient.
    Returns 503 with a structured error if the pipeline completes but
    produces an empty/unsubstantive report due to LLM stage failures.
    Returns 500 with a structured error if the pipeline itself crashes.

    Returns:
        JSON review report with executiveSummary, overallRating,
        azureWafScorecard, atamAnalysis, seiAnalysis,
        structuralAnalysis, risks, recommendations,
        insufficientInfoFindings, completedStages.
    """
    validation_error = _validate_review_request(request)
    if validation_error:
        return JSONResponse(
            status_code=400,
            content={
                "error": "Invalid review request",
                "detail": validation_error,
                "session_id": request.get("session_id", ""),
            },
        )

    initial_state = {
        "session_id": request["session_id"],
        "system_description": request.get("system_description", ""),
        "evidence": request.get("evidence", []),
        "gap_questions": request.get("gap_questions", []),
        "gap_answers": request.get("gap_answers", []),
        "insufficient_info_gaps": request.get("insufficient_info_gaps", []),
        "parsed_evidence": {},
        "azure_waf_scorecard": {},
        "atam_analysis": {},
        "sei_analysis": {},
        "structural_analysis": {},
        "risks": [],
        "recommendations": [],
        "executive_summary": "",
        "overall_rating": "",
        "review_report": {},
        "completed_stages": [],
        "pipeline_gaps": [],
        "has_gaps": False,
    }

    try:
        graph = build_graph()
        final_state = await graph.ainvoke(initial_state)
        report = final_state.get("review_report", {})

        # Guard against empty reports caused by widespread LLM stage failures.
        # A caller receiving HTTP 200 with an empty report would have no signal
        # that the review was not actually performed.
        if not _report_is_substantive(report):
            pipeline_gaps = final_state.get("pipeline_gaps", [])
            logger.error(
                "review: pipeline produced unsubstantive report. "
                "session=%s pipeline_gaps=%s",
                request.get("session_id"),
                pipeline_gaps,
            )
            return JSONResponse(
                status_code=503,
                content={
                    "error": "Review incomplete",
                    "detail": (
                        "The review pipeline completed but most analysis stages "
                        "failed. This is usually caused by LLM timeouts or rate "
                        "limits. Please retry the request."
                    ),
                    "session_id": request.get("session_id"),
                    "pipeline_gaps": pipeline_gaps,
                    "completed_stages": final_state.get("completed_stages", []),
                },
            )

        return JSONResponse(content=report)

    except Exception as exc:
        logger.exception(
            "review: pipeline failed session=%s error=%s",
            request.get("session_id"),
            str(exc),
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": "Review pipeline failed",
                "detail": str(exc),
                "session_id": request.get("session_id"),
                "completed_stages": [],
            },
        )

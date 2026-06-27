"""Gap resolution assessment for Lens architecture reviews.

Determines whether the evidence and answers collected so far are sufficient
to proceed with a meaningful review. Never blocks the user — after
max_rounds the system always returns can_proceed=True and unresolved
gaps become INSUFFICIENT_INFORMATION findings in the report.
"""
from __future__ import annotations

import json
import logging

from app.llm.client import get_llm_client

logger = logging.getLogger(__name__)

# Minimum coverage areas required before the system considers gaps resolved.
# These are assessed qualitatively by the LLM — not keyword matching.
MINIMUM_COVERAGE_AREAS = [
    "system purpose and scope",
    "primary components and responsibilities",
    "deployment or infrastructure detail",
    "security consideration",
    "reliability or availability consideration",
]


async def assess_gap_resolution(
    session_id: str,
    questions: list[dict],
    answers: list[dict],
    round: int,
    max_rounds: int,
) -> dict:
    """
    Assess whether evidence and answers are sufficient to proceed.

    The system NEVER blocks the user. After round >= max_rounds,
    can_proceed is always True regardless of gap state.
    Unresolved gaps are collected and will become INSUFFICIENT_INFORMATION
    findings in the final report.

    Args:
        session_id: Review session identifier.
        questions: All gap questions asked across all rounds.
        answers: All answers provided.
        round: Current round number (1-indexed).
        max_rounds: Maximum configured rounds before forcing proceed.

    Returns:
        Dict with keys: resolved, canProceed, remainingCount,
        unresolvableGaps, summary.
    """
    # After max rounds the system always proceeds — unresolved gaps
    # become findings rather than blockers.
    force_proceed = round >= max_rounds

    answered_pairs = _build_qa_pairs(questions, answers)
    unanswered = [
        q for q in questions
        if not q.get("answered") and not q.get("answer") and not q.get("skipped")
    ]

    if force_proceed:
        unresolvable_gaps = [
            f"[{q.get('category', 'UNKNOWN')}] {q.get('question', '')}"
            for q in unanswered
        ]
        return {
            "resolved": len(unanswered) == 0,
            "canProceed": True,
            "remainingCount": len(unanswered),
            "unresolvableGaps": unresolvable_gaps,
            "summary": (
                f"Maximum rounds ({max_rounds}) reached. Proceeding with "
                f"{len(unanswered)} unresolved gap(s) which will be noted "
                "as insufficient information in the report."
                if unanswered else
                "All questions answered. Proceeding to review."
            ),
        }

    prompt = f"""You are assessing whether an architecture review can proceed.

The review requires sufficient information across these minimum areas:
{chr(10).join(f'- {area}' for area in MINIMUM_COVERAGE_AREAS)}

## Questions Asked and Answers Provided

{answered_pairs if answered_pairs else 'No questions have been asked yet.'}

## Unanswered Questions

{_format_unanswered(unanswered) if unanswered else 'None — all questions answered.'}

## Your Task

Assess whether the information gathered is sufficient to perform a
meaningful architecture review. Sufficient means at least minimal
evidence exists for each of the minimum coverage areas listed above.

IMPORTANT: Be permissive. If the reviewer has enough to work with
for most areas, return resolved=true. Only return resolved=false
if critical areas have no coverage at all.

Return a JSON object:
{{
  "resolved": true,
  "remaining_count": 0,
  "unresolvable_gaps": [],
  "summary": "Brief explanation of assessment."
}}
"""

    client = get_llm_client()
    try:
        raw = await client.complete(
            prompt=prompt,
            response_format="json",
            stage_name="gap_assessment",
        )
        data = json.loads(raw)
        resolved = bool(data.get("resolved", False))
        remaining = int(data.get("remaining_count", len(unanswered)))
        unresolvable = data.get("unresolvable_gaps", [])
        summary = data.get("summary", "")

        return {
            "resolved": resolved,
            "canProceed": resolved,
            "remainingCount": remaining,
            "unresolvableGaps": unresolvable,
            "summary": summary,
        }
    except Exception as exc:
        logger.error(
            "gap_assessor: LLM call failed session=%s round=%d error=%s",
            session_id, round, exc
        )
        # On failure default to allowing proceed — never block the user
        return {
            "resolved": False,
            "canProceed": True,
            "remainingCount": len(unanswered),
            "unresolvableGaps": [
                f"[{q.get('category')}] {q.get('question')}" for q in unanswered
            ],
            "summary": "Gap assessment could not be completed. You may proceed to review.",
        }


def _build_qa_pairs(questions: list[dict], answers: list[dict]) -> str:
    """
    Build a formatted Q&A string from questions and answers.

    Args:
        questions: All gap questions.
        answers: All answers provided.

    Returns:
        Formatted Q&A string.
    """
    answered_ids = {a.get("question_id") or a.get("questionId") for a in answers}
    pairs = []
    for q in questions:
        if q.get("answered") or q.get("answer") or q.get("id") in answered_ids:
            answer_text = q.get("answer", "(answered — text not available)")
            pairs.append(
                f"Q [{q.get('category')}]: {q.get('question')}\n"
                f"A: {answer_text}"
            )
    return "\n\n".join(pairs)


def _format_unanswered(questions: list[dict]) -> str:
    """
    Format unanswered questions for the prompt.

    Args:
        questions: Unanswered question dicts.

    Returns:
        Formatted string.
    """
    return "\n".join(
        f"- [{q.get('category', 'UNKNOWN')}] {q.get('question', '')}"
        for q in questions
    )

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
MINIMUM_COVERAGE_AREAS = [
    "system purpose and scope",
    "primary components and responsibilities",
    "deployment or infrastructure detail",
    "security consideration",
    "reliability or availability consideration",
]


async def assess_gap_resolution(
    session_id: str,
    evidence: list[dict],
    questions: list[dict],
    answers: list[dict],
    round: int,
    max_rounds: int,
) -> dict:
    """
    Assess whether evidence and answers are sufficient to proceed.

    Now accepts evidence so the assessor can evaluate minimum coverage
    against the full architecture context, not just the Q&A pairs.
    The system NEVER blocks the user after round >= max_rounds.

    Args:
        session_id: Review session identifier.
        evidence: All architecture evidence submitted so far.
        questions: All gap questions asked across all rounds.
        answers: All answers provided.
        round: Current round number (1-indexed).
        max_rounds: Maximum configured rounds before forcing proceed.

    Returns:
        Dict with keys: resolved, canProceed, remainingCount,
        unresolvableGaps, summary.
    """
    force_proceed = round >= max_rounds

    # Build answer lookup from both embedded fields and the answers array
    answers_by_id = {}
    for a in answers:
        qid = a.get("question_id") or a.get("questionId")
        if qid:
            answers_by_id[qid] = a.get("answer", "")

    unanswered = []
    for q in questions:
        qid = q.get("id")
        has_embedded_answer = bool(q.get("answer")) or q.get("answered") is True
        has_array_answer = qid in answers_by_id and bool(answers_by_id[qid])
        is_skipped = q.get("skipped") is True
        if not has_embedded_answer and not has_array_answer and not is_skipped:
            unanswered.append(q)

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
                if unanswered
                else "All questions answered. Proceeding to review."
            ),
        }

    evidence_text = _format_evidence(evidence)
    qa_text = _build_qa_pairs(questions, answers_by_id)

    prompt = f"""You are assessing whether an architecture review can proceed.

The review requires sufficient information across these minimum areas:
{chr(10).join(f'- {area}' for area in MINIMUM_COVERAGE_AREAS)}

## Architecture Evidence Already Submitted

{evidence_text}

## Gap Questions and Answers

{qa_text if qa_text else 'No gap questions have been asked yet.'}

## Unanswered Questions

{_format_unanswered(unanswered) if unanswered else 'None — all questions answered or skipped.'}

## Your Task

Assess whether the COMBINED information from the architecture evidence
AND the Q&A answers is sufficient to perform a meaningful review.

IMPORTANT:
- Check the architecture evidence first — many minimum coverage areas
  may already be addressed there even if not in the Q&A answers.
- Only return resolved=false if critical areas have NO coverage at all
  in either the evidence or the answers.
- Be permissive — partial coverage is enough to proceed.

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
            session_id,
            round,
            exc,
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


def _format_evidence(evidence: list[dict]) -> str:
    """
    Format evidence items into a readable text block for the prompt.

    Args:
        evidence: List of evidence dicts.

    Returns:
        Formatted string or 'No evidence submitted yet.'
    """
    if not evidence:
        return "No evidence submitted yet."
    parts = []
    for i, item in enumerate(evidence, 1):
        label = item.get("sourceLabel") or item.get("source_label", f"Evidence {i}")
        evidence_type = item.get("evidenceType") or item.get("evidence_type", "TEXT")
        content = item.get("content", "")
        parts.append(f"### {label} ({evidence_type})\n{content}")
    return "\n\n".join(parts)


def _build_qa_pairs(questions: list[dict], answers_by_id: dict[str, str]) -> str:
    """
    Build a formatted Q&A string from questions and the answer lookup.

    Merges answers from both embedded question fields and the answers
    array so neither source is missed.

    Args:
        questions: All gap questions.
        answers_by_id: Mapping of question ID to answer text.

    Returns:
        Formatted Q&A string, or empty string if no answered questions.
    """
    pairs = []
    for q in questions:
        qid = q.get("id", "")
        answer = (
            q.get("answer")
            or answers_by_id.get(qid)
            or ("(skipped)" if q.get("skipped") else None)
        )
        if answer:
            pairs.append(
                f"Q [{q.get('category', '')}]: {q.get('question', '')}\n"
                f"A: {answer}"
            )
    return "\n\n".join(pairs)


def _format_unanswered(questions: list[dict]) -> str:
    """
    Format unanswered questions for the prompt.

    Args:
        questions: Unanswered question dicts.

    Returns:
        Bullet list string.
    """
    return "\n".join(
        f"- [{q.get('category', 'UNKNOWN')}] {q.get('question', '')}"
        for q in questions
    )

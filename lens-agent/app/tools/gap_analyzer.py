"""Gap question generation for Lens architecture reviews.

Analyses submitted architecture evidence and generates targeted clarifying
questions across all gap categories. Never repeats answered questions.
Never asks about information already present in the evidence.
Returns at most MAX_QUESTIONS_PER_ROUND questions per call.
"""
from __future__ import annotations

import json
import logging

from app.llm.client import get_llm_client

logger = logging.getLogger(__name__)

# Maximum questions returned per elicitation round.
# Keeps each round digestible for the user.
MAX_QUESTIONS_PER_ROUND = 8

GAP_CATEGORIES = [
    "RELIABILITY",
    "SECURITY",
    "COST",
    "OPERATIONS",
    "PERFORMANCE",
    "MODIFIABILITY",
    "INTEGRABILITY",
    "DATA",
    "STRUCTURAL",
    "GOVERNANCE",
]


def generate_gap_questions(
    session_id: str,
    evidence: list[dict],
    previous_questions: list[dict],
    answers: list[dict],
    round: int,
) -> list[dict]:
    """
    Generate targeted gap questions based on submitted evidence.

    Synchronous wrapper around the async implementation so the FastAPI
    route can call it without an explicit await at the route level.
    This is intentional — the route currently uses a sync call pattern.
    For production, migrate the route to async and call the async version.

    Args:
        session_id: Review session identifier.
        evidence: All evidence submitted so far.
        previous_questions: All questions from prior rounds.
        answers: All answers provided so far.
        round: Current round number (1-indexed).

    Returns:
        List of gap question dicts with keys: category, question, rationale.
    """
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # We are inside an async context (FastAPI) — use a thread
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, _generate_gap_questions_async(
                    session_id, evidence, previous_questions, answers, round
                ))
                return future.result()
        else:
            return loop.run_until_complete(_generate_gap_questions_async(
                session_id, evidence, previous_questions, answers, round
            ))
    except Exception as exc:
        logger.error("gap_analyzer: failed to generate questions session=%s error=%s", session_id, exc)
        return []


async def _generate_gap_questions_async(
    session_id: str,
    evidence: list[dict],
    previous_questions: list[dict],
    answers: list[dict],
    round: int,
) -> list[dict]:
    """
    Async implementation of gap question generation.

    Args:
        session_id: Review session identifier.
        evidence: All evidence submitted so far.
        previous_questions: All questions from prior rounds.
        answers: All answers provided so far.
        round: Current round number (1-indexed).

    Returns:
        List of gap question dicts.
    """
    evidence_text = _format_evidence(evidence)
    answered_topics = _summarise_answered_topics(previous_questions, answers)

    prompt = f"""You are an expert architecture reviewer performing gap analysis.

You are reviewing an architecture and need to identify missing information
that would be required to perform a thorough review against:
- Azure Well-Architected Framework (5 pillars)
- SEI ATAM principles
- SEI quality attribute principles
- Structural health principles

## Submitted Architecture Evidence

{evidence_text}

## Already Answered Topics (DO NOT ask about these again)

{answered_topics if answered_topics else 'None — this is round 1.'}

## Your Task

Generate up to {MAX_QUESTIONS_PER_ROUND} targeted clarifying questions that:
1. Focus on information MISSING from the evidence above
2. Cover the most critical gaps first
3. Span multiple gap categories where possible
4. Never duplicate a topic already answered
5. Are specific and answerable — not vague

Gap categories to consider: {', '.join(GAP_CATEGORIES)}

This is round {round} of elicitation. Focus on the most important missing
areas that would most impact the architecture review quality.

Return a JSON object with this exact structure:
{{
  "questions": [
    {{
      "category": "SECURITY",
      "question": "What authentication mechanism is used for service-to-service communication?",
      "rationale": "Service-to-service auth is not mentioned in the evidence. Without this, the Security pillar of the Azure WAF cannot be properly evaluated and the SEI security tactics assessment will be incomplete."
    }}
  ]
}}

Return at most {MAX_QUESTIONS_PER_ROUND} questions. Return fewer if the evidence is already comprehensive.
"""

    client = get_llm_client()
    try:
        raw = await client.complete(
            prompt=prompt,
            response_format="json",
            stage_name="gap_analysis",
        )
        data = json.loads(raw)
        questions = data.get("questions", [])
        # Enforce the cap defensively
        return questions[:MAX_QUESTIONS_PER_ROUND]
    except Exception as exc:
        logger.error(
            "gap_analyzer: LLM call failed session=%s round=%d error=%s",
            session_id, round, exc
        )
        return []


def _format_evidence(evidence: list[dict]) -> str:
    """
    Format evidence items into a readable text block for the prompt.

    Args:
        evidence: List of evidence dicts.

    Returns:
        Formatted string representation.
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


def _summarise_answered_topics(questions: list[dict], answers: list[dict]) -> str:
    """
    Build a summary of already-answered question topics.

    Args:
        questions: All questions from prior rounds.
        answers: All answers provided.

    Returns:
        Bullet list of answered topics, or empty string if none.
    """
    answered_ids = {a.get("question_id") or a.get("questionId") for a in answers}
    answered_questions = [
        q for q in questions
        if q.get("id") in answered_ids or q.get("answered") is True
    ]
    if not answered_questions:
        # Fall back: if questions have answers embedded, use those
        answered_questions = [q for q in questions if q.get("answer")]

    if not answered_questions:
        return ""

    lines = []
    for q in answered_questions:
        category = q.get("category", "")
        question = q.get("question", "")
        lines.append(f"- [{category}] {question}")
    return "\n".join(lines)

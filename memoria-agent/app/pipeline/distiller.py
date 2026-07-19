"""Automatic distillation pipeline."""
from __future__ import annotations

import json
import logging
import os
import re

from app.llm.client import get_llm_client
from app.models.contracts import DistillRequest, DistillResponse, MemoryCandidate
from app.tools.conflict_detector import _overlap, _tokens, detect_conflicts
from app.tools.fact_extractor import extract_facts

logger = logging.getLogger(__name__)

MAX_LLM_CANDIDATES = 30
MAX_SESSION_TEXT_CHARS = 6000
_MIN_TEXT_LEN_FOR_LLM = 200


async def distill(request: DistillRequest) -> DistillResponse:
    # Stage 1 — deterministic extraction (existing)
    deterministic_candidates = await extract_facts(
        session_summary=request.session_summary,
        session_payload=request.session_payload,
    )

    # Stage 2 — LLM extraction (new)
    # Only runs if OPENAI_API_KEY is set and session content is
    # non-trivial (> 200 chars of text). Falls back gracefully if
    # the LLM call fails — never blocks distillation.
    llm_candidates: list[MemoryCandidate] = []
    session_text = _build_session_text(request)
    if len(session_text) > _MIN_TEXT_LEN_FOR_LLM and os.getenv("OPENAI_API_KEY"):
        try:
            llm_candidates = await _llm_extract(
                session_text=session_text,
                existing_entries=request.existing_entries,
                pillar=request.pillar,
            )
        except Exception as exc:
            logger.warning(
                "LLM extraction failed for session=%s error=%s — "
                "proceeding with deterministic candidates only.",
                request.session_id,
                str(exc)[:200],
            )

    # Merge: deterministic candidates take precedence.
    # LLM candidates are added only if they do not duplicate an
    # already-extracted candidate by content similarity.
    all_candidates = _merge_candidates(deterministic_candidates, llm_candidates)

    # Stage 3 — conflict detection (existing)
    conflicts = await detect_conflicts(all_candidates, request.existing_entries)

    return DistillResponse(
        session_id=request.session_id,
        candidates=all_candidates,
        conflicts=conflicts,
        message=(
            f"Extracted {len(deterministic_candidates)} deterministic + "
            f"{len(llm_candidates)} LLM candidates. "
            f"{len(conflicts)} conflict(s) detected."
        ),
    )


async def _llm_extract(
    session_text: str,
    existing_entries: list[dict],
    pillar: str,
) -> list[MemoryCandidate]:
    """Call the LLM to extract memory candidates from session content.

    The prompt instructs the model to extract only what is explicitly
    stated or directly implied in the text — never to hallucinate.
    Each candidate must have a clear evidence quote from the session.

    Returns at most MAX_LLM_CANDIDATES candidates.
    """
    truncated_text = session_text[:MAX_SESSION_TEXT_CHARS]

    existing_contents = [
        str(entry.get("content", ""))
        for entry in existing_entries[:20]
        if entry.get("content")
    ]
    existing_block = "\n".join(existing_contents) if existing_contents else "(none)"

    prompt = f"""You are extracting architectural knowledge from a software architecture session. Extract memory candidates — discrete, self-contained facts that would be useful to preserve in a project knowledge base.

PILLAR: {pillar}

SESSION CONTENT:
{truncated_text}

EXISTING KNOWLEDGE (do not re-extract these):
{existing_block}

INSTRUCTIONS:
Extract only information explicitly stated or directly implied.
Never hallucinate or invent details not present in the text.
Each candidate must be a single, self-contained fact.
Include a source_excerpt: a verbatim quote (max 200 chars) from the session text that supports this candidate.
Classify each candidate with the most specific type that applies.

TYPES:
DECISION — an architectural choice that was made
REQUIREMENT — something the system must do or be
RISK — a threat, vulnerability, or identified concern
QUALITY_SCORE — a measured or assessed quality attribute value
ASSUMPTION — a premise accepted without full verification
CONSTRAINT — a limit that restricts the solution space

Return a JSON object with this exact structure:
{{
  "candidates": [
    {{
      "memory_type": "DECISION",
      "content": "The team decided to use PostgreSQL for the order service.",
      "rationale": "Chosen for ACID compliance and existing team expertise.",
      "confidence": "HIGH",
      "source_excerpt": "decided to use PostgreSQL for the order service",
      "tags": ["postgresql", "database", "order-service"]
    }}
  ]
}}
Return at most {MAX_LLM_CANDIDATES} candidates.
Return fewer if the content does not contain that many distinct facts."""

    client = get_llm_client()
    raw = await client.complete(prompt, response_format="json")

    parsed = json.loads(raw)
    raw_candidates = parsed.get("candidates", [])

    result: list[MemoryCandidate] = []
    for item in raw_candidates:
        if not isinstance(item, dict):
            continue
        content = str(item.get("content", "")).strip()
        if not content:
            continue
        result.append(
            MemoryCandidate(
                memory_type=str(item.get("memory_type", "DECISION")),
                content=content,
                rationale=str(item.get("rationale", "Extracted by LLM from session content.")),
                confidence=str(item.get("confidence", "MEDIUM")),
                source_excerpt=str(item.get("source_excerpt", ""))[:200] or None,
                tags=[str(tag).strip().lower() for tag in item.get("tags", []) if str(tag).strip()][:8],
            )
        )
    return result[:MAX_LLM_CANDIDATES]


def _merge_candidates(
    deterministic: list[MemoryCandidate],
    llm: list[MemoryCandidate],
) -> list[MemoryCandidate]:
    """Merge LLM candidates into deterministic candidates.

    Deterministic candidates always take precedence. An LLM candidate
    is added only if no deterministic candidate has >= 0.70 token
    overlap with it. This prevents LLM paraphrases of already-extracted
    facts from polluting the candidate list.
    """
    if not llm:
        return list(deterministic)

    det_token_sets = [_tokens(c.content) for c in deterministic]
    merged = list(deterministic)
    for candidate in llm:
        candidate_tokens = _tokens(candidate.content)
        duplicate = any(
            _overlap(candidate_tokens, det_tokens) >= 0.70
            for det_tokens in det_token_sets
        )
        if not duplicate:
            merged.append(candidate)
            det_token_sets.append(candidate_tokens)
    return merged


def _build_session_text(request: DistillRequest) -> str:
    """Build a single text string from the session summary and payload
    for LLM extraction.

    Flattens structured payload fields into readable prose. Includes
    the session summary first, then key payload fields. Truncates to
    MAX_SESSION_TEXT_CHARS characters.
    """
    parts: list[str] = []
    if request.session_summary and request.session_summary.strip():
        parts.append(f"SUMMARY:\n{request.session_summary.strip()}")

    if request.session_payload:
        _collect_text_fields(request.session_payload, parts, depth=0)

    text = "\n\n".join(parts)
    return text[:MAX_SESSION_TEXT_CHARS]


_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
_NUMERIC_RE = re.compile(r"^-?\d+(\.\d+)?$")


def _collect_text_fields(obj: object, parts: list[str], depth: int) -> None:
    """Recursively walk a dict/list and collect meaningful string values."""
    if depth > 6:
        return
    if isinstance(obj, dict):
        for key, value in obj.items():
            if isinstance(value, str):
                stripped = value.strip()
                if (
                    len(stripped) > 20
                    and not _UUID_RE.match(stripped)
                    and not _NUMERIC_RE.match(stripped)
                ):
                    label = str(key).replace("_", " ").upper()
                    parts.append(f"{label}:\n{stripped}")
            else:
                _collect_text_fields(value, parts, depth + 1)
    elif isinstance(obj, list):
        for item in obj:
            _collect_text_fields(item, parts, depth + 1)

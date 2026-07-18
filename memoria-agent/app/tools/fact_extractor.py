"""Deterministic Phase 3 fact extraction.

The first automatic distiller intentionally avoids hard runtime dependence on an
LLM key. It extracts memory candidates from structured payload fields and
labelled prose. Model-backed extraction can be layered behind this contract
later without changing memoria-api.
"""

from __future__ import annotations

import re
from typing import Any

from app.models.contracts import MemoryCandidate


TYPE_KEYWORDS = {
    "DECISION": ("decision", "decided", "choose", "chosen", "use ", "selected"),
    "REQUIREMENT": ("requirement", "must", "shall", "needs to", "should"),
    "RISK": ("risk", "failure", "threat", "vulnerability", "gap"),
    "QUALITY_SCORE": ("score", "rating", "waf", "sei", "atam", "quality"),
    "ASSUMPTION": ("assumption", "assume", "assuming"),
    "CONSTRAINT": ("constraint", "cannot", "limited", "bound", "compliance"),
}

FIELD_TYPE_HINTS = {
    "decisions": "DECISION",
    "architecture_decisions": "DECISION",
    "requirements": "REQUIREMENT",
    "risks": "RISK",
    "fmea_risks": "RISK",
    "quality_scores": "QUALITY_SCORE",
    "waf_scores": "QUALITY_SCORE",
    "assumptions": "ASSUMPTION",
    "constraints": "CONSTRAINT",
}


async def extract_facts(session_summary: str | None = None, session_payload: dict | None = None) -> list[MemoryCandidate]:
    candidates: list[MemoryCandidate] = []
    payload = session_payload or {}

    for key, value in payload.items():
        hinted_type = FIELD_TYPE_HINTS.get(key.lower())
        candidates.extend(_extract_from_value(value, hinted_type, key))

    if session_summary and session_summary.strip():
        candidates.extend(_extract_from_text(session_summary))
        candidates.append(
            MemoryCandidate(
                memory_type="SESSION_SUMMARY",
                content=_compact(session_summary, 1200),
                rationale="Automatic session summary captured for lineage; not intended for context injection.",
                confidence="MEDIUM",
                source_excerpt=_compact(session_summary, 500),
                tags=["session-summary"],
            )
        )

    return _dedupe(candidates)


def _extract_from_value(value: Any, hinted_type: str | None, source_key: str) -> list[MemoryCandidate]:
    if value is None:
        return []
    if isinstance(value, list):
        candidates: list[MemoryCandidate] = []
        for item in value:
            candidates.extend(_extract_from_value(item, hinted_type, source_key))
        return candidates
    if isinstance(value, dict):
        memory_type = hinted_type or _infer_type(" ".join(str(v) for v in value.values()))
        content = _first_text(value, ("content", "decision", "requirement", "risk", "title", "description", "summary"))
        if not content:
            nested: list[MemoryCandidate] = []
            for child_key, child_value in value.items():
                nested.extend(_extract_from_value(child_value, FIELD_TYPE_HINTS.get(child_key.lower()) or hinted_type, child_key))
            return nested
        rationale = _first_text(value, ("rationale", "reason", "context", "evidence", "impact")) or f"Extracted from {source_key}."
        return [
            MemoryCandidate(
                memory_type=memory_type,
                content=_compact(content),
                rationale=_compact(rationale),
                confidence=_confidence(value),
                source_excerpt=_compact(str(value), 500),
                tags=_tags(value, memory_type, source_key),
            )
        ]
    if isinstance(value, str):
        return _extract_from_text(value, hinted_type)
    return []


def _extract_from_text(text: str, hinted_type: str | None = None) -> list[MemoryCandidate]:
    candidates: list[MemoryCandidate] = []
    for statement in _statements(text):
        memory_type = _label_type(statement) or hinted_type or _infer_type(statement)
        if not memory_type:
            continue
        candidates.append(
            MemoryCandidate(
                memory_type=memory_type,
                content=_strip_label(statement),
                rationale="Extracted from labelled or keyword-bearing session text.",
                confidence="MEDIUM",
                source_excerpt=_compact(statement, 500),
                tags=_keyword_tags(statement, memory_type),
            )
        )
    return candidates


def _infer_type(text: str) -> str | None:
    label_type = _label_type(text)
    if label_type:
        return label_type
    normalized = text.lower()
    for memory_type, keywords in TYPE_KEYWORDS.items():
        if any(keyword in normalized for keyword in keywords):
            return memory_type
    return None


def _label_type(text: str) -> str | None:
    normalized = text.lower()
    label_match = re.match(r"^\s*(decision|requirement|risk|assumption|constraint|quality score)\s*[:\-]", normalized)
    if label_match:
        return label_match.group(1).upper().replace(" ", "_")
    return None


def _statements(text: str) -> list[str]:
    rough = re.split(r"[\n\r]+|(?<=[.!?])\s+(?=[A-Z])", text)
    return [_compact(part) for part in rough if len(part.strip()) >= 20]


def _strip_label(value: str) -> str:
    return re.sub(r"^\s*(decision|requirement|risk|assumption|constraint|quality score)\s*[:\-]\s*", "", value.strip(), flags=re.I)


def _first_text(value: dict, keys: tuple[str, ...]) -> str | None:
    for key in keys:
        candidate = value.get(key)
        if isinstance(candidate, str) and candidate.strip():
            return candidate
    return None


def _confidence(value: dict) -> str:
    raw = str(value.get("confidence", "")).upper()
    return raw if raw in {"HIGH", "MEDIUM", "LOW", "INFERRED"} else "MEDIUM"


def _tags(value: dict, memory_type: str, source_key: str) -> list[str]:
    raw_tags = value.get("tags")
    if isinstance(raw_tags, list):
        return [str(tag).strip().lower() for tag in raw_tags if str(tag).strip()][:8]
    return _keyword_tags(f"{source_key} {value}", memory_type)


def _keyword_tags(text: str, memory_type: str) -> list[str]:
    tags = {memory_type.lower().replace("_", "-")}
    for token in re.findall(r"[A-Za-z][A-Za-z0-9-]{3,}", text.lower()):
        if token not in {"this", "that", "with", "from", "have", "will", "must", "should", "architecture"}:
            tags.add(token)
        if len(tags) >= 8:
            break
    return sorted(tags)


def _compact(value: str, limit: int = 1000) -> str:
    normalized = re.sub(r"\s+", " ", value).strip()
    return normalized if len(normalized) <= limit else normalized[: limit - 3].rstrip() + "..."


def _dedupe(candidates: list[MemoryCandidate]) -> list[MemoryCandidate]:
    seen: set[tuple[str, str]] = set()
    unique: list[MemoryCandidate] = []
    for candidate in candidates:
        key = (candidate.memory_type, candidate.content.lower())
        if key not in seen:
            seen.add(key)
            unique.append(candidate)
    return unique

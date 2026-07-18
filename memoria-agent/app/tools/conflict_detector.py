"""Deterministic conflict and supersession detection for memory candidates."""

from __future__ import annotations

import re

from app.models.contracts import ConflictFlag, MemoryCandidate


async def detect_conflicts(candidates: list[MemoryCandidate], existing_entries: list[dict]) -> list[ConflictFlag]:
    conflicts: list[ConflictFlag] = []
    for index, candidate in enumerate(candidates):
        if candidate.memory_type == "SESSION_SUMMARY":
            continue
        candidate_tokens = _tokens(candidate.content)
        candidate_tags = {tag.lower() for tag in candidate.tags}
        for entry in existing_entries:
            entry_id = str(entry.get("id", ""))
            if not entry_id:
                continue
            if str(entry.get("memoryType") or entry.get("memory_type") or "").upper() != candidate.memory_type:
                continue
            entry_content = str(entry.get("content", ""))
            overlap = _overlap(candidate_tokens, _tokens(entry_content))
            entry_tags = {str(tag).lower() for tag in entry.get("tags") or []}
            shared_tags = candidate_tags.intersection(entry_tags)
            if _same_subject_replacement(candidate.content, entry_content) or (overlap >= 0.55 and shared_tags):
                conflicts.append(
                    ConflictFlag(
                        existing_entry_id=entry_id,
                        new_candidate_index=index,
                        conflict_description="New session fact appears to replace an active memory entry.",
                        supersedes=True,
                    )
                )
                break
    return conflicts


def _tokens(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9][a-z0-9-]{2,}", value.lower())
        if token not in {"the", "and", "for", "with", "from", "that", "this", "will", "must", "should"}
    }


def _overlap(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left.intersection(right)) / max(len(left), len(right))


def _same_subject_replacement(new_content: str, old_content: str) -> bool:
    new = new_content.lower()
    old = old_content.lower()
    replacement_markers = ("instead of", "replaces", "supersedes", "no longer", "rather than")
    if any(marker in new for marker in replacement_markers):
        return _overlap(_tokens(new), _tokens(old)) >= 0.25
    return False

"""Deterministic conflict and supersession detection for memory candidates."""

from __future__ import annotations

import re

from app.models.contracts import ConflictFlag, MemoryCandidate

# Minimum content length required before overlap-based supersession is considered.
# Short entries have too few tokens for overlap to be statistically meaningful.
# Only explicit replacement language can trigger supersession for short content.
MIN_CONTENT_LEN_FOR_OVERLAP = 40

# Minimum token overlap ratio required to flag a candidate as superseding an
# existing entry. Set high (0.80) to avoid false positives between distinct
# decisions about the same technology (e.g. "Use Redis for caching" vs
# "Use Redis for rate limiting" share many tokens but are different decisions).
OVERLAP_THRESHOLD = 0.80

# Minimum number of shared tags required alongside high overlap.
# Requiring at least 2 shared tags prevents a single shared technology tag
# (e.g. "postgresql") from triggering supersession for unrelated decisions.
MIN_SHARED_TAGS = 2


async def detect_conflicts(
    candidates: list[MemoryCandidate],
    existing_entries: list[dict],
) -> list[ConflictFlag]:
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
            if (
                str(entry.get("memoryType") or entry.get("memory_type") or "").upper()
                != candidate.memory_type
            ):
                continue
            entry_content = str(entry.get("content", ""))

            # Explicit replacement language always triggers supersession
            # regardless of content length or overlap score.
            if _same_subject_replacement(candidate.content, entry_content):
                conflicts.append(
                    ConflictFlag(
                        existing_entry_id=entry_id,
                        new_candidate_index=index,
                        conflict_description=(
                            "New session fact uses explicit replacement language "
                            "and appears to supersede an active memory entry."
                        ),
                        supersedes=True,
                    )
                )
                break

            # Short entries are skipped for overlap-based detection — token
            # sets are too small to produce meaningful overlap ratios.
            if (
                len(candidate.content) < MIN_CONTENT_LEN_FOR_OVERLAP
                or len(entry_content) < MIN_CONTENT_LEN_FOR_OVERLAP
            ):
                continue

            overlap = _overlap(candidate_tokens, _tokens(entry_content))
            entry_tags = {str(tag).lower() for tag in entry.get("tags") or []}
            shared_tags = candidate_tags.intersection(entry_tags)

            if overlap >= OVERLAP_THRESHOLD and len(shared_tags) >= MIN_SHARED_TAGS:
                conflicts.append(
                    ConflictFlag(
                        existing_entry_id=entry_id,
                        new_candidate_index=index,
                        conflict_description=(
                            f"New session fact has {overlap:.0%} token overlap and "
                            f"{len(shared_tags)} shared tags with an active memory "
                            "entry — likely a replacement."
                        ),
                        supersedes=True,
                    )
                )
                break
    return conflicts


def _tokens(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9][a-z0-9-]{2,}", value.lower())
        if token
        not in {
            "the", "and", "for", "with", "from", "that", "this",
            "will", "must", "should", "use", "our", "all",
        }
    }


def _overlap(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left.intersection(right)) / max(len(left), len(right))


def _same_subject_replacement(new_content: str, old_content: str) -> bool:
    new = new_content.lower()
    old = old_content.lower()
    replacement_markers = (
        "instead of",
        "replaces",
        "supersedes",
        "no longer",
        "rather than",
    )
    if any(marker in new for marker in replacement_markers):
        return _overlap(_tokens(new), _tokens(old)) >= 0.25
    return False

from __future__ import annotations

from dataclasses import dataclass


async def assess_gap_resolution(
    session_id: str,
    questions: list[dict],
    answers: list[dict],
    round: int,
    max_rounds: int,
) -> dict:
    return {
        "resolved": True,
        "canProceed": True if round >= max_rounds else True,
        "remainingCount": 0,
        "unresolvableGaps": [],
        "summary": "Proceed with review.",
    }

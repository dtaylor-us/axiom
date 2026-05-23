"""
Quality attribute elicitor for the Quality Attribute Workshop.

Responsible for deciding whether sufficient evidence exists to derive
quality attributes, and for applying confidence constraints based on
the current gap state.

This module enforces the ask-before-assert principle at the logic
level. The node layer (nodes.py) calls into this module to determine
whether elicitation should proceed.

Not part of the pipeline domain. Does not import from app.pipeline.
"""

from __future__ import annotations

import logging

from app.workshop.context import (
    ElicitedAttribute,
    InformationGap,
    WorkshopContext,
)

logger = logging.getLogger(__name__)

# Minimum number of confirmed attributes needed before the session
# should transition to the attribute_consolidation phase.
MIN_ATTRIBUTES_FOR_CONSOLIDATION = 3

# Category weights for gap completeness scoring.
# Business context is the most critical because quality attribute
# priority cannot be established without knowing why the system exists.
_GAP_CATEGORY_WEIGHTS: dict[str, float] = {
    "business_context":  0.40,
    "usage_context":     0.25,
    "technical_context": 0.20,
    "risk_priority":     0.15,
}


def open_critical_gaps(gaps: list[InformationGap]) -> list[InformationGap]:
    """
    Return all gaps with critical priority that are not yet filled.

    Args:
        gaps: Full gap list from WorkshopContext.

    Returns:
        List of unfilled critical gaps.
    """
    return [g for g in gaps if not g.filled and g.priority == "critical"]


def can_elicit(ctx: WorkshopContext) -> bool:
    """
    Determine whether elicitation may proceed for this turn.

    Elicitation is blocked when:
      - The session is in an early phase (input_analysis or business_context)
      - Any critical gap is still open

    Args:
        ctx: Current WorkshopContext.

    Returns:
        True if the agent may attempt attributing derivation.
    """
    early_phases = {"input_analysis", "business_context", "usage_context"}
    if ctx.workshop_phase in early_phases:
        logger.debug(
            "Elicitation blocked: early phase=%s session=%s",
            ctx.workshop_phase,
            ctx.session_id,
        )
        return False

    critical_open = open_critical_gaps(ctx.gaps)
    if critical_open:
        logger.debug(
            "Elicitation blocked: %d critical gaps open session=%s",
            len(critical_open),
            ctx.session_id,
        )
        return False

    return True


def cap_confidence(
    raw_confidence: str,
    ctx: WorkshopContext,
) -> str:
    """
    Cap attribute confidence based on the current gap state.

    While critical gaps remain open, confidence cannot exceed
    'tentative'. This enforces the principle that the agent
    cannot assert attributes without sufficient evidence.

    Args:
        raw_confidence: Confidence value proposed by the LLM.
        ctx:            Current WorkshopContext.

    Returns:
        The effective confidence value, possibly downgraded.
    """
    if open_critical_gaps(ctx.gaps) and raw_confidence != "tentative":
        logger.debug(
            "Confidence capped from %s to tentative — critical gaps open. session=%s",
            raw_confidence,
            ctx.session_id,
        )
        return "tentative"
    return raw_confidence


def weighted_gap_completion(ctx: WorkshopContext) -> float:
    """
    Calculate a weighted gap completion score across all categories.

    Weights business_context most heavily because quality attribute
    prioritisation depends on understanding the business mission.

    Args:
        ctx: Current WorkshopContext.

    Returns:
        Float between 0.0 and 1.0 representing weighted completion.
    """
    if not ctx.gaps:
        return 0.0

    score = 0.0
    for category, weight in _GAP_CATEGORY_WEIGHTS.items():
        category_gaps = [g for g in ctx.gaps if g.category == category]
        if not category_gaps:
            # No gaps identified in this category yet — treat as unknown.
            continue
        filled_count = sum(1 for g in category_gaps if g.filled)
        category_completion = filled_count / len(category_gaps)
        score += category_completion * weight

    return min(score, 1.0)


def attributes_needing_measures(
    attributes: list[ElicitedAttribute],
) -> list[ElicitedAttribute]:
    """
    Return attributes whose scenarios are missing a response measure.

    These are the attributes that most need the next turn's questions
    to focus on measurability rather than more feature elicitation.

    Args:
        attributes: All elicited attributes from WorkshopContext.

    Returns:
        Attributes with at least one scenario in needs_measure state.
    """
    return [
        a for a in attributes
        if any(sc.completeness == "needs_measure" for sc in a.scenarios)
    ]

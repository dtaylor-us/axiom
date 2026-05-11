"""
Context budget manager for the Quality Attribute Workshop.

Prevents context explosion by enforcing token and turn limits before
assembling the prompt sent to the LLM on each turn. When the full
accumulated context would exceed MAX_CONTEXT_TOKENS, a summarised
view is returned instead.

The manager is a pure utility module — it has no state and makes no
LLM calls. It is called by the workshop agent nodes before building prompts.

Boundary: does NOT import from app.pipeline or app.tools (ADL-001).
"""

from __future__ import annotations

import logging

from app.workshop.context import WorkshopContext

logger = logging.getLogger(__name__)

# Hard token budget for the full context payload sent to the LLM.
# This is a conservative character-based estimate (1 token ≈ 4 chars).
# When the estimate exceeds this, _summarised_context_dict is used instead.
MAX_CONTEXT_TOKENS: int = 60_000

# Maximum raw input characters accumulated across all turns.
# Inputs beyond this length are truncated in prompts (but stored in full).
MAX_RAW_INPUT_CHARS: int = 20_000

# Number of recent turns included verbatim in the prompt.
# Older turns are reduced to a one-line digest.
MAX_TURNS_IN_FULL: int = 5

# Maximum length of a single user input before a warning is issued.
# The input is never blocked — only a warning is surfaced to the caller.
MAX_SINGLE_INPUT_CHARS: int = 3_000


def estimate_context_size(context: WorkshopContext) -> int:
    """
    Estimate the token count of the full serialised context.

    Uses character count / 4 as a proxy for token count.
    Only counts the fields that are included in LLM prompts.

    Args:
        context: Current WorkshopContext.

    Returns:
        Estimated token count (integer).
    """
    char_count = 0

    # System name and phase are small constants.
    char_count += len(context.system_name) + len(context.workshop_phase)

    # Raw inputs — the primary driver of context growth.
    for inp in context.raw_inputs:
        char_count += len(inp)

    # Gap descriptions + questions.
    for g in context.gaps:
        char_count += len(g.description)
        for q in g.questions:
            char_count += len(q)

    # Attribute descriptions + scenarios.
    for a in context.attributes:
        char_count += len(a.name) + len(a.description)
        for sc in a.scenarios:
            char_count += (
                len(sc.stimulus) + len(sc.response) + len(sc.response_measure)
            )

    # Turn history — agent responses can be verbose.
    for t in context.turns:
        char_count += len(t.user_input) + len(t.agent_response)

    return char_count // 4


def prepare_context_for_prompt(context: WorkshopContext) -> dict:
    """
    Return a context dictionary sized to fit within MAX_CONTEXT_TOKENS.

    When the estimated size is within budget, the full context dict is
    returned. When over budget, a summarised view is returned that:
      - truncates old raw_inputs to a digest
      - keeps only the MAX_TURNS_IN_FULL most recent turns in full
      - reduces older turns to a one-line summary

    Args:
        context: Current WorkshopContext.

    Returns:
        Dict safe to pass to load_prompt as template variables.
    """
    estimated = estimate_context_size(context)

    if estimated <= MAX_CONTEXT_TOKENS:
        return _full_context_dict(context)

    logger.warning(
        "Context size %d tokens exceeds budget %d — using summarised view. "
        "session=%s",
        estimated,
        MAX_CONTEXT_TOKENS,
        context.session_id,
    )
    return _summarised_context_dict(context)


def validate_input_size(user_input: str) -> tuple[bool, str]:
    """
    Check whether a single user input exceeds the per-input limit.

    Does not block the input — returns a flag and a warning message
    so the caller can surface it in the UI.

    Args:
        user_input: The raw text provided by the user.

    Returns:
        Tuple of (is_oversized: bool, warning_message: str).
        warning_message is empty when is_oversized is False.
    """
    if len(user_input) <= MAX_SINGLE_INPUT_CHARS:
        return False, ""

    return True, (
        f"Your message is {len(user_input):,} characters "
        f"(recommended: {MAX_SINGLE_INPUT_CHARS:,} or fewer). "
        "Long inputs may reduce response quality. "
        "Consider splitting into separate messages."
    )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _full_context_dict(context: WorkshopContext) -> dict:
    """Build the full context payload with no truncation."""
    return {
        "session_id":      context.session_id,
        "system_name":     context.system_name,
        "workshop_phase":  context.workshop_phase,
        "current_turn":    context.current_turn,
        "raw_inputs":      context.raw_inputs[-20:],  # last 20 entries max
        "gaps":            [g.model_dump() for g in context.gaps],
        "open_gaps":       context.open_gaps,
        "attributes":      [a.model_dump() for a in context.attributes],
        "turns":           [t.model_dump() for t in context.turns],
        "generation_count": context.generation_count,
        "attributes_stale": context.attributes_stale,
    }


def _summarised_context_dict(context: WorkshopContext) -> dict:
    """
    Build a compact context payload for over-budget sessions.

    Recent turns are kept verbatim; older turns become one-line digests.
    """
    recent_turns = context.turns[-MAX_TURNS_IN_FULL:]
    old_turns = context.turns[:-MAX_TURNS_IN_FULL]

    facts_digest = _build_facts_digest(context, old_turns)

    return {
        "session_id":      context.session_id,
        "system_name":     context.system_name,
        "workshop_phase":  context.workshop_phase,
        "current_turn":    context.current_turn,
        "raw_inputs":      context.raw_inputs[-3:],  # only the last 3 raw inputs
        "gaps":            [g.model_dump() for g in context.gaps if not g.filled],
        "open_gaps":       context.open_gaps,
        "attributes":      [a.model_dump() for a in context.attributes],
        "turns":           [t.model_dump() for t in recent_turns],
        "facts_digest":    facts_digest,
        "generation_count": context.generation_count,
        "attributes_stale": context.attributes_stale,
        "_context_summarised": True,
    }


def _build_facts_digest(
    context: WorkshopContext,
    old_turns: list,
) -> str:
    """
    Build a brief prose digest of facts established in older turns.

    Used in summarised mode to convey session history without including
    full turn transcripts.

    Args:
        context:   WorkshopContext (for filled gaps and confirmed attributes).
        old_turns: Turns that have been excluded from the full turn list.

    Returns:
        Multi-line digest string.
    """
    lines: list[str] = [
        f"System: {context.system_name}.",
        f"Workshop phase: {context.workshop_phase}.",
        f"Total turns: {context.current_turn} "
        f"(showing last {MAX_TURNS_IN_FULL} in full).",
    ]

    filled = [g for g in context.gaps if g.filled]
    if filled:
        lines.append(
            f"Filled gaps ({len(filled)}): "
            + ", ".join(g.description[:60] for g in filled[:5])
            + ("..." if len(filled) > 5 else "")
        )

    if context.attributes:
        attr_names = [a.name for a in context.attributes[:8]]
        lines.append(
            f"Identified attributes ({len(context.attributes)}): "
            + ", ".join(attr_names)
            + ("..." if len(context.attributes) > 8 else "")
        )

    if old_turns:
        lines.append(
            f"Earlier turns summary ({len(old_turns)} turns): "
            + " | ".join(
                f"T{t.turn_number}: {(t.user_input or '')[:80]}"
                for t in old_turns[-3:]
            )
        )

    return "\n".join(lines)

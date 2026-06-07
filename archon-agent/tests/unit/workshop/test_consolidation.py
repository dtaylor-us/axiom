"""Unit tests for ConsolidationEngine (app.workshop.consolidator)."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.workshop.consolidator import ConsolidationEngine, MAX_ATTRIBUTES
from app.workshop.context import ElicitedAttribute, QAScenario, WorkshopContext

MIN_FOR_MERGE = 6


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_attr(
    name: str,
    importance: str = "medium",
    confidence: str = "inferred",
    response_measure: str = "",
    canonical_name: str | None = None,
) -> ElicitedAttribute:
    scenarios: list[QAScenario] = []
    if response_measure:
        scenarios.append(QAScenario(
            scenario_id=str(uuid.uuid4()),
            stimulus="stimulus text long enough here",
            source="source text long enough here",
            environment="environment text long",
            artifact="artifact text long",
            response="response text long enough",
            response_measure=response_measure,
        ))
    return ElicitedAttribute(
        attribute_id=str(uuid.uuid4()),
        name=name,
        category="other",
        importance=importance,
        confidence=confidence,
        description=f"{name} description",
        evidence_quotes=[f"User said {name}"],
        canonical_name=canonical_name or name.lower(),
        scenarios=scenarios,
    )


def _pad_attrs(attrs: list[ElicitedAttribute], n: int = MIN_FOR_MERGE) -> list[ElicitedAttribute]:
    """Consolidation runs only when attribute count meets the minimum threshold."""
    out = list(attrs)
    i = 0
    while len(out) < n:
        out.append(_make_attr(f"_padding_attr_{i}"))
        i += 1
    return out


def _make_context(attrs: list[ElicitedAttribute]) -> WorkshopContext:
    if len(attrs) == 0:
        merged: list[ElicitedAttribute] = []
    elif len(attrs) < MIN_FOR_MERGE:
        merged = _pad_attrs(attrs)
    else:
        merged = attrs
    return WorkshopContext(
        session_id=str(uuid.uuid4()),
        user_id="test-user",
        system_name="TestSystem",
        current_turn=3,
        attributes=merged,
    )


def _make_engine() -> ConsolidationEngine:
    mock_llm = MagicMock()
    engine = ConsolidationEngine(llm_client=mock_llm)
    return engine


async def _dedupe_passthrough(
    attrs: list[ElicitedAttribute],
    ctx: WorkshopContext,
) -> tuple[list[ElicitedAttribute], list]:
    """Simulate LLM dedupe returning the input list unchanged."""
    return attrs, []


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_alias_normalised_to_canonical():
    """'resilience' is an alias for 'availability' and should be normalised."""
    engine = _make_engine()
    engine._llm_deduplicate = AsyncMock(side_effect=_dedupe_passthrough)

    ctx = _make_context([_make_attr("resilience")])
    result = await engine.consolidate(ctx)

    assert any(a.canonical_name == "availability" for a in result.attributes)


@pytest.mark.asyncio
async def test_taxonomy_merge_same_canonical():
    """Two attributes with the same canonical category are merged into one."""
    engine = _make_engine()
    engine._llm_deduplicate = AsyncMock(side_effect=_dedupe_passthrough)

    attrs = [
        _make_attr("availability", importance="high", confidence="confirmed"),
        _make_attr("resilience", importance="medium", confidence="tentative"),
    ]
    ctx = _make_context(attrs)
    result = await engine.consolidate(ctx)

    canonical_names = [a.canonical_name for a in result.attributes]
    assert canonical_names.count("availability") == 1


@pytest.mark.asyncio
async def test_distinct_scenarios_not_merged():
    """Two attributes with different response measures are kept separate."""
    engine = _make_engine()
    engine._llm_deduplicate = AsyncMock(side_effect=_dedupe_passthrough)

    a1 = _make_attr("availability", response_measure="99.99% uptime")
    a1 = a1.model_copy(update={"canonical_name": "availability"})
    a2 = _make_attr("availability", response_measure="RTO < 4 hours")
    a2 = a2.model_copy(update={"canonical_name": "availability"})

    ctx = _make_context([a1, a2])
    result = await engine.consolidate(ctx)

    availability_count = sum(
        1 for a in result.attributes if a.canonical_name == "availability"
    )
    assert availability_count == 2


@pytest.mark.asyncio
async def test_llm_failure_fallback_does_not_crash():
    """When LLM deduplication fails, consolidation should still return a result."""
    engine = _make_engine()
    engine._llm.complete = AsyncMock(side_effect=Exception("LLM unavailable"))

    ctx = _make_context([_make_attr("performance")])

    result = await engine.consolidate(ctx)
    assert len(result.attributes) >= 0


@pytest.mark.asyncio
async def test_non_qa_separated():
    """Non-QA concepts are moved to non_qa_concerns, not kept in attributes."""
    engine = _make_engine()
    engine._llm_deduplicate = AsyncMock(side_effect=_dedupe_passthrough)

    gdpr_attr = _make_attr("gdpr")
    perf_attr = _make_attr("performance")
    ctx = _make_context([gdpr_attr, perf_attr])

    result = await engine.consolidate(ctx)

    attr_names = [a.name.lower() for a in result.attributes]
    assert "gdpr" not in attr_names
    assert any("gdpr" in str(c).lower() for c in result.non_qa_concerns)


@pytest.mark.asyncio
async def test_cap_enforced_at_max_attributes():
    """When attrs exceed MAX_ATTRIBUTES, lowest-importance are trimmed."""
    engine = _make_engine()
    engine._llm_deduplicate = AsyncMock(side_effect=_dedupe_passthrough)

    attrs = [
        _make_attr(f"unique_qa_{i}", importance="low")
        for i in range(MAX_ATTRIBUTES + 5)
    ]
    ctx = _make_context(attrs)
    result = await engine.consolidate(ctx)

    assert len(result.attributes) <= MAX_ATTRIBUTES


@pytest.mark.asyncio
async def test_consolidate_returns_new_context_not_mutated():
    """consolidate() returns a new context; original is not mutated."""
    engine = _make_engine()
    engine._llm_deduplicate = AsyncMock(side_effect=_dedupe_passthrough)

    original_attrs = [_make_attr("performance")]
    ctx = _make_context(original_attrs)
    original_id = id(ctx.attributes)

    result = await engine.consolidate(ctx)

    assert id(result.attributes) != original_id
    assert result.last_consolidated_turn == ctx.current_turn


@pytest.mark.asyncio
async def test_max_attributes_constant_is_12():
    """MAX_ATTRIBUTES must equal 12 per ADL-037."""
    assert MAX_ATTRIBUTES == 12


@pytest.mark.asyncio
async def test_empty_context_returns_unchanged():
    """consolidate() on an empty attribute list returns context unchanged."""
    engine = _make_engine()
    ctx = _make_context([])
    result = await engine.consolidate(ctx)

    assert result.attributes == []

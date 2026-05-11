"""Tests for MIN_ATTRIBUTES_FOR_CONSOLIDATION behaviour."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.workshop.consolidator import MIN_ATTRIBUTES_FOR_CONSOLIDATION
from app.workshop.context import ElicitedAttribute, WorkshopContext
from app.workshop.nodes import consolidation_node


def _attr(name: str) -> ElicitedAttribute:
    return ElicitedAttribute(
        attribute_id=str(uuid.uuid4()),
        name=name,
        category="other",
        importance="medium",
        confidence="tentative",
        description=name,
        evidence_quotes=["q"],
    )


@pytest.mark.asyncio
async def test_consolidation_node_skips_below_threshold() -> None:
    attrs = [_attr(f"a{i}") for i in range(MIN_ATTRIBUTES_FOR_CONSOLIDATION - 1)]
    ctx = WorkshopContext(
        session_id="s",
        user_id="u",
        current_turn=1,
        attributes=attrs,
    )
    mock_engine = MagicMock()
    mock_engine.consolidate = AsyncMock(return_value=ctx)
    config = {"configurable": {"consolidator": mock_engine}}
    out = await consolidation_node(ctx, config)
    mock_engine.consolidate.assert_not_called()
    assert out.attributes == attrs


@pytest.mark.asyncio
async def test_consolidation_node_runs_at_threshold() -> None:
    attrs = [_attr(f"a{i}") for i in range(MIN_ATTRIBUTES_FOR_CONSOLIDATION)]
    ctx = WorkshopContext(
        session_id="s",
        user_id="u",
        current_turn=2,
        attributes=attrs,
        last_consolidated_turn=None,
    )
    merged = WorkshopContext(
        session_id="s",
        user_id="u",
        current_turn=2,
        attributes=attrs[:3],
        last_consolidated_turn=2,
    )
    mock_engine = MagicMock()
    mock_engine.consolidate = AsyncMock(return_value=merged)
    config = {"configurable": {"consolidator": mock_engine}}
    out = await consolidation_node(ctx, config)
    mock_engine.consolidate.assert_awaited_once()
    assert out.last_consolidated_turn == 2

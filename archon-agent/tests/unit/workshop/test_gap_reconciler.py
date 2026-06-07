"""Unit tests for GapReconciler."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest

from app.workshop.context import InformationGap, WorkshopContext
from app.workshop.gap_reconciler import GapReconciler


def _ctx(gaps: list[InformationGap], *, turn: int = 2) -> WorkshopContext:
    return WorkshopContext(
        session_id="s1",
        user_id="u1",
        current_turn=turn,
        raw_inputs=["first turn context", "second turn regulatory detail"],
        gaps=gaps,
        open_gaps=[g.gap_id for g in gaps if not g.filled],
    )


@pytest.fixture
def llm() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def reconciler(llm: AsyncMock) -> GapReconciler:
    return GapReconciler(llm)


@pytest.mark.asyncio
async def test_reconcile_does_nothing_when_no_open_gaps(reconciler: GapReconciler) -> None:
    g = InformationGap(
        gap_id="g1",
        category="business_context",
        description="ctx",
        resolution_confidence=1.0,
    )
    ctx = _ctx([g])
    out = await reconciler.reconcile(ctx)
    assert out is ctx


@pytest.mark.asyncio
async def test_reconcile_updates_confidence_and_monotonic(
    reconciler: GapReconciler,
    llm: AsyncMock,
) -> None:
    llm.complete = AsyncMock(
        return_value=json.dumps({
            "gap_evaluations": [{
                "gap_id": "g1",
                "resolution_confidence": 0.8,
                "evidence_phrases": ["regulatory"],
                "residual_question": "cost of missing window?",
                "reasoning": "partial",
            }],
        }),
    )
    gap = InformationGap(
        gap_id="g1",
        category="business_context",
        description="business ctx",
        priority="high",
        resolution_confidence=0.4,
    )
    ctx = _ctx([gap])
    out = await reconciler.reconcile(ctx)
    g = out.gaps[0]
    assert g.resolution_confidence == 0.8
    assert "regulatory" in g.resolution_evidence
    assert g.residual_question.startswith("cost")


@pytest.mark.asyncio
async def test_reconcile_monotonic_increase_only(
    reconciler: GapReconciler,
    llm: AsyncMock,
) -> None:
    llm.complete = AsyncMock(
        return_value=json.dumps({
            "gap_evaluations": [{
                "gap_id": "g1",
                "resolution_confidence": 0.2,
                "evidence_phrases": [],
                "residual_question": "",
                "reasoning": "noise",
            }],
        }),
    )
    gap = InformationGap(
        gap_id="g1",
        category="business_context",
        description="ctx",
        resolution_confidence=0.55,
    )
    ctx = _ctx([gap])
    out = await reconciler.reconcile(ctx)
    assert out.gaps[0].resolution_confidence == 0.55


@pytest.mark.asyncio
async def test_critical_threshold_requires_point_nine(
    reconciler: GapReconciler,
    llm: AsyncMock,
) -> None:
    llm.complete = AsyncMock(
        return_value=json.dumps({
            "gap_evaluations": [{
                "gap_id": "g1",
                "resolution_confidence": 0.85,
                "evidence_phrases": ["x"],
                "residual_question": "",
                "reasoning": "",
            }],
        }),
    )
    gap = InformationGap(
        gap_id="g1",
        category="risk_priority",
        description="risk",
        priority="critical",
    )
    ctx = _ctx([gap])
    out = await reconciler.reconcile(ctx)
    assert not out.gaps[0].filled


@pytest.mark.asyncio
async def test_medium_threshold_filled_at_point_six(
    reconciler: GapReconciler,
    llm: AsyncMock,
) -> None:
    llm.complete = AsyncMock(
        return_value=json.dumps({
            "gap_evaluations": [{
                "gap_id": "g1",
                "resolution_confidence": 0.65,
                "evidence_phrases": ["ok"],
                "residual_question": "",
                "reasoning": "",
            }],
        }),
    )
    gap = InformationGap(
        gap_id="g1",
        category="technical_context",
        description="tech",
        priority="medium",
    )
    ctx = _ctx([gap], turn=5)
    out = await reconciler.reconcile(ctx)
    assert out.gaps[0].filled
    assert out.gaps[0].filled_in_turn == 5

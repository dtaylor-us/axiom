"""
Unit tests for the weakness → FMEA dependency ordering.

These tests lock in the reliability constraint that weakness analysis must
complete before FMEA begins so that the FMEA prompt always receives populated
weakness context.
"""

from __future__ import annotations

import pytest

from app.models import ArchitectureContext
from app.pipeline import graph as pipeline_graph
from app.pipeline import nodes as pipeline_nodes


class _FakeTool:
    """Test double implementing the tool registry execute() contract."""

    def __init__(self, name: str, fn):
        self._name = name
        self._fn = fn

    async def execute(self, ctx: ArchitectureContext) -> ArchitectureContext:
        return await self._fn(ctx)


@pytest.mark.asyncio
async def test_fmea_analysis_receives_populated_weaknesses(monkeypatch):
    """fmea_analysis must receive populated weaknesses from weakness_analysis."""
    ctx = ArchitectureContext(conversation_id="c1", raw_requirements="r1")

    calls: list[str] = []

    async def weakness(ctx_in: ArchitectureContext) -> ArchitectureContext:
        calls.append("weakness")
        ctx_in.weaknesses = [{"id": "W-001"}]
        ctx_in.weakness_summary = "summary"
        return ctx_in

    async def fmea(ctx_in: ArchitectureContext) -> ArchitectureContext:
        calls.append("fmea")
        assert len(ctx_in.weaknesses) == 1
        ctx_in.fmea_risks = [{"id": "FMEA-001"}]
        ctx_in.fmea_critical_risks = ["FMEA-001"]
        return ctx_in

    monkeypatch.setattr(
        pipeline_nodes,
        "_registry",
        {
            "weakness_analyzer": _FakeTool("weakness_analyzer", weakness),
            "fmea_analyzer": _FakeTool("fmea_analyzer", fmea),
        },
    )

    result = await pipeline_nodes.weakness_analysis({"context": ctx})
    result = await pipeline_nodes.fmea_analysis({"context": result["context"]})

    assert calls == ["weakness", "fmea"]
    assert result["context"].fmea_critical_risks == ["FMEA-001"]


def test_stage_payload_includes_sequential_execution_order():
    """fmea_analysis stage payload must document sequential execution."""
    ctx = ArchitectureContext(conversation_id="c1", raw_requirements="r1")
    ctx.weaknesses = [{"id": "W-001"}]
    ctx.fmea_risks = [{"id": "FMEA-001"}]
    ctx.fmea_critical_risks = ["FMEA-001"]
    ctx.weakness_summary = "summary"

    payload = pipeline_graph._stage_payload("fmea_analysis", ctx)

    assert payload["execution_order"] == "sequential"


def test_stage_payload_marks_fmea_used_weakness_context_true_when_non_empty():
    """fmea_used_weakness_context must be true when weaknesses exist."""
    ctx = ArchitectureContext(conversation_id="c1", raw_requirements="r1")
    ctx.weaknesses = [{"id": "W-001"}]
    ctx.fmea_risks = []
    ctx.fmea_critical_risks = []

    payload = pipeline_graph._stage_payload("fmea_analysis", ctx)

    assert payload["fmea_used_weakness_context"] is True


def test_stage_payload_marks_fmea_used_weakness_context_false_when_empty():
    """fmea_used_weakness_context must be false when weaknesses are empty."""
    ctx = ArchitectureContext(conversation_id="c1", raw_requirements="r1")
    ctx.weaknesses = []
    ctx.fmea_risks = []
    ctx.fmea_critical_risks = []

    payload = pipeline_graph._stage_payload("fmea_analysis", ctx)

    assert payload["fmea_used_weakness_context"] is False


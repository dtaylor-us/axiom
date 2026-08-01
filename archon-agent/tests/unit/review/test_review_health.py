"""
Unit tests for review health tracking.

These tests ensure review sub-nodes never fail silently: each node must append a
SubReviewResult on both success and failure paths, and the agent must compute
confidence and completion flags from those outcomes.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest

from app.models import ArchitectureContext
from app.review.agent import ArchitectReviewAgent
from app.review.context import ReviewContext, SubReviewResult
from app.review.nodes import (
    challenge_assumptions_node,
    stress_test_trade_offs_node,
    audit_adl_node,
    score_governance_node,
)


def _review_context_with_llm() -> tuple[ReviewContext, AsyncMock]:
    rc = ReviewContext(conversation_id="c1", raw_requirements="r1")
    llm = AsyncMock()
    rc._llm_client = llm  # type: ignore[attr-defined]
    return rc, llm


@pytest.mark.asyncio
async def test_challenge_assumptions_node_appends_succeeded_subreviewresult_when_llm_succeeds():
    """challenge_assumptions_node records a succeeded SubReviewResult."""
    rc, llm = _review_context_with_llm()
    llm.complete.return_value = json.dumps({
        "assumption_challenges": [
            {
                "assumption": "A",
                "risk": "R",
                "recommendation": "Do X",
            }
        ]
    })

    result = await challenge_assumptions_node({"review_context": rc})

    out = result["review_context"]
    assert len(out.sub_review_results) == 1
    assert out.sub_review_results[0].node_name == "challenge_assumptions"
    assert out.sub_review_results[0].succeeded is True
    assert out.sub_review_results[0].items_produced == 1


@pytest.mark.asyncio
async def test_challenge_assumptions_node_records_failure_in_sub_review_results_when_llm_raises():
    """challenge_assumptions_node records failure and does not raise."""
    rc, llm = _review_context_with_llm()
    llm.complete.side_effect = RuntimeError("boom")

    result = await challenge_assumptions_node({"review_context": rc})

    out = result["review_context"]
    assert len(out.sub_review_results) == 1
    res = out.sub_review_results[0]
    assert res.node_name == "challenge_assumptions"
    assert res.succeeded is False
    assert res.failure_reason


@pytest.mark.asyncio
async def test_stress_test_trade_offs_node_records_failure_in_sub_review_results_when_llm_raises():
    """stress_test_trade_offs_node records failure and does not raise."""
    rc, llm = _review_context_with_llm()
    llm.complete.side_effect = RuntimeError("boom")

    result = await stress_test_trade_offs_node({"review_context": rc})

    out = result["review_context"]
    res = out.sub_review_results[0]
    assert res.node_name == "stress_test_trade_offs"
    assert res.succeeded is False
    assert res.failure_reason


@pytest.mark.asyncio
async def test_audit_adl_node_records_failure_in_sub_review_results_when_llm_raises():
    """audit_adl_node records failure and does not raise."""
    rc, llm = _review_context_with_llm()
    llm.complete.side_effect = RuntimeError("boom")

    result = await audit_adl_node({"review_context": rc})

    out = result["review_context"]
    res = out.sub_review_results[0]
    assert res.node_name == "audit_adl"
    assert res.succeeded is False
    assert res.failure_reason


@pytest.mark.asyncio
async def test_score_governance_node_sets_score_none_and_confidence_unavailable_when_it_fails():
    """score_governance_node failure clears governance_score and should_reiterate."""
    rc, llm = _review_context_with_llm()
    llm.complete.side_effect = RuntimeError("boom")

    result = await score_governance_node({"review_context": rc})

    out = result["review_context"]
    assert out.governance_score is None
    assert out.should_reiterate is False
    res = out.sub_review_results[0]
    assert res.node_name == "score_governance"
    assert res.succeeded is False


@pytest.mark.asyncio
async def test_architect_review_agent_sets_confidence_high_when_all_nodes_succeed(monkeypatch):
    """ArchitectReviewAgent sets high confidence when 4/4 sub-reviews succeed."""
    agent = ArchitectReviewAgent(AsyncMock())

    async def _ok(state):
        rc = state["review_context"]
        rc.sub_review_results = rc.sub_review_results + [
            # exactly four succeeded entries
            # (node names match the canonical set)
            rc.sub_review_results.__class__.__args__[0]  # type: ignore[attr-defined]
        ]
        return state

    # Replace compiled graph with a stub that returns 4 successes.
    async def _ainvoke(_):
        rc = ReviewContext(conversation_id="c1")
        rc.sub_review_results = [
            SubReviewResult(node_name="challenge_assumptions", succeeded=True),
            SubReviewResult(node_name="stress_test_trade_offs", succeeded=True),
            SubReviewResult(node_name="audit_adl", succeeded=True),
            SubReviewResult(node_name="score_governance", succeeded=True),
        ]
        rc.governance_score = 80
        return {"review_context": rc}

    agent._compiled.ainvoke = _ainvoke  # type: ignore[assignment]

    ctx = ArchitectureContext(conversation_id="c1", raw_requirements="r1")
    out = await agent.run(ctx)

    assert out.governance_score_confidence == "high"
    assert out.review_completed_fully is True
    assert out.failed_review_nodes == []


@pytest.mark.asyncio
async def test_architect_review_agent_sets_confidence_partial_when_two_nodes_succeed(caplog):
    """ArchitectReviewAgent sets partial confidence when 2/4 sub-reviews succeed."""
    agent = ArchitectReviewAgent(AsyncMock())

    async def _ainvoke(_):
        rc = ReviewContext(conversation_id="c1")
        rc.sub_review_results = [
            SubReviewResult(node_name="challenge_assumptions", succeeded=True),
            SubReviewResult(
                node_name="stress_test_trade_offs",
                succeeded=False,
                failure_reason="x",
            ),
            SubReviewResult(node_name="audit_adl", succeeded=True),
            SubReviewResult(
                node_name="score_governance",
                succeeded=False,
                failure_reason="y",
            ),
        ]
        rc.governance_score = 70
        return {"review_context": rc}

    agent._compiled.ainvoke = _ainvoke  # type: ignore[assignment]

    ctx = ArchitectureContext(conversation_id="c1", raw_requirements="r1")
    with caplog.at_level("WARNING"):
        out = await agent.run(ctx)

    assert out.governance_score_confidence == "partial"
    assert out.review_completed_fully is False
    assert "Architecture review completed with degradation" in caplog.text


@pytest.mark.asyncio
async def test_architect_review_agent_sets_confidence_unavailable_when_score_governance_fails(caplog):
    """Confidence is unavailable when score_governance fails."""
    agent = ArchitectReviewAgent(AsyncMock())

    async def _ainvoke(_):
        rc = ReviewContext(conversation_id="c1")
        rc.sub_review_results = [
            SubReviewResult(
                node_name="challenge_assumptions",
                succeeded=False,
                failure_reason="x",
            ),
            SubReviewResult(
                node_name="stress_test_trade_offs",
                succeeded=False,
                failure_reason="y",
            ),
            SubReviewResult(
                node_name="audit_adl",
                succeeded=False,
                failure_reason="z",
            ),
            SubReviewResult(
                node_name="score_governance",
                succeeded=False,
                failure_reason="boom",
            ),
        ]
        rc.governance_score = None
        return {"review_context": rc}

    agent._compiled.ainvoke = _ainvoke  # type: ignore[assignment]

    ctx = ArchitectureContext(conversation_id="c1", raw_requirements="r1")
    with caplog.at_level("WARNING"):
        out = await agent.run(ctx)

    assert out.governance_score_confidence == "unavailable"
    assert out.review_completed_fully is False
    assert "Architecture review completed with degradation" in caplog.text


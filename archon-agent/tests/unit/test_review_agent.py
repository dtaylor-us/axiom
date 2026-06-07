from __future__ import annotations

import json
import pytest
from unittest.mock import AsyncMock, patch

from app.models import ArchitectureContext, PipelineMode
from app.review.agent import ArchitectReviewAgent
from app.review.context import (
    AssumptionChallenge,
    GovernanceScoreBreakdown,
    ImprovementRecommendation,
    ReviewContext,
    TradeOffChallenge,
    AdlIssue,
)


@pytest.fixture
def mock_llm() -> AsyncMock:
    llm = AsyncMock()
    llm.complete = AsyncMock(return_value='{}')
    return llm


@pytest.fixture
def rich_context() -> ArchitectureContext:
    """Fully populated context ready for review."""
    return ArchitectureContext(
        conversation_id="test-conv-review",
        raw_requirements="Build a payment platform",
        mode=PipelineMode.AUTO,
        iteration=0,
        parsed_entities={"domain": "fintech"},
        characteristics=[{"name": "scalability"}, {"name": "latency"}],
        architecture_design={
            "style": "event-driven",
            "style_selection": {
                "selected_style": "event-driven",
                "style_scores": [
                    {"style": "event-driven", "score": 85, "driving_characteristics": ["scalability"]},
                ],
                "runner_up": "microservices",
            },
            "components": [
                {"name": "PaymentGateway", "type": "service"},
            ],
        },
        architecture_style_scores=[
            {"style": "event-driven", "score": 85},
        ],
        scenarios=[{"tier": "large", "description": "50k TPS peak"}],
        trade_offs=[
            {"decision_id": "TD-001", "decision": "Use async messaging"},
        ],
        adl_blocks=[],
        weaknesses=[
            {"id": "W-001", "category": "fragility", "title": "Gateway timeout"},
        ],
        fmea_risks=[
            {"id": "FMEA-001", "failure_mode": "Timeout", "rpn": 200},
        ],
    )


def _make_llm_responses() -> list[str]:
    """Return 4 JSON response strings for the 4 review nodes."""
    return [
        # 1. assumption_challenger
        json.dumps({
            "assumption_challenges": [
                {
                    "assumption": "10k TPS is peak not sustained",
                    "risk": "Under-provisioning",
                    "recommendation": "Size for sustained load",
                },
            ],
        }),
        # 2. trade_off_stress
        json.dumps({
            "trade_off_challenges": [
                {
                    "decision_id": "TD-001",
                    "concern": "Async adds latency to critical path",
                    "suggested_revision": "Sync for payments",
                    "severity": "high",
                },
            ],
        }),
        # 3. adl_audit
        json.dumps({
            "adl_issues": [
                {
                    "adl_id": "ADL-001",
                    "issue_type": "missing_coverage",
                    "description": "No availability rule",
                    "recommendation": "Add availability ADL",
                },
            ],
        }),
        # 4. governance_scorer
        json.dumps({
            "governance_score_breakdown": {
                "requirement_coverage": 20,
                "architectural_soundness": 18,
                "risk_mitigation": 12,
                "governance_completeness": 15,
                "total": 65,
                "justification": "Needs improvement in risk mitigation",
            },
            "improvement_recommendations": [
                {
                    "area": "risk_mitigation",
                    "recommendation": "Add circuit breakers",
                    "priority": "high",
                    "requires_reiteration": True,
                },
            ],
            "should_reiterate": True,
        }),
    ]


class TestArchitectReviewAgent:
    """Tests for ArchitectReviewAgent."""

    @pytest.fixture
    def agent(self, mock_llm: AsyncMock) -> ArchitectReviewAgent:
        return ArchitectReviewAgent(mock_llm)

    def test_build_review_context_creates_deep_copy(
        self, agent: ArchitectReviewAgent, rich_context: ArchitectureContext,
    ):
        """_build_review_context creates an independent ReviewContext."""
        rc = agent._build_review_context(rich_context)

        assert isinstance(rc, ReviewContext)
        assert rc.raw_requirements == rich_context.raw_requirements
        # Ensure it's a copy, not a reference
        assert rc.characteristics is not rich_context.characteristics
        assert rc.trade_offs is not rich_context.trade_offs

    def test_build_review_context_injects_llm(
        self, agent: ArchitectReviewAgent, rich_context: ArchitectureContext,
        mock_llm: AsyncMock,
    ):
        """_build_review_context injects the LLM client."""
        rc = agent._build_review_context(rich_context)

        assert rc._llm_client is mock_llm  # type: ignore[attr-defined]

    async def test_run_writes_review_findings_to_context(
        self, agent: ArchitectReviewAgent, rich_context: ArchitectureContext,
        mock_llm: AsyncMock,
    ):
        """run() populates review_findings on the context."""
        responses = _make_llm_responses()
        mock_llm.complete.side_effect = responses

        result = await agent.run(rich_context)

        assert "assumption_challenges" in result.review_findings
        assert len(result.review_findings["assumption_challenges"]) == 1
        assert "trade_off_challenges" in result.review_findings
        assert "adl_issues" in result.review_findings

    async def test_run_writes_governance_score(
        self, agent: ArchitectReviewAgent, rich_context: ArchitectureContext,
        mock_llm: AsyncMock,
    ):
        """run() sets governance_score from the scorer node."""
        responses = _make_llm_responses()
        mock_llm.complete.side_effect = responses

        result = await agent.run(rich_context)

        assert result.governance_score == 65

    async def test_run_writes_governance_breakdown(
        self, agent: ArchitectReviewAgent, rich_context: ArchitectureContext,
        mock_llm: AsyncMock,
    ):
        """run() sets governance_score_breakdown as a dict."""
        responses = _make_llm_responses()
        mock_llm.complete.side_effect = responses

        result = await agent.run(rich_context)

        assert result.governance_score_breakdown["requirement_coverage"] == 20
        assert result.governance_score_breakdown["risk_mitigation"] == 12

    async def test_run_sets_should_reiterate_on_first_iteration(
        self, agent: ArchitectReviewAgent, rich_context: ArchitectureContext,
        mock_llm: AsyncMock,
    ):
        """run() sets should_reiterate=True when score is low and iteration=0."""
        rich_context.iteration = 0
        responses = _make_llm_responses()
        mock_llm.complete.side_effect = responses

        result = await agent.run(rich_context)

        assert result.should_reiterate is True

    async def test_run_blocks_reiteration_on_final_iteration(
        self, agent: ArchitectReviewAgent, rich_context: ArchitectureContext,
        mock_llm: AsyncMock,
    ):
        """run() sets should_reiterate=False when iteration >= 1 (final)."""
        rich_context.iteration = 1  # is_final_iteration = True
        responses = _make_llm_responses()
        mock_llm.complete.side_effect = responses

        result = await agent.run(rich_context)

        assert result.should_reiterate is False

    async def test_run_builds_review_constraints(
        self, agent: ArchitectReviewAgent, rich_context: ArchitectureContext,
        mock_llm: AsyncMock,
    ):
        """run() builds review_constraints from high-priority recommendations."""
        rich_context.iteration = 0
        responses = _make_llm_responses()
        mock_llm.complete.side_effect = responses

        result = await agent.run(rich_context)

        assert len(result.review_constraints) > 0
        # Should include the recommendation text
        assert any("circuit breakers" in c.lower() for c in result.review_constraints)

    async def test_run_includes_high_severity_tradeoff_in_constraints(
        self, agent: ArchitectReviewAgent, rich_context: ArchitectureContext,
        mock_llm: AsyncMock,
    ):
        """run() adds high-severity trade-off challenges to review_constraints."""
        rich_context.iteration = 0
        responses = _make_llm_responses()
        mock_llm.complete.side_effect = responses

        result = await agent.run(rich_context)

        # The trade-off challenge has severity "high" → should appear as constraint
        assert any("TD-001" in c for c in result.review_constraints)

    async def test_run_calls_llm_four_times(
        self, agent: ArchitectReviewAgent, rich_context: ArchitectureContext,
        mock_llm: AsyncMock,
    ):
        """run() calls LLM once per review node (4 total)."""
        responses = _make_llm_responses()
        mock_llm.complete.side_effect = responses

        await agent.run(rich_context)

        assert mock_llm.complete.await_count == 4

    async def test_run_writes_improvement_recommendations(
        self, agent: ArchitectReviewAgent, rich_context: ArchitectureContext,
        mock_llm: AsyncMock,
    ):
        """run() populates improvement_recommendations on context."""
        responses = _make_llm_responses()
        mock_llm.complete.side_effect = responses

        result = await agent.run(rich_context)

        assert len(result.improvement_recommendations) == 1
        assert result.improvement_recommendations[0]["area"] == "risk_mitigation"

    async def test_run_does_not_mutate_original_design(
        self, agent: ArchitectReviewAgent, rich_context: ArchitectureContext,
        mock_llm: AsyncMock,
    ):
        """run() does not change architecture_design or other forward-pass fields."""
        original_design = rich_context.architecture_design.copy()
        original_weaknesses = rich_context.weaknesses.copy()
        responses = _make_llm_responses()
        mock_llm.complete.side_effect = responses

        result = await agent.run(rich_context)

        assert result.architecture_design == original_design
        assert result.weaknesses == original_weaknesses

from __future__ import annotations

import json
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.review.context import (
    AssumptionChallenge,
    GovernanceScoreBreakdown,
    ImprovementRecommendation,
    ReviewContext,
    TradeOffChallenge,
    AdlIssue,
)
from app.review.nodes import (
    ReviewState,
    assumption_challenger,
    trade_off_stress,
    adl_audit,
    governance_scorer,
)


@pytest.fixture
def mock_llm() -> AsyncMock:
    llm = AsyncMock()
    llm.complete = AsyncMock(return_value='{}')
    return llm


@pytest.fixture
def review_context(mock_llm: AsyncMock) -> ReviewContext:
    """ReviewContext with snapshot data and LLM client injected."""
    rc = ReviewContext(
        raw_requirements="Build a payment platform with 10k TPS",
        parsed_entities={"domain": "fintech", "system_type": "payment"},
        characteristics=[{"name": "scalability"}, {"name": "latency"}],
        architecture_design={
            "style": "event-driven",
            "components": [
                {"name": "PaymentGateway", "type": "service"},
                {"name": "FraudEngine", "type": "service"},
            ],
        },
        architecture_style_scores=[
            {"style": "event-driven", "score": 85},
        ],
        scenarios=[{"tier": "large", "description": "50k TPS peak"}],
        trade_offs=[{"decision_id": "TD-001", "decision": "Use async messaging"}],
        adl_blocks=[
            {
                "adl_id": "ADL-001",
                "adl_source": "ASSERT scalability ...",
                "characteristic_enforced": "scalability",
            }
        ],
        weaknesses=[{"id": "W-001", "category": "fragility", "title": "Timeout"}],
        fmea_risks=[
            {"id": "FMEA-001", "failure_mode": "Gateway timeout", "rpn": 200},
        ],
    )
    rc._llm_client = mock_llm  # type: ignore[attr-defined]
    return rc


@pytest.fixture
def state(review_context: ReviewContext) -> ReviewState:
    return {"review_context": review_context}


# ── assumption_challenger ──────────────────────────────────────

class TestAssumptionChallenger:

    async def test_parses_valid_challenges(self, state, mock_llm):
        mock_llm.complete.return_value = json.dumps({
            "assumption_challenges": [
                {
                    "assumption": "10k TPS is peak, not sustained",
                    "risk": "Under-provisioning at sustained load",
                    "recommendation": "Size for sustained 10k TPS",
                },
                {
                    "assumption": "Fraud detection is non-blocking",
                    "risk": "Synchronous call tree",
                    "recommendation": "Use async fraud check",
                },
            ]
        })

        result = await assumption_challenger(state)
        rc = result["review_context"]

        assert len(rc.assumption_challenges) == 2
        assert isinstance(rc.assumption_challenges[0], AssumptionChallenge)
        assert "10k TPS" in rc.assumption_challenges[0].assumption

    async def test_filters_incomplete_challenges(self, state, mock_llm):
        mock_llm.complete.return_value = json.dumps({
            "assumption_challenges": [
                {
                    "assumption": "Valid",
                    "risk": "Valid risk",
                    "recommendation": "Valid rec",
                },
                {
                    "assumption": "Missing risk field",
                    # no "risk" key
                    "recommendation": "something",
                },
            ]
        })

        result = await assumption_challenger(state)
        rc = result["review_context"]

        assert len(rc.assumption_challenges) == 1

    async def test_handles_invalid_json_gracefully(self, state, mock_llm):
        mock_llm.complete.return_value = "{{broken"

        result = await assumption_challenger(state)
        rc = result["review_context"]

        assert len(rc.assumption_challenges) == 0


# ── trade_off_stress ───────────────────────────────────────────

class TestTradeOffStress:

    async def test_parses_valid_challenges(self, state, mock_llm):
        mock_llm.complete.return_value = json.dumps({
            "trade_off_challenges": [
                {
                    "decision_id": "TD-001",
                    "concern": "Async messaging adds latency",
                    "suggested_revision": "Use sync for critical path",
                    "severity": "high",
                },
            ]
        })

        result = await trade_off_stress(state)
        rc = result["review_context"]

        assert len(rc.trade_off_challenges) == 1
        assert isinstance(rc.trade_off_challenges[0], TradeOffChallenge)
        assert rc.trade_off_challenges[0].severity == "high"

    async def test_filters_incomplete_entries(self, state, mock_llm):
        mock_llm.complete.return_value = json.dumps({
            "trade_off_challenges": [
                {
                    "decision_id": "TD-001",
                    "concern": "Valid",
                    "suggested_revision": "Fix",
                },
                {
                    "decision_id": "TD-002",
                    # missing concern
                    "suggested_revision": "Fix",
                },
            ]
        })

        result = await trade_off_stress(state)
        rc = result["review_context"]

        assert len(rc.trade_off_challenges) == 1

    async def test_handles_invalid_json_gracefully(self, state, mock_llm):
        mock_llm.complete.return_value = "not json"

        result = await trade_off_stress(state)
        rc = result["review_context"]

        assert len(rc.trade_off_challenges) == 0


# ── adl_audit ──────────────────────────────────────────────────

class TestAdlAudit:

    async def test_parses_valid_issues(self, state, mock_llm):
        mock_llm.complete.return_value = json.dumps({
            "adl_issues": [
                {
                    "adl_id": "ADL-001",
                    "issue_type": "weak_assertion",
                    "description": "No measurable threshold",
                    "recommendation": "Add p99 latency <= 100ms",
                },
                {
                    "adl_id": "ADL-002",
                    "issue_type": "missing_coverage",
                    "description": "No availability rule",
                    "recommendation": "Add availability ADL block",
                },
            ]
        })

        result = await adl_audit(state)
        rc = result["review_context"]

        assert len(rc.adl_issues) == 2
        assert isinstance(rc.adl_issues[0], AdlIssue)

    async def test_filters_incomplete_issues(self, state, mock_llm):
        mock_llm.complete.return_value = json.dumps({
            "adl_issues": [
                {
                    "adl_id": "ADL-001",
                    "issue_type": "weak_assertion",
                    "description": "Valid",
                    "recommendation": "Fix it",
                },
                {
                    "adl_id": "ADL-002",
                    # missing description
                    "issue_type": "missing_coverage",
                    "recommendation": "Fix",
                },
            ]
        })

        result = await adl_audit(state)
        rc = result["review_context"]

        assert len(rc.adl_issues) == 1


# ── governance_scorer ──────────────────────────────────────────

class TestGovernanceScorer:

    async def test_parses_score_breakdown(self, state, mock_llm):
        mock_llm.complete.return_value = json.dumps({
            "governance_score_breakdown": {
                "requirement_coverage": 20,
                "architectural_soundness": 18,
                "risk_mitigation": 15,
                "governance_completeness": 22,
                "total": 75,
                "justification": "Solid but needs work on risk mitigation",
            },
            "improvement_recommendations": [],
            "should_reiterate": False,
        })

        result = await governance_scorer(state)
        rc = result["review_context"]

        assert rc.governance_score == 75
        assert rc.governance_score_breakdown is not None
        assert rc.governance_score_breakdown.requirement_coverage == 20

    async def test_corrects_inconsistent_total(self, state, mock_llm):
        mock_llm.complete.return_value = json.dumps({
            "governance_score_breakdown": {
                "requirement_coverage": 20,
                "architectural_soundness": 18,
                "risk_mitigation": 15,
                "governance_completeness": 22,
                "total": 99,  # Should be 75
                "justification": "Wrong total",
            },
            "improvement_recommendations": [],
            "should_reiterate": False,
        })

        result = await governance_scorer(state)
        rc = result["review_context"]

        assert rc.governance_score == 75  # 20+18+15+22
        assert rc.governance_score_breakdown.total == 75

    async def test_parses_improvement_recommendations(self, state, mock_llm):
        mock_llm.complete.return_value = json.dumps({
            "governance_score_breakdown": {
                "requirement_coverage": 20,
                "architectural_soundness": 18,
                "risk_mitigation": 15,
                "governance_completeness": 22,
                "total": 75,
                "justification": "OK",
            },
            "improvement_recommendations": [
                {
                    "area": "risk_mitigation",
                    "recommendation": "Add circuit breakers",
                    "priority": "high",
                    "requires_reiteration": True,
                },
                {
                    "area": "governance_completeness",
                    "recommendation": "Add more ADL blocks",
                    "priority": "medium",
                    "requires_reiteration": False,
                },
            ],
            "should_reiterate": True,
        })

        result = await governance_scorer(state)
        rc = result["review_context"]

        assert len(rc.improvement_recommendations) == 2
        assert isinstance(rc.improvement_recommendations[0], ImprovementRecommendation)
        assert rc.improvement_recommendations[0].requires_reiteration is True

    async def test_sets_should_reiterate(self, state, mock_llm):
        mock_llm.complete.return_value = json.dumps({
            "governance_score_breakdown": {
                "requirement_coverage": 10,
                "architectural_soundness": 10,
                "risk_mitigation": 10,
                "governance_completeness": 10,
                "total": 40,
                "justification": "Low score",
            },
            "improvement_recommendations": [],
            "should_reiterate": True,
        })

        result = await governance_scorer(state)
        rc = result["review_context"]

        assert rc.should_reiterate is True

    async def test_handles_invalid_json_gracefully(self, state, mock_llm):
        mock_llm.complete.return_value = "not valid json"

        result = await governance_scorer(state)
        rc = result["review_context"]

        # Should not crash; scoring failure makes score unavailable.
        assert rc.governance_score is None

"""Review agent node functions.

Each node performs one review activity using an LLM call and
writes results into the ReviewContext. Nodes are designed to
run sequentially within the review sub-graph: assumptions and
trade-off stress run first (can be parallel), then ADL audit,
then governance scoring which aggregates all prior findings.
"""

from __future__ import annotations

import json
import logging
from typing import TypedDict

from app.llm.client import LLMClient, set_llm_context
from app.prompts.loader import load_prompt
from app.review.context import (
    AdlIssue,
    AssumptionChallenge,
    GovernanceScoreBreakdown,
    ImprovementRecommendation,
    ReviewContext,
    SubReviewResult,
    TradeOffChallenge,
)

logger = logging.getLogger(__name__)

_MAX_FAILURE_REASON_CHARS = 300
# Truncate exception text to keep payloads and logs bounded.


class ReviewState(TypedDict):
    review_context: ReviewContext


async def challenge_assumptions_node(state: ReviewState) -> dict:
    """Challenge hidden assumptions in the architecture design.

    Records success or failure into sub_review_results regardless of outcome.
    """
    rc = state["review_context"]
    node_name = "challenge_assumptions"

    try:
        llm: LLMClient = rc._llm_client  # type: ignore[attr-defined]
        set_llm_context(node_name, rc.conversation_id)

        prompt = load_prompt(
            "review_assumption_challenger",
            raw_requirements=rc.raw_requirements,
            parsed_entities=rc.parsed_entities,
            architecture_design=rc.architecture_design,
            characteristics=rc.characteristics,
            scenarios=rc.scenarios,
        )

        raw = await llm.complete(prompt, response_format="json")
        parsed = json.loads(raw)

        challenges = [
            AssumptionChallenge(**c)
            for c in parsed.get("assumption_challenges", [])
            if all(k in c for k in ("assumption", "risk", "recommendation"))
        ]

        rc.assumption_challenges = challenges
        rc.sub_review_results = rc.sub_review_results + [
            SubReviewResult(
                node_name=node_name,
                succeeded=True,
                items_produced=len(challenges),
            )
        ]
        logger.info("%s produced %d challenges", node_name, len(challenges))
        return {"review_context": rc}
    except Exception as e:
        logger.error(
            "Review sub-stage failed. node=%s error=%s conversation_id=%s",
            node_name,
            str(e),
            rc.conversation_id,
        )
        rc.sub_review_results = rc.sub_review_results + [
            SubReviewResult(
                node_name=node_name,
                succeeded=False,
                failure_reason=str(e)[:_MAX_FAILURE_REASON_CHARS],
                items_produced=0,
            )
        ]
        return {"review_context": rc}


async def stress_test_trade_offs_node(state: ReviewState) -> dict:
    """Stress-test trade-off decisions against risks and weaknesses.

    Records success or failure into sub_review_results regardless of outcome.
    """
    rc = state["review_context"]
    node_name = "stress_test_trade_offs"

    try:
        llm: LLMClient = rc._llm_client  # type: ignore[attr-defined]
        set_llm_context(node_name, rc.conversation_id)

        prompt = load_prompt(
            "review_tradeoff_stress",
            architecture_design=rc.architecture_design,
            trade_offs=rc.trade_offs,
            characteristics=rc.characteristics,
            weaknesses=rc.weaknesses,
            fmea_risks=rc.fmea_risks,
        )

        raw = await llm.complete(prompt, response_format="json")
        parsed = json.loads(raw)

        challenges = [
            TradeOffChallenge(**c)
            for c in parsed.get("trade_off_challenges", [])
            if all(k in c for k in ("decision_id", "concern", "suggested_revision"))
        ]

        rc.trade_off_challenges = challenges
        rc.sub_review_results = rc.sub_review_results + [
            SubReviewResult(
                node_name=node_name,
                succeeded=True,
                items_produced=len(challenges),
            )
        ]
        logger.info("%s produced %d challenges", node_name, len(challenges))
        return {"review_context": rc}
    except Exception as e:
        logger.error(
            "Review sub-stage failed. node=%s error=%s conversation_id=%s",
            node_name,
            str(e),
            rc.conversation_id,
        )
        rc.sub_review_results = rc.sub_review_results + [
            SubReviewResult(
                node_name=node_name,
                succeeded=False,
                failure_reason=str(e)[:_MAX_FAILURE_REASON_CHARS],
                items_produced=0,
            )
        ]
        return {"review_context": rc}


async def audit_adl_node(state: ReviewState) -> dict:
    """Audit ADL blocks for coverage gaps and consistency issues.

    Records success or failure into sub_review_results regardless of outcome.
    """
    rc = state["review_context"]
    node_name = "audit_adl"

    try:
        llm: LLMClient = rc._llm_client  # type: ignore[attr-defined]
        set_llm_context(node_name, rc.conversation_id)

        prompt = load_prompt(
            "review_adl_audit",
            adl_blocks=[b if isinstance(b, dict) else b for b in rc.adl_blocks],
            architecture_design=rc.architecture_design,
            characteristics=rc.characteristics,
            weaknesses=rc.weaknesses,
            fmea_risks=rc.fmea_risks,
        )

        raw = await llm.complete(prompt, response_format="json")
        parsed = json.loads(raw)

        issues = [
            AdlIssue(**i)
            for i in parsed.get("adl_issues", [])
            if all(k in i for k in ("adl_id", "issue_type", "description", "recommendation"))
        ]

        rc.adl_issues = issues
        rc.sub_review_results = rc.sub_review_results + [
            SubReviewResult(
                node_name=node_name,
                succeeded=True,
                items_produced=len(issues),
            )
        ]
        logger.info("%s found %d issues", node_name, len(issues))
        return {"review_context": rc}
    except Exception as e:
        logger.error(
            "Review sub-stage failed. node=%s error=%s conversation_id=%s",
            node_name,
            str(e),
            rc.conversation_id,
        )
        rc.sub_review_results = rc.sub_review_results + [
            SubReviewResult(
                node_name=node_name,
                succeeded=False,
                failure_reason=str(e)[:_MAX_FAILURE_REASON_CHARS],
                items_produced=0,
            )
        ]
        return {"review_context": rc}


async def score_governance_node(state: ReviewState) -> dict:
    """Compute the overall governance score and improvement recommendations.

    Records success or failure into sub_review_results regardless of outcome.
    On failure, governance_score is set to None and should_reiterate is False.
    """
    rc = state["review_context"]
    node_name = "score_governance"

    try:
        llm: LLMClient = rc._llm_client  # type: ignore[attr-defined]
        set_llm_context(node_name, rc.conversation_id)

        prompt = load_prompt(
            "review_governance_score",
            raw_requirements=rc.raw_requirements,
            parsed_entities=rc.parsed_entities,
            architecture_design=rc.architecture_design,
            characteristics=rc.characteristics,
            trade_offs=rc.trade_offs,
            adl_blocks=[b if isinstance(b, dict) else b for b in rc.adl_blocks],
            weaknesses=rc.weaknesses,
            fmea_risks=rc.fmea_risks,
            assumption_challenges=[c.model_dump() for c in rc.assumption_challenges],
            trade_off_challenges=[c.model_dump() for c in rc.trade_off_challenges],
            adl_issues=[i.model_dump() for i in rc.adl_issues],
        )

        raw = await llm.complete(prompt, response_format="json")
        parsed = json.loads(raw)

        # Parse score breakdown
        breakdown_data = parsed.get("governance_score_breakdown", {})
        breakdown = GovernanceScoreBreakdown(**breakdown_data)
        expected_total = (
            breakdown.requirement_coverage
            + breakdown.architectural_soundness
            + breakdown.risk_mitigation
            + breakdown.governance_completeness
        )
        if breakdown.total != expected_total:
            logger.warning(
                "%s: correcting total %d -> %d",
                node_name,
                breakdown.total,
                expected_total,
            )
            breakdown.total = expected_total
        rc.governance_score_breakdown = breakdown
        rc.governance_score = breakdown.total

        # Parse improvement recommendations
        recs = [
            ImprovementRecommendation(**r)
            for r in parsed.get("improvement_recommendations", [])
            if all(k in r for k in ("area", "recommendation"))
        ]
        rc.improvement_recommendations = recs

        # Determine re-iteration need
        rc.should_reiterate = parsed.get("should_reiterate", False)

        rc.sub_review_results = rc.sub_review_results + [
            SubReviewResult(
                node_name=node_name,
                succeeded=True,
                items_produced=len(recs),
            )
        ]
        logger.info(
            "%s: score=%s, reiterate=%s, %d recommendations",
            node_name,
            rc.governance_score,
            rc.should_reiterate,
            len(recs),
        )
        return {"review_context": rc}
    except Exception as e:
        logger.error(
            "Review sub-stage failed. node=%s error=%s conversation_id=%s",
            node_name,
            str(e),
            rc.conversation_id,
        )
        rc.governance_score = None
        rc.governance_score_breakdown = None
        rc.should_reiterate = False
        rc.sub_review_results = rc.sub_review_results + [
            SubReviewResult(
                node_name=node_name,
                succeeded=False,
                failure_reason=str(e)[:_MAX_FAILURE_REASON_CHARS],
                items_produced=0,
            )
        ]
        return {"review_context": rc}


# Backward-compatible aliases (internal) — keep node keys stable for any callers.
assumption_challenger = challenge_assumptions_node
trade_off_stress = stress_test_trade_offs_node
adl_audit = audit_adl_node
governance_scorer = score_governance_node

"""Architect Review Agent — a LangGraph sub-graph that stress-tests the architecture.

The review agent operates on a deep copy of the main context data (via ReviewContext)
and never holds a reference to the live ArchitectureContext. Its findings are written
back to the main context after the sub-graph completes.
"""

from __future__ import annotations

import logging

from langgraph.graph import StateGraph, END

from app.llm.client import LLMClient
from app.models import ArchitectureContext
from app.review.context import ReviewContext
from app.review.nodes import (
    ReviewState,
    challenge_assumptions_node,
    stress_test_trade_offs_node,
    audit_adl_node,
    score_governance_node,
)

logger = logging.getLogger(__name__)


class ArchitectReviewAgent:
    """Encapsulates the review sub-graph lifecycle.

    Build once at startup, invoke per-pipeline run with a deep copy of context.
    """

    def __init__(self, llm_client: LLMClient) -> None:
        self._llm_client = llm_client
        self._compiled = self._build_graph()
        logger.info("ArchitectReviewAgent graph compiled")

    @staticmethod
    def _build_graph():
        builder = StateGraph(ReviewState)

        builder.add_node("challenge_assumptions", challenge_assumptions_node)
        builder.add_node("stress_test_trade_offs", stress_test_trade_offs_node)
        builder.add_node("audit_adl", audit_adl_node)
        builder.add_node("score_governance", score_governance_node)

        builder.set_entry_point("challenge_assumptions")
        builder.add_edge("challenge_assumptions", "stress_test_trade_offs")
        builder.add_edge("stress_test_trade_offs", "audit_adl")
        builder.add_edge("audit_adl", "score_governance")
        builder.add_edge("score_governance", END)

        return builder.compile()

    def _build_review_context(
        self, context: ArchitectureContext
    ) -> ReviewContext:
        """Create a ReviewContext from a deep copy of main context data."""
        rc = ReviewContext(
            conversation_id=context.conversation_id,
            raw_requirements=context.raw_requirements,
            parsed_entities=context.parsed_entities.copy(),
            characteristics=[c.copy() for c in context.characteristics],
            architecture_design=context.architecture_design.copy(),
            architecture_style_scores=[
                s.copy() for s in context.architecture_style_scores
            ],
            scenarios=[s.copy() for s in context.scenarios],
            trade_offs=[t.copy() for t in context.trade_offs],
            adl_blocks=[
                b.model_dump() if hasattr(b, "model_dump") else b.copy()
                for b in context.adl_blocks
            ],
            weaknesses=[w.copy() for w in context.weaknesses],
            fmea_risks=[r.copy() for r in context.fmea_risks],
        )
        # Inject the LLM client for review nodes to use
        rc._llm_client = self._llm_client  # type: ignore[attr-defined]
        return rc

    async def run(self, context: ArchitectureContext) -> ArchitectureContext:
        """Execute the review sub-graph and write findings back to context.

        Args:
            context: The main pipeline context (NOT mutated during review
                     graph execution — only updated with results at the end).

        Returns:
            Updated ArchitectureContext with review findings populated.
        """
        review_ctx = self._build_review_context(context)

        initial_state: ReviewState = {"review_context": review_ctx}

        # Run the review sub-graph to completion
        result = await self._compiled.ainvoke(initial_state)
        final_rc: ReviewContext = result["review_context"]

        # Compute review health summary
        succeeded_count = len(final_rc.succeeded_sub_reviews)
        total_nodes = 4
        if succeeded_count == total_nodes:
            confidence = "high"
            completed_fully = True
        elif succeeded_count >= 2:
            confidence = "partial"
            completed_fully = False
        elif succeeded_count == 1 and "score_governance" in final_rc.succeeded_sub_reviews:
            confidence = "low"
            completed_fully = False
        else:
            confidence = "unavailable"
            completed_fully = False

        final_rc.review_completed_fully = completed_fully
        final_rc.governance_score_confidence = confidence

        if not completed_fully:
            logger.warning(
                "Architecture review completed with degradation. succeeded=%d/%d "
                "failed_nodes=%s confidence=%s conversation_id=%s",
                succeeded_count,
                total_nodes,
                final_rc.failed_sub_reviews,
                confidence,
                context.conversation_id,
            )

        # Write review findings back to the main context
        context.review_findings = {
            "assumption_challenges": [
                c.model_dump() for c in final_rc.assumption_challenges
            ],
            "trade_off_challenges": [
                c.model_dump() for c in final_rc.trade_off_challenges
            ],
            "adl_issues": [
                i.model_dump() for i in final_rc.adl_issues
            ],
            # Preserve existing style_selection_challenge if present
            **(
                {"style_selection_challenge": context.review_findings.get(
                    "style_selection_challenge"
                )}
                if context.review_findings.get("style_selection_challenge")
                else {}
            ),
        }

        context.governance_score = final_rc.governance_score
        if final_rc.governance_score_breakdown:
            context.governance_score_breakdown = (
                final_rc.governance_score_breakdown.model_dump()
            )
        context.improvement_recommendations = [
            r.model_dump() for r in final_rc.improvement_recommendations
        ]
        context.should_reiterate = (
            final_rc.should_reiterate and not context.is_final_iteration
        )
        context.governance_score_confidence = final_rc.governance_score_confidence
        context.review_completed_fully = final_rc.review_completed_fully
        context.failed_review_nodes = final_rc.failed_sub_reviews

        # Build review constraints for re-iteration
        if context.should_reiterate:
            constraints: list[str] = []
            for r in final_rc.improvement_recommendations:
                if r.requires_reiteration:
                    constraints.append(r.recommendation)
            # Add high-severity trade-off challenges
            for c in final_rc.trade_off_challenges:
                if c.severity == "high":
                    constraints.append(
                        f"Revise trade-off {c.decision_id}: {c.concern}"
                    )
            context.review_constraints = constraints

        logger.info(
            "ArchitectReviewAgent complete: score=%s, reiterate=%s",
            context.governance_score,
            context.should_reiterate,
        )
        return context

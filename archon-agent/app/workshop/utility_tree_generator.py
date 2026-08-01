"""
Utility tree generator for the Quality Attribute Workshop.

Implements the SEI QAW utility tree technique: groups scenarios by
quality attribute and refinement, scores each by business importance
and technical risk, and identifies architectural drivers.

Reference: Bass, Clements, Kazman "Software Architecture in Practice"
4th ed. ch. 2.
"""

import json
import logging

from app.llm.client import LLMClient
from app.prompts.loader import load_prompt
from app.workshop.context import UtilityTree, UtilityTreeNode, WorkshopContext

logger = logging.getLogger(__name__)


class UtilityTreeGenerator:
    """
    Generates or refreshes the SEI QAW utility tree for a workshop session.

    The utility tree organises all accumulated scenarios by quality attribute
    and refinement, scores them by business importance and technical risk,
    and identifies architectural drivers — scenarios scored (H,H) or (H,M)
    that most constrain the architecture.

    Generation is guarded by WorkshopContext.has_sufficient_for_utility_tree.
    When the threshold is not met, generate() returns the existing tree
    unchanged (or None if no tree exists yet).
    """

    def __init__(self, llm: LLMClient) -> None:
        """
        Args:
            llm: LLM client used to call the generate_utility_tree prompt.
        """
        self._llm = llm

    async def generate(self, context: WorkshopContext) -> UtilityTree | None:
        """
        Generate or refresh the utility tree from the current session state.

        Returns the existing tree unchanged when there are insufficient
        scenarios (fewer than 5 partial-or-better across fewer than 3
        attributes). Logs an info message in that case.

        Args:
            context: Current WorkshopContext after consolidation.

        Returns:
            A new UtilityTree when generation succeeds, the existing tree
            when the threshold is not met, or None when no tree exists yet
            and generation cannot proceed.
        """
        if not context.has_sufficient_for_utility_tree:
            logger.info(
                "Utility tree generation skipped — insufficient scenarios. "
                "session=%s partial_or_better=%d",
                context.session_id,
                sum(
                    1 for s in context.deduplicated_scenarios
                    if s.completeness in (
                        "complete",
                        "partial",
                        "needs_measure",
                        "needs_operational_metric",
                    )
                ),
            )
            return context.utility_tree

        scenarios = context.deduplicated_scenarios
        prompt = load_prompt(
            "workshop/generate_utility_tree",
            system_name=context.system_name,
            scenarios=[s.model_dump() for s in scenarios],
            attributes=[a.model_dump() for a in context.attributes],
            current_turn=context.current_turn,
        )

        try:
            raw = await self._llm.complete(
                prompt,
                response_format="json",
                stage_name="generate_utility_tree",
            )
            parsed = json.loads(raw)
        except Exception:
            logger.error(
                "Utility tree LLM call failed. session=%s turn=%d",
                context.session_id,
                context.current_turn,
                exc_info=True,
            )
            # Return the existing tree on failure so partial state is preserved.
            return context.utility_tree

        nodes = [
            UtilityTreeNode(**node_data)
            for node_data in parsed.get("nodes", [])
        ]

        tree = UtilityTree(
            generated_at_turn=parsed.get("generated_at_turn", context.current_turn),
            total_scenarios=parsed.get("total_scenarios", len(scenarios)),
            architectural_drivers=parsed.get("architectural_drivers", []),
            nodes=nodes,
            generation_rationale=parsed.get("generation_rationale", ""),
        )

        logger.info(
            "Utility tree generated. session=%s turn=%d nodes=%d drivers=%d",
            context.session_id,
            context.current_turn,
            len(nodes),
            len(tree.architectural_drivers),
        )
        return tree

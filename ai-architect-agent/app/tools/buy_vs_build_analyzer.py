"""
Buy-vs-build analysis tool for the AI Architect Assistant.

For each component in the proposed architecture, evaluates whether it should be
built as custom software, bought as a commercial SaaS product, or adopted as an
open-source solution.

The analysis is grounded in real market knowledge — actual named products and
projects, not hypothetical ones. It considers:
  - Whether the component is a core business differentiator
  - Total cost of ownership (build cost vs licensing cost)
  - Integration effort
  - Vendor lock-in risk
  - User-stated preferences and constraints
  - Team operational capacity

Pipeline position: stage 6b — after architecture_generation (stage 6) and before
diagram_generation (stage 7).

The analysis runs on the finalised architecture design so it can reference
actual named components. It cannot run before stage 6 because the component
list does not exist yet.
"""

from __future__ import annotations

import json
import logging

from app.models.context import ArchitectureContext, BuyVsBuildDecision
from app.prompts.loader import load_prompt
from app.tools.base import BaseTool, ToolExecutionException

logger = logging.getLogger(__name__)

MIN_RATIONALE_LENGTH = 60


class BuyVsBuildAnalyzerTool(BaseTool):
    """Evaluates architecture components for build vs buy vs adopt sourcing."""

    async def run(self, context: ArchitectureContext) -> ArchitectureContext:
        """
        Performs buy-vs-build analysis for each architecture component.

        Reads:
            context.architecture_design (must be populated)
            context.characteristics
            context.buy_vs_build_preferences
            context.scenarios

        Writes:
            context.buy_vs_build_analysis
            context.buy_vs_build_summary

        Raises:
            ToolExecutionException: when architecture_design/components are missing,
                when the LLM returns invalid JSON, or when parsing fails.
        """
        architecture_design = context.architecture_design or {}
        components = architecture_design.get("components", []) if architecture_design else []

        if not architecture_design:
            raise ToolExecutionException(
                "Cannot perform buy-vs-build analysis without an "
                "architecture design. Ensure stage 6 completed."
            )
        if not components:
            raise ToolExecutionException(
                "Cannot perform buy-vs-build analysis without an "
                "architecture components list. Ensure stage 6 completed."
            )

        relevant_components: list[dict] = []
        for c in components:
            c_type = (c.get("type") or "").strip().lower()
            if c_type == "external":
                continue
            if c_type in {"service", "database", "queue", "cache", "gateway"}:
                relevant_components.append(c)
        if not relevant_components:
            # Defensive fallback: some architecture styles emit component types
            # like "processing-unit" or "core-system". We still need sourcing
            # decisions for major components, so fall back to all non-external
            # components rather than returning an empty analysis.
            relevant_components = [
                c for c in components
                if str(c.get("type", "")).strip().lower() != "external"
            ]
            logger.warning(
                "BuyVsBuildAnalyzer found no components of expected types; "
                "falling back to all non-external components. conversation_id=%s",
                context.conversation_id,
            )

        prompt = load_prompt(
            "buy_vs_build_analyzer",
            components=relevant_components,
            characteristics=context.characteristics,
            buy_vs_build_preferences=context.buy_vs_build_preferences,
            scenarios=context.scenarios,
            architecture_style=architecture_design.get("style", ""),
            parsed_entities=context.parsed_entities,
        )

        raw = await self.llm_client.complete(prompt, response_format="json")

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            logger.error(
                "BuyVsBuildAnalyzer LLM returned invalid JSON: %s",
                raw[:500],
            )
            raise ToolExecutionException(
                f"LLM returned invalid JSON: {exc}"
            ) from exc

        raw_decisions = parsed.get("decisions", [])
        if not isinstance(raw_decisions, list):
            raise ToolExecutionException(
                "LLM returned invalid decisions format; expected a list."
            )

        decisions: list[BuyVsBuildDecision] = []
        rejected = 0
        for raw_decision in raw_decisions:
            if not isinstance(raw_decision, dict):
                rejected += 1
                logger.warning(
                    "Rejected buy-vs-build decision: not an object. conversation_id=%s",
                    context.conversation_id,
                )
                continue

            rejection_reason = self._validate_decision(raw_decision)
            if rejection_reason:
                rejected += 1
                logger.warning(
                    "Rejected buy-vs-build decision. reason=%s component=%s conversation_id=%s",
                    rejection_reason,
                    str(raw_decision.get("component_name", ""))[:80],
                    context.conversation_id,
                )
                continue

            decisions.append(BuyVsBuildDecision(**raw_decision))

        build_count = sum(1 for d in decisions if d.recommendation == "build")
        buy_count = sum(1 for d in decisions if d.recommendation == "buy")
        adopt_count = sum(1 for d in decisions if d.recommendation == "adopt")
        conflict_count = sum(1 for d in decisions if d.conflicts_with_user_preference)

        logger.info(
            "Buy-vs-build analysis: %d decisions. build=%d buy=%d adopt=%d conflicts=%d conversation_id=%s",
            len(decisions),
            build_count,
            buy_count,
            adopt_count,
            conflict_count,
            context.conversation_id,
        )

        if rejected:
            logger.warning(
                "Buy-vs-build analysis rejected %d decision(s). conversation_id=%s",
                rejected,
                context.conversation_id,
            )

        context.buy_vs_build_analysis = [d.model_dump() for d in decisions]
        context.buy_vs_build_summary = parsed.get("buy_vs_build_summary", "") or ""

        return context

    def _validate_decision(self, raw: dict) -> str | None:
        """
        Validate a single raw decision dict from the LLM.

        Returns:
            Rejection reason string if invalid, else None.
        """
        component_name = str(raw.get("component_name", "")).strip()
        if not component_name:
            return "component_name must be non-blank"

        recommendation = str(raw.get("recommendation", "")).strip().lower()
        if recommendation not in {"build", "buy", "adopt"}:
            return "recommendation must be one of build|buy|adopt"

        rationale = str(raw.get("rationale", "")).strip()
        if len(rationale) < MIN_RATIONALE_LENGTH:
            return f"rationale must be at least {MIN_RATIONALE_LENGTH} characters"

        alternatives = raw.get("alternatives_considered", [])
        if not isinstance(alternatives, list) or len(alternatives) < 2:
            return "alternatives_considered must contain at least 2 items"

        recommended_solution = str(raw.get("recommended_solution", "")).strip()
        if recommendation in {"buy", "adopt"} and not recommended_solution:
            return "recommended_solution must be non-blank for buy/adopt recommendations"

        vendor_lock_in_risk = str(raw.get("vendor_lock_in_risk", "")).strip().lower()
        if vendor_lock_in_risk not in {"low", "medium", "high"}:
            return "vendor_lock_in_risk must be low|medium|high"

        integration_effort = str(raw.get("integration_effort", "")).strip().lower()
        if integration_effort not in {"low", "medium", "high"}:
            return "integration_effort must be low|medium|high"

        conflicts = raw.get("conflicts_with_user_preference", False)
        if not isinstance(conflicts, bool):
            # Defensive: treat strings like "true" as invalid rather than guessing.
            return "conflicts_with_user_preference must be boolean"

        conflict_explanation = str(raw.get("conflict_explanation", "")).strip()
        if conflicts and not conflict_explanation:
            return "conflict_explanation must be non-blank when conflicts_with_user_preference is true"

        return None


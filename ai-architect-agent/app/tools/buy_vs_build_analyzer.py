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

Pipeline position: stage 6b — before architecture_generation (stage 6) so
buy/adopt decisions can constrain the generated component model.

The analysis prefers an existing component list, but can derive candidate
capabilities from parsed requirements when architecture_generation has not run.
"""

from __future__ import annotations

import json
import logging

from app.models.context import ArchitectureContext, BuyVsBuildDecision
from app.llm.schemas import SCHEMAS
from app.prompts.loader import load_prompt
from app.tools.base import BaseTool, ToolExecutionException

logger = logging.getLogger(__name__)

_STAGE = "buy_vs_build_analysis"
MIN_RATIONALE_LENGTH = 60

COMMODITY_CAPABILITY_HINTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Payment Provider", ("payment", "billing", "invoice", "charge", "checkout")),
    ("Email Delivery", ("email", "notification", "sendgrid", "postmark")),
    ("SMS Delivery", ("sms", "text message", "twilio")),
    ("Identity Provider", ("auth", "oauth", "saml", "sso", "identity")),
    ("Observability Platform", ("monitoring", "observability", "logging", "tracing")),
    ("Search Platform", ("search", "indexing", "catalog")),
    ("CDN Provider", ("cdn", "edge", "cache invalidation")),
    ("DRM Provider", ("drm", "license server")),
)


class BuyVsBuildAnalyzerTool(BaseTool):
    """Evaluates architecture components for build vs buy vs adopt sourcing."""

    async def run(self, context: ArchitectureContext) -> ArchitectureContext:
        """
        Performs buy-vs-build analysis for each architecture component.

        Reads:
            context.architecture_design when available, otherwise parsed
            requirements and raw requirements for candidate capabilities
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

        logger.info(
            "BUY_VS_BUILD: starting analysis. components_to_evaluate=%d "
            "conversation_id=%s",
            len(components),
            context.conversation_id,
        )

        relevant_components = self._components_to_evaluate(context, components)
        if not relevant_components:
            raise ToolExecutionException(
                "Cannot perform buy-vs-build analysis without an "
                "architecture components list or inferred candidate capabilities."
            )

        prompt = load_prompt(
            "buy_vs_build_analyzer",
            components=relevant_components,
            characteristics=context.characteristics,
            buy_vs_build_preferences=context.buy_vs_build_preferences,
            scenarios=context.scenarios,
            architecture_style=architecture_design.get("style", "pre-architecture"),
            parsed_entities=context.parsed_entities,
        )

        raw = await self.llm_client.complete(
            prompt,
            response_format="json",
            output_schema=SCHEMAS.get(_STAGE),
            schema_name=_STAGE,
            stage_name=_STAGE,
        )

        repair_attempted = False
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            logger.warning(
                "BuyVsBuildAnalyzer JSON parse failed, attempting repair. error=%s", exc
            )
            repair_attempted = True
            raw = await self.attempt_repair(
                original_prompt=prompt,
                failed_response=raw,
                error_description=f"Invalid JSON: {exc}",
                output_schema=SCHEMAS.get(_STAGE),
                schema_name=_STAGE,
                stage_name=_STAGE,
            )
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError as e2:
                raise ToolExecutionException(
                    f"Stage output could not be parsed after repair attempt. error={e2}"
                ) from e2

        raw_decisions = parsed.get("decisions", [])
        logger.info(
            "BUY_VS_BUILD: raw analysis returned decisions=%d conversation_id=%s",
            len(raw_decisions) if isinstance(raw_decisions, list) else 0,
            context.conversation_id,
        )
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
        logger.info(
            "BUY_VS_BUILD: analysis complete. decisions=%d buy_count=%d "
            "adopt_count=%d build_count=%d conversation_id=%s",
            len(decisions),
            buy_count,
            adopt_count,
            build_count,
            context.conversation_id,
        )

        if not decisions:
            logger.warning(
                "BUY_VS_BUILD: returned zero decisions. The prompt may not "
                "be finding buy candidates, or the components list is empty. "
                "architecture_design has %d components.",
                len(components),
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

    def _components_to_evaluate(
        self,
        context: ArchitectureContext,
        components: list[dict],
    ) -> list[dict]:
        """Return architecture components or inferred sourcing candidates."""
        if components:
            relevant_components: list[dict] = []
            for component in components:
                component_type = (component.get("type") or "").strip().lower()
                if component_type == "external":
                    continue
                if component_type in {"service", "database", "queue", "cache", "gateway"}:
                    relevant_components.append(component)
            if relevant_components:
                return relevant_components

            logger.warning(
                "BuyVsBuildAnalyzer found no components of expected types; "
                "falling back to all non-external components. conversation_id=%s",
                context.conversation_id,
            )
            return [
                component for component in components
                if str(component.get("type", "")).strip().lower() != "external"
            ]

        candidates = self._candidate_components_from_requirements(context)
        logger.info(
            "BUY_VS_BUILD: derived %d candidate components before architecture "
            "generation. conversation_id=%s",
            len(candidates),
            context.conversation_id,
        )
        return candidates

    def _candidate_components_from_requirements(
        self,
        context: ArchitectureContext,
    ) -> list[dict]:
        """Infer commodity capabilities from parsed and raw requirements."""
        parsed_components = context.parsed_entities.get("components", [])
        if isinstance(parsed_components, list) and parsed_components:
            return [
                {
                    "name": str(component.get("name", component)),
                    "type": str(component.get("type", "service")),
                    "responsibility": str(component.get("responsibility", "")),
                }
                if isinstance(component, dict)
                else {"name": str(component), "type": "service", "responsibility": ""}
                for component in parsed_components
            ]

        requirements_text = (
            f"{context.raw_requirements} {json.dumps(context.parsed_entities)}"
        ).lower()
        candidates: list[dict] = []
        for capability_name, keywords in COMMODITY_CAPABILITY_HINTS:
            if any(keyword in requirements_text for keyword in keywords):
                candidates.append({
                    "name": capability_name,
                    "type": "service",
                    "responsibility": (
                        f"Provide {capability_name.lower()} capability identified "
                        "from requirements."
                    ),
                })
        return candidates

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

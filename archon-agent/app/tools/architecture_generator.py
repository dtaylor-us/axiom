"""Architecture style selection and system design generator.

Implements Mark Richards' characteristic-driven style selection
methodology from *Fundamentals of Software Architecture* (O'Reilly, 2020).
Scores all eight Richards styles against inferred characteristics,
applies veto rules, then generates a component-level design using
the winning style.
"""

from __future__ import annotations

import json
import logging
import os

from app.llm.budget import budget_json_list, get_input_budget
from app.llm.client import LLMClient
from app.llm.schemas import SCHEMAS
from app.memory.store import MemoryStore
from app.models import ArchitectureContext
from app.prompts.loader import load_prompt
from app.tools.base import BaseTool, ToolExecutionException

logger = logging.getLogger(__name__)

_STAGE = "architecture_generation"

# Number of architecture styles in the Richards catalog.
# Layered, Modular Monolith, Microkernel, Pipeline,
# Service-based, Event-driven, Microservices, Space-based.
EXPECTED_STYLE_COUNT = 8

# Minimum length for a meaningful style selection rationale.
# Anything shorter likely indicates the LLM defaulted without reasoning.
MIN_RATIONALE_LENGTH = 100

# Characteristics that signal a distributed style is likely needed.
# If the selected style is "Layered" and any of these appear with a
# non-trivial measurable_target, we emit a warning (not a rejection).
DISTRIBUTED_SIGNAL_CHARACTERISTICS = frozenset({
    "scalability",
    "elasticity",
    "agility",
    "deployability",
    "fault_tolerance",
})

INVALID_INTERACTION_FIELD_VALUES = frozenset({
    "",
    "undefined",
    "null",
    "unknown",
})

DEFAULT_COMPONENT_OWNERSHIP = {
    "service": "enterprise-built",
    "database": "adopted-platform",
    "queue": "adopted-platform",
    "cache": "adopted-platform",
    "gateway": "enterprise-built",
    "external": "bought-saas",
    "processing-unit": "enterprise-built",
    "plugin": "enterprise-built",
    "core-system": "enterprise-built",
}


class ArchitectureGeneratorTool(BaseTool):
    """Generates a full architecture design driven by inferred characteristics.

    Performs explicit style selection across all eight Richards architecture
    styles before producing the component-level design. Validates that
    the LLM performed proper style scoring and applies bias-detection
    warnings for monolith defaults.
    """

    def __init__(
        self, llm_client: LLMClient, memory_store: MemoryStore
    ) -> None:
        super().__init__(llm_client)
        self._memory = memory_store

    async def run(self, context: ArchitectureContext) -> ArchitectureContext:
        """Execute style selection and architecture generation.

        Args:
            context: Pipeline context with characteristics already populated.

        Returns:
            Context with architecture_design and architecture_style_scores populated.

        Raises:
            ToolExecutionException: If characteristics are empty, JSON is
                invalid, style_selection is missing, or selected_style is blank.
        """
        if not context.characteristics:
            raise ToolExecutionException(
                "characteristics is empty; run CharacteristicReasoningEngine first"
            )

        canonical = context.canonical_decisions
        logger.info(
            "ARCHITECTURE_GEN_AUDIT: canonical_decisions=%d "
            "buy_vs_build_analysis_raw=%d "
            "conversation_id=%s",
            len(canonical),
            len(context.buy_vs_build_analysis or []),
            context.conversation_id,
        )
        for decision in canonical:
            logger.info(
                "ARCHITECTURE_GEN_AUDIT: constraint component=%s "
                "decision=%s solution=%s",
                decision.get("component"),
                decision.get("decision"),
                decision.get("recommended_solution"),
            )
        if not canonical and context.buy_vs_build_analysis:
            logger.warning(
                "ARCHITECTURE_GEN_AUDIT: buy_vs_build_analysis "
                "has %d entries but canonical_decisions is empty. "
                "Check that recommendations include 'buy' or 'adopt'.",
                len(context.buy_vs_build_analysis),
            )
            for decision in context.buy_vs_build_analysis:
                logger.warning(
                    "ARCHITECTURE_GEN_AUDIT: bvb entry "
                    "component=%s recommendation=%s",
                    decision.get("component_name", decision.get("component")),
                    decision.get("recommendation"),
                )

        # Retrieve similar past designs from Qdrant (best-effort)
        similar = await self._memory.retrieve_similar(
            context.raw_requirements, limit=3
        )
        context.similar_past_designs = similar

        # Pick a representative scenario as the target
        target_scenario = (
            context.scenarios[0] if context.scenarios else {}
        )
        provider = os.getenv("LLM_PROVIDER", "ollama")
        num_ctx = int(os.getenv("OLLAMA_NUM_CTX_PRIMARY", "16384"))
        input_budget = get_input_budget(_STAGE, provider, num_ctx)
        budgeted_entities = _budget_parsed_entities(
            context.parsed_entities,
            max_tokens=input_budget // 3,
        )
        budgeted_characteristics = budget_json_list(
            context.characteristics,
            max_tokens=input_budget // 3,
            stage_name=_STAGE,
            item_label="characteristics",
        )

        prompt = load_prompt(
            "architecture_generator",
            parsed_entities=budgeted_entities,
            characteristics=budgeted_characteristics,
            characteristic_conflicts=context.characteristic_conflicts,
            target_scenario=target_scenario,
            scenarios=context.scenarios,
            similar_past_designs=similar,
            architecture_override=context.architecture_override,
            buy_vs_build_preferences=context.buy_vs_build_preferences,
            canonical_decisions=context.canonical_decisions,
            project_memory_context=json.dumps(
                context.project_memory_context or {},
                indent=2,
                sort_keys=True,
            ),
        )
        if context.iterative_mode and context.previous_architecture:
            previous = context.previous_architecture
            previous_adl = previous.get("adl_document", "")
            prompt = f"""
## ITERATIVE UPDATE — PRESERVE AND EXTEND

This is a delta update to an existing architecture.
Previous architecture style: {previous.get("style", "")}

Previous components (preserve unless explicitly changed):
{_format_component_list(previous.get("components", []))}

Previous ADL governance rules (preserve unless superseded):
{previous_adl[:1500] if previous_adl else "(none)"}

Apply the delta from requirement parsing. Preserve every previous decision not
explicitly changed. Do not regenerate from scratch.

{prompt}"""

        raw = await self.llm_client.complete(
            prompt,
            response_format="json",
            output_schema=SCHEMAS.get(_STAGE),
            schema_name=_STAGE,
            stage_name=_STAGE,
        )

        repair_attempted = False
        try:
            result = json.loads(raw)
        except json.JSONDecodeError as exc:
            logger.warning(
                "ArchitectureGenerator JSON parse failed, attempting repair. error=%s",
                exc,
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
                result = json.loads(raw)
            except json.JSONDecodeError as e2:
                raise ToolExecutionException(
                    f"Stage output could not be parsed after repair attempt. error={e2}"
                ) from e2

        # --- Validate style selection ---
        self._validate_style_selection(result, context)

        # Keep one canonical architecture identity.  The model historically
        # returned both style_selection.selected_style and a top-level style,
        # which allowed the chat report and persisted Architecture View to
        # disagree.  Downstream consumers may still read the legacy top-level
        # fields, so overwrite them from the authoritative selection and parsed
        # requirements before the context is formatted or persisted.
        selected_style = result["style_selection"]["selected_style"].strip()
        result["style"] = selected_style
        for field in ("domain", "system_type"):
            parsed_value = context.parsed_entities.get(field)
            if parsed_value:
                result[field] = parsed_value

        # --- Validate components ---
        components = self._apply_canonical_component_constraints(
            result.get("components", []),
            canonical,
        )
        result["components"] = components
        if not components:
            raise ToolExecutionException(
                "Architecture generator returned an empty components list."
            )
        result["interactions"] = self._validate_interactions(
            result.get("interactions", [])
        )

        # Write style scores into the dedicated context field
        style_selection = result.get("style_selection", {})
        context.architecture_style_scores = style_selection.get(
            "style_scores", []
        )
        context.architecture_design = result

        # Write override metadata to context for stage payload
        context.architecture_design["override_applied"] = style_selection.get(
            "override_applied", False
        )
        context.architecture_design["override_warning"] = style_selection.get(
            "override_warning", ""
        )

        # Log warning if an override produced a poor-fit selection
        override_warning = style_selection.get("override_warning", "")
        if override_warning:
            logger.warning(
                "Architecture override produced a poor-fit selection. "
                "warning=%s selected_style=%s conversation_id=%s",
                override_warning[:200],
                style_selection.get("selected_style"),
                context.conversation_id,
            )

        logger.info(
            "ArchitectureGenerator produced design with %d components, "
            "style=%s, runner_up=%s repair_attempted=%s",
            len(components),
            style_selection.get("selected_style", "unknown"),
            style_selection.get("runner_up", "unknown"),
            repair_attempted,
        )
        return context

    def _apply_canonical_component_constraints(
        self,
        components: list[dict],
        canonical_decisions: list[dict],
    ) -> list[dict]:
        """Enforce sourcing decisions and fill component ownership."""
        constrained: list[dict] = []
        for component in components:
            normalized = dict(component)
            matching_decision = self._matching_canonical_decision(
                normalized,
                canonical_decisions,
            )
            component_type = normalized.get("type", "").lower()
            if matching_decision and component_type != "external":
                logger.warning(
                    "ARCHITECTURE_GEN_AUDIT: removed internal component "
                    "that conflicts with buy/adopt decision. component=%s "
                    "capability=%s solution=%s",
                    normalized.get("name"),
                    matching_decision.get("component"),
                    matching_decision.get("recommended_solution"),
                )
                continue

            if matching_decision:
                normalized["type"] = "external"
                normalized["ownership"] = "bought-saas"
            else:
                normalized["ownership"] = self._component_ownership(normalized)
            constrained.append(normalized)

        for decision in canonical_decisions:
            if not self._has_external_component_for_decision(
                constrained,
                decision,
            ):
                constrained.append(self._integration_component(decision))

        return constrained

    def _component_ownership(self, component: dict) -> str:
        """Return a valid ownership classification for a component."""
        ownership = component.get("ownership", "")
        if ownership == "bought-saas":
            component["type"] = "external"
            return "bought-saas"
        if ownership:
            return ownership
        component_type = component.get("type", "").lower()
        return DEFAULT_COMPONENT_OWNERSHIP.get(component_type, "enterprise-built")

    def _matching_canonical_decision(
        self,
        component: dict,
        canonical_decisions: list[dict],
    ) -> dict | None:
        """Return the decision whose excluded patterns overlap the component."""
        haystack = " ".join([
            str(component.get("name", "")),
            str(component.get("responsibility", "")),
        ]).lower()
        for decision in canonical_decisions:
            patterns = decision.get("excluded_component_patterns", [])
            if any(pattern and pattern in haystack for pattern in patterns):
                return decision
        return None

    def _has_external_component_for_decision(
        self,
        components: list[dict],
        decision: dict,
    ) -> bool:
        """Return True when a bought capability is represented externally."""
        solution = str(decision.get("recommended_solution", "")).lower()
        capability = str(decision.get("component", "")).lower()
        for component in components:
            if component.get("type", "").lower() != "external":
                continue
            text = " ".join([
                str(component.get("name", "")),
                str(component.get("technology", "")),
                str(component.get("responsibility", "")),
            ]).lower()
            if (
                (solution and solution in text)
                or (capability and capability in text)
            ):
                component["ownership"] = "bought-saas"
                return True
        return False

    def _integration_component(self, decision: dict) -> dict:
        """Create the required external integration component."""
        solution = decision.get("recommended_solution") or decision.get("component")
        return {
            "name": f"{solution} Integration",
            "type": "external",
            "ownership": "bought-saas",
            "technology": f"{solution} SDK/API",
            "responsibility": (
                f"Delegates all {decision.get('component')} "
                f"capability logic to {solution}."
            ),
            "characteristics": ["sourcing compliance"],
            "rationale": decision.get("constraint", ""),
        }

    def _validate_interactions(
        self,
        interactions: list[dict],
    ) -> list[dict]:
        """Reject interactions with undefined protocol or purpose.

        Args:
            interactions: Raw interaction objects from the architecture
                generator response.

        Returns:
            Interactions that satisfy the minimum interoperability contract.
        """
        valid: list[dict] = []
        for interaction in interactions:
            protocol = interaction.get("protocol", "").strip()
            purpose = interaction.get("purpose", "").strip()

            if protocol.lower() in INVALID_INTERACTION_FIELD_VALUES:
                logger.warning(
                    "Interaction rejected: undefined protocol. from=%s to=%s",
                    interaction.get("from"),
                    interaction.get("to"),
                )
                continue

            if purpose.lower() in INVALID_INTERACTION_FIELD_VALUES:
                logger.warning(
                    "Interaction rejected: undefined purpose. from=%s to=%s",
                    interaction.get("from"),
                    interaction.get("to"),
                )
                continue

            valid.append(interaction)

        rejected_count = len(interactions) - len(valid)
        if rejected_count:
            logger.warning(
                "Interaction validation: %d of %d interactions passed. "
                "%d rejected for undefined fields.",
                len(valid),
                len(interactions),
                rejected_count,
            )

        return valid

    def _validate_style_selection(
        self, result: dict, context: ArchitectureContext
    ) -> None:
        """Validate the style_selection block in the LLM response.

        Raises ToolExecutionException for hard failures (missing
        style_selection or blank selected_style). Logs warnings for
        soft issues (too few scores, short rationale, monolith bias).

        Args:
            result: The parsed JSON response from the LLM.
            context: The pipeline context for conversation_id logging.
        """
        # 1. style_selection must be present
        style_selection = result.get("style_selection")
        if not style_selection:
            raise ToolExecutionException(
                "Architecture generator did not perform style selection. "
                "The prompt requires explicit style scoring before design."
            )

        # 2. style_scores should contain all 8 styles
        style_scores = style_selection.get("style_scores", [])
        if len(style_scores) < EXPECTED_STYLE_COUNT:
            logger.warning(
                "Style selection scored only %d of %d expected styles. "
                "conversation_id=%s",
                len(style_scores),
                EXPECTED_STYLE_COUNT,
                context.conversation_id,
            )

        # 3. selected_style must not be blank
        selected_style = style_selection.get("selected_style", "")
        if not selected_style or not selected_style.strip():
            raise ToolExecutionException(
                "Architecture generator returned blank style selection."
            )

        # 4. selection_rationale must be substantive
        rationale = style_selection.get("selection_rationale", "")
        if len(rationale) < MIN_RATIONALE_LENGTH:
            logger.warning(
                "Style selection rationale is too brief — "
                "may indicate the LLM defaulted without reasoning. "
                "style=%s rationale_length=%d",
                selected_style,
                len(rationale),
            )

        # 5. Monolith bias check — warn if Layered selected despite
        #    characteristics that suggest a distributed style
        if selected_style.lower() in ("layered", "layered (n-tier)"):
            characteristic_names = {
                c.get("name", "").lower() for c in context.characteristics
            }
            distributed_signals = characteristic_names & DISTRIBUTED_SIGNAL_CHARACTERISTICS
            if distributed_signals:
                logger.warning(
                    "Layered architecture selected despite quality "
                    "characteristics that suggest a distributed style. "
                    "Review style_selection.selection_rationale. "
                    "distributed_signals=%s conversation_id=%s",
                    sorted(distributed_signals),
                    context.conversation_id,
                )

        # 6. when_to_reconsider_this_style must be present and non-empty
        reconsider = result.get("when_to_reconsider_this_style", [])
        if not reconsider:
            logger.warning(
                "Architecture design has no when_to_reconsider_this_style "
                "migration triggers. style=%s conversation_id=%s",
                selected_style,
                context.conversation_id,
            )


def _budget_parsed_entities(
    parsed_entities: dict,
    max_tokens: int,
) -> dict:
    """
    Budget list-valued parsed requirement sections.

    Args:
        parsed_entities: Requirement parser output.
        max_tokens: Token budget for parsed requirement lists.

    Returns:
        Copy of parsed_entities with long lists truncated.
    """
    budgeted = dict(parsed_entities)
    list_fields = [
        key for key, value in parsed_entities.items()
        if isinstance(value, list)
    ]
    if not list_fields:
        return budgeted

    per_field_budget = max(1, max_tokens // len(list_fields))
    for key in list_fields:
        budgeted[key] = budget_json_list(
            parsed_entities[key],
            max_tokens=per_field_budget,
            stage_name=_STAGE,
            item_label=f"parsed_entities.{key}",
        )
    return budgeted


def _format_component_list(components: list) -> str:
    """Format up to twenty previous components for the update prompt."""
    if not components:
        return "(none)"
    lines = []
    for component in components[:20]:
        if isinstance(component, dict):
            lines.append(
                f"  - {component.get('name', '')} "
                f"({component.get('type', 'internal')}): "
                f"{component.get('responsibility', '')}"
            )
        else:
            lines.append(f"  - {component}")
    return "\n".join(lines)

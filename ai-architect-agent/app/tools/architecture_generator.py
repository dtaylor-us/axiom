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

from app.llm.client import LLMClient
from app.memory.store import MemoryStore
from app.models import ArchitectureContext
from app.prompts.loader import load_prompt
from app.tools.base import BaseTool, ToolExecutionException

logger = logging.getLogger(__name__)

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

        # Retrieve similar past designs from Qdrant (best-effort)
        similar = await self._memory.retrieve_similar(
            context.raw_requirements, limit=3
        )
        context.similar_past_designs = similar

        # Pick a representative scenario as the target
        target_scenario = (
            context.scenarios[0] if context.scenarios else {}
        )

        prompt = load_prompt(
            "architecture_generator",
            parsed_entities=context.parsed_entities,
            characteristics=context.characteristics,
            characteristic_conflicts=context.characteristic_conflicts,
            target_scenario=target_scenario,
            scenarios=context.scenarios,
            similar_past_designs=similar,
            architecture_override=context.architecture_override,
            buy_vs_build_preferences=context.buy_vs_build_preferences,
        )

        raw = await self.llm_client.complete(prompt, response_format="json")

        try:
            result = json.loads(raw)
        except json.JSONDecodeError as exc:
            logger.error(
                "ArchitectureGenerator LLM returned invalid JSON: %s",
                raw[:500],
            )
            raise ToolExecutionException(
                f"LLM returned invalid JSON: {exc}"
            ) from exc

        # --- Validate style selection ---
        self._validate_style_selection(result, context)

        # --- Validate components ---
        components = result.get("components", [])
        if not components:
            raise ToolExecutionException(
                "Architecture generator returned an empty components list."
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
            "style=%s, runner_up=%s",
            len(components),
            style_selection.get("selected_style", "unknown"),
            style_selection.get("runner_up", "unknown"),
        )
        return context

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

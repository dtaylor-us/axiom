"""Diagram generation tool for the AI Architect Assistant.

Selects diagram types intelligently based on architecture style
and characteristics, then generates detailed Mermaid diagrams.

Selection logic follows these rules:
  MANDATORY: c4_container, sequence_primary, sequence_error
  CONDITIONAL: state, class, er, deployment, flowchart
               selected based on architecture style and
               primary characteristics (see _select_diagram_types)

Reference for Mermaid syntax: mermaid.js.org
"""

from __future__ import annotations

import json
import logging

from app.llm.client import LLMClient
from app.models.context import (
    ArchitectureContext, Diagram, DiagramType
)
from app.prompts.loader import load_prompt
from app.tools.base import BaseTool, ToolExecutionException

logger = logging.getLogger(__name__)

# Minimum acceptable length for a non-trivial diagram source.
# Diagrams shorter than this are almost certainly incomplete.
MIN_DIAGRAM_SOURCE_LINES = 10

# Maximum diagrams to generate per run.
# More than 5 is noise; fewer than 3 is insufficient.
MAX_DIAGRAMS = 5
MIN_DIAGRAMS = 3

# Mermaid syntax opening keywords per type.
# Used to validate that the LLM used the correct syntax.
EXPECTED_SYNTAX_PREFIXES: dict[DiagramType, tuple[str, ...]] = {
    DiagramType.C4_CONTAINER:     ("graph td", "graph TD"),
    DiagramType.SEQUENCE_PRIMARY: ("sequencediagram", "sequenceDiagram"),
    DiagramType.SEQUENCE_ERROR:   ("sequencediagram", "sequenceDiagram"),
    DiagramType.STATE:            ("statediagram-v2", "stateDiagram-v2"),
    DiagramType.CLASS:            ("classdiagram", "classDiagram"),
    DiagramType.ER:               ("erdiagram", "erDiagram"),
    DiagramType.DEPLOYMENT:       ("graph td", "graph TD"),
    DiagramType.FLOWCHART:        ("flowchart",),
}


class DiagramGeneratorTool(BaseTool):
    """Generates between 3 and 5 Mermaid diagrams for an architecture.

    The diagram types are selected based on:
      - Architecture style (from architecture_design.style)
      - Primary architecture characteristics
      - Always includes: c4_container, sequence_primary, sequence_error

    Guards:
      - Requires architecture_design to be populated
      - Requires characteristics to be populated
      - Validates syntax prefix of each generated diagram
      - Filters diagrams below minimum line count
      - Populates backward-compatible flat string fields
    """

    async def run(
        self, context: ArchitectureContext
    ) -> ArchitectureContext:
        """Select diagram types and generate detailed Mermaid source.

        Args:
            context: Pipeline state — reads architecture_design
                     and characteristics.

        Returns:
            Context with diagrams list and compat fields populated.

        Raises:
            ToolExecutionException: If architecture_design is empty,
                LLM returns invalid JSON, or all diagrams fail validation.
        """
        if not context.architecture_design:
            raise ToolExecutionException(
                "Cannot generate diagrams without architecture design. "
                "Ensure stage 6 (architecture_generation) completed."
            )

        if not context.characteristics:
            logger.warning(
                "Generating diagrams without characteristics. "
                "Conditional diagram selection will use defaults. "
                "conversation_id=%s", context.conversation_id
            )

        selected_types = self._select_diagram_types(
            context.architecture_design,
            context.characteristics
        )

        logger.info(
            "Diagram type selection: %s conversation_id=%s",
            [t.value for t in selected_types],
            context.conversation_id
        )

        prompt = load_prompt(
            "diagram_generator",
            parsed_entities=context.parsed_entities,
            architecture_design=context.architecture_design,
            characteristics=context.characteristics,
            selected_diagram_types=[t.value for t in selected_types],
        )

        raw = await self.llm_client.complete(
            prompt, response_format="json"
        )

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            logger.error(
                "DiagramGenerator LLM returned invalid JSON: %s",
                raw[:500],
            )
            raise ToolExecutionException(
                f"Diagram generator returned invalid JSON: {exc}. "
                f"Raw: {raw[:200]}"
            ) from exc

        raw_diagrams = parsed.get("diagrams", [])
        if not raw_diagrams:
            raise ToolExecutionException(
                "Diagram generator returned empty diagrams list."
            )

        validated = self._validate_diagrams(
            raw_diagrams, selected_types
        )

        context.diagrams = validated

        # Populate backward-compatible fields for any code
        # still referencing the Phase 3 flat string properties.
        context.mermaid_component_diagram = context.get_diagram(
            DiagramType.C4_CONTAINER
        )
        context.mermaid_sequence_diagram = context.get_diagram(
            DiagramType.SEQUENCE_PRIMARY
        )

        logger.info(
            "Diagram generation complete: %d diagrams produced. "
            "types=%s conversation_id=%s",
            len(validated),
            [d.type.value for d in validated],
            context.conversation_id
        )

        return context

    def _select_diagram_types(
        self,
        architecture_design: dict,
        characteristics: list[dict]
    ) -> list[DiagramType]:
        """Select diagram types based on architecture style and characteristics.

        Rules:
          Always includes: c4_container, sequence_primary, sequence_error.
          Conditional additions based on style and characteristics.
          Caps at MAX_DIAGRAMS by removing lowest-priority conditionals.

        This is a pure function — no LLM calls, no side effects.

        Args:
            architecture_design: Populated architecture design dict.
            characteristics: Inferred characteristics list.

        Returns:
            Ordered list of DiagramType values, 3 to 5 items.
        """
        selected: list[DiagramType] = [
            DiagramType.C4_CONTAINER,
            DiagramType.SEQUENCE_PRIMARY,
            DiagramType.SEQUENCE_ERROR,
        ]

        style = architecture_design.get("style", "").lower()

        # Build set of primary characteristic names — those that
        # are explicitly required or have a measurable target.
        primary_char_names: set[str] = {
            c.get("name", "").lower()
            for c in characteristics
            if c.get("current_requirement_coverage") == "explicit"
            or c.get("measurable_target", "")
        }

        # Style-driven conditional additions
        if any(s in style for s in ["event-driven", "microservices"]):
            if DiagramType.STATE not in selected:
                selected.append(DiagramType.STATE)

        if any(s in style for s in [
            "modular monolith", "service-based", "layered"
        ]):
            if DiagramType.CLASS not in selected:
                selected.append(DiagramType.CLASS)

        if "pipeline" in style:
            if DiagramType.FLOWCHART not in selected:
                selected.append(DiagramType.FLOWCHART)

        if "microkernel" in style:
            if DiagramType.CLASS not in selected:
                selected.append(DiagramType.CLASS)

        # Characteristic-driven conditional additions
        data_chars = {
            "data_integrity", "auditability", "data integrity",
        }
        if primary_char_names & data_chars:
            if DiagramType.ER not in selected:
                selected.append(DiagramType.ER)

        deploy_chars = {
            "deployability", "scalability", "elasticity",
        }
        if primary_char_names & deploy_chars:
            if DiagramType.DEPLOYMENT not in selected:
                selected.append(DiagramType.DEPLOYMENT)

        # Ensure minimum of MIN_DIAGRAMS
        if len(selected) < MIN_DIAGRAMS:
            if DiagramType.STATE not in selected:
                selected.append(DiagramType.STATE)

        # Cap at maximum — remove lowest priority conditionals first.
        # Priority: state > class > er > deployment > flowchart
        removal_priority = [
            DiagramType.FLOWCHART,
            DiagramType.DEPLOYMENT,
            DiagramType.ER,
            DiagramType.CLASS,
            DiagramType.STATE,
        ]
        while len(selected) > MAX_DIAGRAMS:
            for candidate in removal_priority:
                if candidate in selected:
                    selected.remove(candidate)
                    break

        return selected

    def _validate_diagrams(
        self,
        raw_diagrams: list[dict],
        expected_types: list[DiagramType]
    ) -> list[Diagram]:
        """Validate each raw diagram dict against quality rules.

        Filters diagrams that fail validation and logs warnings for
        each rejected diagram and each missing expected type.

        Validation rules:
          - mermaid_source must be present and non-empty
          - mermaid_source must be >= MIN_DIAGRAM_SOURCE_LINES lines
          - mermaid_source must not contain ``` fence characters
          - mermaid_source must start with the correct syntax keyword
          - title must not be blank
          - type field must be a valid DiagramType value

        Args:
            raw_diagrams: Unvalidated diagram dicts from LLM.
            expected_types: Types that were requested.

        Returns:
            List of validated Diagram instances.

        Raises:
            ToolExecutionException: If all diagrams fail validation.
        """
        validated: list[Diagram] = []
        seen_types: set[DiagramType] = set()

        for raw in raw_diagrams:
            diagram_id = raw.get("diagram_id", "unknown")
            reason = self._rejection_reason(raw)
            if reason:
                logger.warning(
                    "Diagram %s rejected: %s", diagram_id, reason
                )
                continue

            try:
                diagram_type = DiagramType(raw["type"])
            except (KeyError, ValueError) as exc:
                logger.warning(
                    "Diagram %s has invalid type '%s': %s",
                    diagram_id, raw.get("type"), exc
                )
                continue

            if diagram_type in seen_types:
                logger.warning(
                    "Duplicate diagram type %s — keeping first instance. "
                    "diagram_id=%s", diagram_type.value, diagram_id
                )
                continue

            try:
                diagram = Diagram(
                    diagram_id=diagram_id,
                    type=diagram_type,
                    title=raw.get("title", ""),
                    description=raw.get("description", ""),
                    mermaid_source=raw.get("mermaid_source", ""),
                    characteristic_addressed=raw.get(
                        "characteristic_addressed", ""
                    ),
                )
                validated.append(diagram)
                seen_types.add(diagram_type)
            except Exception as exc:
                logger.warning(
                    "Diagram %s failed model construction: %s",
                    diagram_id, exc
                )

        # Warn for any requested types that are missing from output
        returned_types = {d.type for d in validated}
        for expected in expected_types:
            if expected not in returned_types:
                logger.warning(
                    "Requested diagram type %s was not returned "
                    "by the LLM or failed validation.",
                    expected.value
                )

        if not validated:
            raise ToolExecutionException(
                "All generated diagrams failed validation. "
                f"Requested types: {[t.value for t in expected_types]}"
            )

        return validated

    def _rejection_reason(self, raw: dict) -> str | None:
        """Return a rejection reason string if the diagram fails quality checks.

        Args:
            raw: Unvalidated diagram dict from LLM output.

        Returns:
            Rejection reason string, or None if valid.
        """
        source = raw.get("mermaid_source", "")

        if not source:
            return "mermaid_source is empty"

        if "```" in source:
            return (
                "mermaid_source contains ``` fence characters — "
                "must be raw Mermaid source only"
            )

        lines = [line for line in source.strip().split("\n") if line.strip()]
        if len(lines) < MIN_DIAGRAM_SOURCE_LINES:
            return (
                f"mermaid_source has only {len(lines)} non-empty lines "
                f"(minimum {MIN_DIAGRAM_SOURCE_LINES}) — diagram is "
                f"too shallow to be useful"
            )

        # Validate syntax prefix for the declared type
        diagram_type_str = raw.get("type", "")
        try:
            diagram_type = DiagramType(diagram_type_str)
            expected_prefixes = EXPECTED_SYNTAX_PREFIXES.get(
                diagram_type, ()
            )
            first_line = lines[0].strip().lower()
            if expected_prefixes and not any(
                first_line.startswith(p.lower())
                for p in expected_prefixes
            ):
                return (
                    f"mermaid_source for type '{diagram_type_str}' "
                    f"starts with '{lines[0].strip()[:40]}' but "
                    f"expected one of: {expected_prefixes}"
                )
        except ValueError:
            pass  # type validation handled separately in _validate_diagrams

        if not raw.get("title", "").strip():
            return "title is blank"

        return None

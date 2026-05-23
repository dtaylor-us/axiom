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
from app.llm.schemas import SCHEMAS
from app.models.context import (
    ArchitectureContext, Diagram, DiagramType
)
from app.prompts.loader import load_prompt
from app.tools.base import BaseTool, ToolExecutionException

_STAGE_SINGLE = "diagram_generation_single"

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

MERMAID_OPENING_KEYWORDS = EXPECTED_SYNTAX_PREFIXES


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
        """Select diagram types and generate one Mermaid diagram per type.

        Each diagram type is generated in a dedicated LLM call so the model
        focuses entirely on one diagram at a time.  Partial success is
        preferred — only raises if ALL types fail.

        Args:
            context: Pipeline state — reads architecture_design
                     and characteristics.

        Returns:
            Context with diagrams list and compat fields populated.

        Raises:
            ToolExecutionException: If architecture_design is empty,
                or all diagram types fail generation/validation.
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
        logger.info(
            "DIAGNOSTIC: Diagram generation starting. "
            "method=per_type_sequential selected_types=%s session=%s",
            [t.value for t in selected_types],
            context.conversation_id,
        )

        failed_types: list[str] = []
        validated: list[Diagram] = []

        for diagram_type in selected_types:
            diagram = await self._generate_single_diagram(diagram_type, context)
            if diagram is not None:
                validated.append(diagram)
            else:
                failed_types.append(diagram_type.value)
                logger.warning(
                    "Diagram type %s failed generation. conversation_id=%s",
                    diagram_type.value, context.conversation_id,
                )

        if not validated:
            raise ToolExecutionException(
                f"All diagram types failed generation. "
                f"Requested types: {[t.value for t in selected_types]}"
            )

        context.diagrams = validated
        context.mermaid_component_diagram = context.get_diagram(
            DiagramType.C4_CONTAINER
        )
        context.mermaid_sequence_diagram = context.get_diagram(
            DiagramType.SEQUENCE_PRIMARY
        )

        logger.info(
            "Diagram generation complete: %d/%d diagrams produced. "
            "types=%s failed_types=%s conversation_id=%s",
            len(validated), len(selected_types),
            [d.type.value for d in validated],
            failed_types,
            context.conversation_id,
        )

        return context

    async def _generate_single_diagram(
        self,
        diagram_type: DiagramType,
        context: ArchitectureContext,
    ) -> Diagram | None:
        """Generate a single Mermaid diagram for the given type.

        Args:
            diagram_type: The diagram type to generate.
            context: Current pipeline context.

        Returns:
            Validated Diagram instance, or None if generation/validation failed.
        """
        prompt = load_prompt(
            "diagram_generator_single",
            diagram_type=diagram_type.value,
            parsed_entities=context.parsed_entities,
            architecture_design=context.architecture_design,
            characteristics=context.characteristics,
            canonical_decisions=context.canonical_decisions,
        )

        try:
            raw = await self.llm_client.complete(
                prompt,
                response_format="json",
                output_schema=SCHEMAS.get(_STAGE_SINGLE),
                schema_name=_STAGE_SINGLE,
                stage_name=_STAGE_SINGLE,
            )
        except Exception as exc:
            logger.warning(
                "LLM call failed for diagram type %s: %s",
                diagram_type.value, exc,
            )
            return None

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            logger.warning(
                "JSON parse failed for diagram type %s, attempting repair. error=%s",
                diagram_type.value, exc,
            )
            try:
                raw = await self.attempt_repair(
                    original_prompt=prompt,
                    failed_response=raw,
                    error_description=f"Invalid JSON: {exc}",
                    output_schema=SCHEMAS.get(_STAGE_SINGLE),
                    schema_name=_STAGE_SINGLE,
                    stage_name=_STAGE_SINGLE,
                )
                parsed = json.loads(raw)
            except Exception as repair_exc:
                logger.warning(
                    "Repair failed for diagram type %s: %s",
                    diagram_type.value, repair_exc,
                )
                # Return None so run() treats this type as a partial failure
                # rather than aborting the entire diagram generation run.
                return None

        if isinstance(parsed, dict) and "diagrams" in parsed:
            raw_diagrams = parsed.get("diagrams", [])
            if not raw_diagrams:
                raise ToolExecutionException("empty diagrams list")
            matching = [
                diagram for diagram in raw_diagrams
                if diagram.get("type") == diagram_type.value
            ]
            parsed = matching[0] if matching else raw_diagrams[0]

        # Inject the expected type so _rejection_reason can validate prefix
        parsed.setdefault("type", diagram_type.value)
        parsed.setdefault("diagram_id", diagram_type.value)

        reason = self._rejection_reason(parsed)
        if reason:
            logger.warning(
                "Diagram type %s rejected after generation: %s",
                diagram_type.value, reason,
            )
            return None

        source = parsed.get("mermaid_source", "")
        is_valid, error = self._validate_mermaid_syntax(
            source, diagram_type
        )
        if not is_valid:
            logger.warning(
                "Mermaid syntax validation failed. type=%s error=%s "
                "attempting repair. conversation_id=%s",
                diagram_type.value,
                error,
                context.conversation_id,
            )
            repaired_source = await self._repair_mermaid_source(
                source, diagram_type, error
            )
            is_valid_after_repair, error_after = (
                self._validate_mermaid_syntax(
                    repaired_source, diagram_type
                )
            )
            if is_valid_after_repair:
                source = repaired_source
                logger.info(
                    "Mermaid repair succeeded. type=%s conversation_id=%s",
                    diagram_type.value,
                    context.conversation_id,
                )
            else:
                logger.warning(
                    "Mermaid repair failed. type=%s error_after_repair=%s "
                    "storing with error. conversation_id=%s",
                    diagram_type.value,
                    error_after,
                    context.conversation_id,
                )
                return Diagram(
                    diagram_id=f"D-{diagram_type.value.upper()}",
                    type=diagram_type,
                    title=parsed.get("title", diagram_type.value),
                    description=parsed.get("description", ""),
                    mermaid_source=source,
                    characteristic_addressed=parsed.get(
                        "characteristic_addressed", ""
                    ),
                    has_syntax_error=True,
                    syntax_error_description=error_after,
                )

        try:
            return Diagram(
                diagram_id=f"D-{diagram_type.value.upper()}",
                type=diagram_type,
                title=parsed.get("title", ""),
                description=parsed.get("description", ""),
                mermaid_source=source,
                characteristic_addressed=parsed.get("characteristic_addressed", ""),
                has_syntax_error=False,
                syntax_error_description="",
            )
        except Exception as exc:
            logger.warning(
                "Diagram model construction failed for type %s: %s",
                diagram_type.value, exc,
            )
            return None

    async def _repair_mermaid_source(
        self,
        source: str,
        diagram_type: DiagramType,
        error: str,
    ) -> str:
        """Ask the LLM for one syntax-only Mermaid repair.

        Args:
            source: Original Mermaid source.
            diagram_type: Diagram type being repaired.
            error: Validation error that triggered repair.

        Returns:
            Repaired Mermaid source with accidental fences stripped.
        """
        repair_prompt = (
            "The following Mermaid diagram has a syntax error:\n"
            f"Error: {error}\n\n"
            f"Original source:\n{source}\n\n"
            "Fix ONLY the syntax error. Return valid "
            f"{diagram_type.value} Mermaid syntax. No markdown fences. "
            "No explanation. Common fixes:\n"
            "  - Quote edge labels containing special chars: |\"label text\"|\n"
            "  - Replace 'undefined' with a descriptive string\n"
            "  - Use --> not -> for directed edges in graph TD\n"
            "Return only the corrected Mermaid source."
        )
        repaired_raw = await self.llm_client.complete(
            repair_prompt, response_format="text", stage_name=_STAGE_SINGLE
        )
        repaired_source = repaired_raw.strip()
        if repaired_source.startswith("```"):
            lines = repaired_source.split("\n")
            repaired_source = "\n".join(lines[1:-1])
        return repaired_source

    def _validate_mermaid_syntax(
        self,
        source: str,
        diagram_type: DiagramType,
    ) -> tuple[bool, str]:
        """Perform lightweight Mermaid syntax validation before storage.

        Args:
            source: Mermaid source returned by the model.
            diagram_type: Expected diagram type.

        Returns:
            Tuple of validity flag and error description.
        """
        if not source or not source.strip():
            return False, "Empty Mermaid source"

        lines = [line for line in source.strip().split("\n") if line.strip()]
        if len(lines) < 3:
            return False, f"Too few lines: {len(lines)}"

        first_line = lines[0].strip().lower()
        expected = MERMAID_OPENING_KEYWORDS.get(diagram_type, ())
        if expected and not any(
            first_line.startswith(keyword.lower())
            for keyword in expected
        ):
            return False, (
                f"Wrong opening for {diagram_type.value}: "
                f"'{lines[0].strip()[:40]}'"
            )

        for line in lines:
            lower_line = line.lower()
            is_interaction = (
                "-->" in line or "---" in line or "[" in line or "(" in line
            )
            if (
                ("undefined" in lower_line or "null" in lower_line)
                and is_interaction
            ):
                return False, (
                    "Literal undefined/null in interaction: "
                    f"{line.strip()[:60]}"
                )

            if "-->" in line or "---" in line:
                if "|" in line:
                    first_label_delimiter = line.index("|")
                    second_label_delimiter = line.find(
                        "|", first_label_delimiter + 1
                    )
                    label_part = (
                        line[first_label_delimiter:second_label_delimiter + 1]
                        if second_label_delimiter != -1
                        else line[first_label_delimiter:]
                    )
                    has_quotes = '"' in label_part or "'" in label_part
                    if "(" in label_part and not has_quotes:
                        return False, (
                            "Unquoted parentheses in edge label: "
                            f"{line.strip()[:60]}"
                        )

        return True, ""

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

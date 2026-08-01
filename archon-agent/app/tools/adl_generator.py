"""
ADL generation tool implementing Mark Richards' Architecture
Definition Language specification.

Reference: developertoarchitect.com/downloads/adl-ref.pdf

ADL is pseudo-code that governs system structure and is designed
to be converted into executable fitness functions (ArchUnit,
NetArchTest, PyTestArch, or custom CI checks) via LLM code generation.
"""

import logging
import json
from app.llm.schemas import SCHEMAS
from app.tools.base import BaseTool, ToolExecutionException
from app.models.context import ArchitectureContext, AdlBlock, AdlMetadata
from app.prompts.loader import load_prompt

logger = logging.getLogger(__name__)

_STAGE = "adl_generation"

# Valid ADL keywords per the Richards specification.
# Any block using keywords outside this set is rejected.
VALID_ADL_KEYWORDS = {
    "REQUIRES", "DESCRIPTION", "PROMPT",
    "DEFINE", "SYSTEM", "DOMAIN", "SUBDOMAIN",
    "COMPONENT", "LIBRARY", "SERVICE", "CONST", "AS",
    "ASSERT", "FOREACH", "IN", "DO", "END",
    "CLASSES", "DOMAINS", "SUBDOMAINS", "COMPONENTS", "SERVICES",
    "CONTAINED", "WITHIN", "CONTAINS",
    "DEPENDS", "ON", "DEPENDENCY", "NO", "EXCLUSIVELY",
}

# REQUIRE (without S) is a common LLM mistake — catch it explicitly
FORBIDDEN_KEYWORDS = {"REQUIRE"}

# Minimum meaningful ADL source length in characters
MIN_ADL_SOURCE_LENGTH = 40

# Minimum ADL block count required from the architecture pipeline.
MIN_ADL_BLOCKS = 15


class ADLGeneratorV2Tool(BaseTool):
    """
    Generates Architecture Definition Language blocks following
    Mark Richards' ADL specification. Each block targets one
    architectural concern and includes a PROMPT field that enables
    an LLM to produce runnable ArchUnit or equivalent test code.

    Guards:
      - Requires architecture_design to be populated
      - Warns but continues when trade_offs is empty
      - Filters any block failing spec validation before writing
        to context
    """

    async def run(
        self, context: ArchitectureContext
    ) -> ArchitectureContext:
        """
        Generates and validates ADL blocks for the architecture.

        Args:
            context: Pipeline state — reads architecture_design,
                     trade_offs, characteristics, parsed_entities
        Returns:
            Context with adl_blocks and adl_document populated
        Raises:
            ToolExecutionException: if architecture_design is empty
        """
        if not context.architecture_design:
            raise ToolExecutionException(
                "Cannot generate ADL without architecture design. "
                "Ensure stage 6 (architecture_generation) completed."
            )

        if not context.trade_offs:
            logger.warning(
                "Generating ADL without trade-off decisions. "
                "Rule rationale will reference characteristics only. "
                "conversation_id=%s", context.conversation_id
            )

        canonical_decisions = context.canonical_decisions
        prompt = load_prompt(
            "adl_generator",
            parsed_entities=context.parsed_entities,
            architecture_design=context.architecture_design,
            trade_offs=context.trade_offs,
            characteristics=context.characteristics[:8],
            canonical_decisions=canonical_decisions,
            components=[
                component for component in context.architecture_design.get("components", [])
                if component.get("type") != "external"
            ],
            external_components=[
                component for component in context.architecture_design.get("components", [])
                if component.get("type") == "external"
            ],
            min_adl_blocks=MIN_ADL_BLOCKS,
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
        except json.JSONDecodeError as e:
            logger.warning(
                "ADLGenerator JSON parse failed, attempting repair. error=%s", e
            )
            repair_attempted = True
            raw = await self.attempt_repair(
                original_prompt=prompt,
                failed_response=raw,
                error_description=f"Invalid JSON: {e}",
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

        # The LLM may return one of three shapes:
        #   a) A JSON array of blocks                        — canonical format
        #   b) {"adl_blocks": [...]}                         — json_object wrapper
        #   c) A single block dict (LLM ignored the array instruction)
        # All three are normalised to a list here so downstream validation is
        # consistent.
        if isinstance(parsed, dict):
            if "adl_blocks" in parsed:
                parsed = parsed["adl_blocks"]
            elif "adl_id" in parsed:
                # LLM returned one block as a bare object instead of a one-element
                # array. Wrap it so validation proceeds normally.
                logger.warning(
                    "ADL generator returned a single block object instead of an "
                    "array. Wrapping automatically. conversation_id=%s",
                    context.conversation_id,
                )
                parsed = [parsed]
            else:
                raise ToolExecutionException(
                    "ADL generator returned a JSON object with no 'adl_blocks' or "
                    f"'adl_id' key. Keys found: {list(parsed.keys())}"
                )

        if not isinstance(parsed, list):
            raise ToolExecutionException(
                "ADL generator must return a JSON array or object with adl_blocks. "
                f"Got type: {type(parsed).__name__}"
            )

        logger.info(
            "ADL_GENERATION: produced %d blocks. conversation_id=%s",
            len(parsed), context.conversation_id,
        )

        minimum_blocks = max(MIN_ADL_BLOCKS, len(canonical_decisions) + 3)
        if len(parsed) < minimum_blocks:
            logger.warning(
                "ADL_GENERATION: only %d blocks generated. Minimum is %d. "
                "This may indicate the prompt is not receiving enough "
                "architecture context, or the model is satisfying the schema "
                "with minimum output. conversation_id=%s",
                len(parsed), minimum_blocks,
                context.conversation_id,
            )

        validated = self._validate_blocks(parsed)

        logger.info(
            "ADL generation complete: %d blocks produced, "
            "%d passed validation. conversation_id=%s",
            len(parsed), len(validated), context.conversation_id
        )

        context.adl_blocks = validated
        # Keep adl_rules populated for backward compatibility
        context.adl_rules = [b.model_dump() for b in validated]
        context.adl_document = self._render_adl_document(validated)

        return context

    def _validate_blocks(
        self, raw_blocks: list[dict]
    ) -> list[AdlBlock]:
        """
        Validates each raw block against the Richards ADL spec.
        Filters and logs any block that fails — never raises.

        Validation rules:
          - adl_source must be present and >= MIN_ADL_SOURCE_LENGTH
          - adl_source must not contain FORBIDDEN_KEYWORDS
          - metadata.requires must be non-blank
          - metadata.prompt must be non-blank
          - adl_source must contain DEFINE SYSTEM
          - adl_source must contain at least one ASSERT or FOREACH

        Args:
            raw_blocks: Unvalidated dicts from LLM output
        Returns:
            List of valid AdlBlock instances
        """
        validated = []
        for raw in raw_blocks:
            adl_id = raw.get("adl_id", "unknown")
            reason = self._rejection_reason(raw)
            if reason:
                logger.warning(
                    "ADL block %s rejected: %s", adl_id, reason
                )
                continue
            try:
                meta = raw.get("metadata", {})
                block = AdlBlock(
                    adl_id=adl_id,
                    metadata=AdlMetadata(
                        requires=meta.get("requires", ""),
                        description=meta.get("description", ""),
                        prompt=meta.get("prompt", ""),
                    ),
                    adl_source=raw.get("adl_source", ""),
                    characteristic_enforced=raw.get(
                        "characteristic_enforced", ""
                    ),
                    enforcement_level=raw.get(
                        "enforcement_level", "soft"
                    ),
                )
                validated.append(block)
            except Exception as e:
                logger.warning(
                    "ADL block %s failed model construction: %s",
                    adl_id, e
                )
        return validated

    def _rejection_reason(self, raw: dict) -> str | None:
        """
        Returns a human-readable rejection reason if the block
        fails spec validation, or None if it passes.

        Args:
            raw: Unvalidated block dict
        Returns:
            Rejection reason string, or None if valid
        """
        source = raw.get("adl_source", "")
        meta = raw.get("metadata", {})

        if not source or len(source) < MIN_ADL_SOURCE_LENGTH:
            return (
                f"adl_source too short ({len(source)} chars, "
                f"minimum {MIN_ADL_SOURCE_LENGTH})"
            )

        source_upper = source.upper()

        for forbidden in FORBIDDEN_KEYWORDS:
            if forbidden in source_upper.split():
                return (
                    f"contains forbidden keyword '{forbidden}' — "
                    f"correct keyword is '{forbidden}S'"
                )

        if "DEFINE SYSTEM" not in source_upper:
            return "missing required DEFINE SYSTEM declaration"

        if "ASSERT" not in source_upper and "FOREACH" not in source_upper:
            return "must contain at least one ASSERT or FOREACH statement"

        if not meta.get("requires", "").strip():
            return "metadata.requires is blank — must name the test tooling"

        if not meta.get("prompt", "").strip():
            return (
                "metadata.prompt is blank — must contain LLM "
                "instruction to generate runnable test code"
            )

        return None

    def _render_adl_document(
        self, blocks: list[AdlBlock]
    ) -> str:
        """
        Renders the validated ADL blocks as a Markdown document.

        The ADL pseudo-code is preserved verbatim in fenced code
        blocks so downstream tooling can extract and send it to
        an LLM for test code generation without any parsing.

        Args:
            blocks: Validated AdlBlock list
        Returns:
            Markdown string with all blocks and metadata
        """
        lines = [
            "# Architecture Definition Language\n",
            "_Mark Richards ADL specification — "
            "developertoarchitect.com/downloads/adl-ref.pdf_\n",
        ]

        hard = [b for b in blocks if b.enforcement_level == "hard"]
        soft = [b for b in blocks if b.enforcement_level == "soft"]

        lines.append(
            f"**{len(blocks)} blocks total** — "
            f"{len(hard)} hard enforcement, "
            f"{len(soft)} soft enforcement\n"
        )
        lines.append("---\n")

        for block in blocks:
            lines.append(
                f"## {block.adl_id}: {block.metadata.description}\n"
            )
            lines.append(
                f"**Enforcement:** {block.enforcement_level}  "
            )
            lines.append(
                f"**Characteristic:** {block.characteristic_enforced}  "
            )
            lines.append(
                f"**Tooling:** {block.metadata.requires}\n"
            )
            lines.append(
                f"**Code generation prompt:** "
                f"`{block.metadata.prompt}`\n"
            )
            lines.append("```adl")
            # Render full ADL block with metadata headers
            lines.append(f"REQUIRES {block.metadata.requires}")
            lines.append(f"DESCRIPTION {block.metadata.description}")
            lines.append(f"PROMPT {block.metadata.prompt}")
            lines.append("")
            lines.append(block.adl_source)
            lines.append("```\n")

        return "\n".join(lines)

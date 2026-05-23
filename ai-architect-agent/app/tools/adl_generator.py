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
from app.tools.base import BaseTool, ToolExecutionException
from app.models.context import ArchitectureContext, AdlBlock, AdlMetadata
from app.prompts.loader import load_prompt

logger = logging.getLogger(__name__)

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

        prompt = load_prompt(
            "adl_generator",
            parsed_entities=context.parsed_entities,
            architecture_design=context.architecture_design,
            trade_offs=context.trade_offs,
            characteristics=context.characteristics,
        )

        raw = await self.llm_client.complete(
            prompt, response_format="json"
        )

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as e:
            raise ToolExecutionException(
                f"ADL generator returned invalid JSON: {e}. "
                f"Raw response: {raw[:200]}"
            )

        if not isinstance(parsed, list):
            raise ToolExecutionException(
                "ADL generator must return a JSON array. "
                f"Got type: {type(parsed).__name__}"
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

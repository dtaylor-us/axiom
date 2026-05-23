"""Architecture tactics advisor tool.

Recommends named architecture tactics for each inferred quality attribute,
sourced from the Bass, Clements, Kazman catalog
(Software Architecture in Practice, 4th ed., SEI/Addison-Wesley 2021).

A tactic is a focused design decision that influences a single quality
attribute response. This tool bridges the gap between knowing WHAT quality
attributes matter (stage 4) and knowing HOW to achieve them in the
architecture design (stage 6).

Pipeline position: stage 4b — after CharacteristicReasoningEngine (stage 4),
before CharacteristicConflictAnalyzer (stage 5).

Guards:
    - Requires characteristics to be populated (stage 4 must run first).
    - Warns but continues if architecture_design is empty (tactics can still
      be recommended before design is generated; concrete_application will
      be less specific).
    - Validates each tactic against required fields before writing to context.
"""

from __future__ import annotations

import json
import logging

from app.llm.client import LLMClient
from app.models.context import ArchitectureContext, TacticRecommendation
from app.prompts.loader import load_prompt
from app.tools.base import BaseTool, ToolExecutionException

logger = logging.getLogger(__name__)

# Minimum tactics per run to be considered useful output.
# Fewer than this indicates the LLM produced near-empty output.
MIN_TACTICS = 4

# Minimum character lengths for quality-sensitive free-text fields.
# Too-short values indicate the LLM produced generic, non-specific content.
MIN_DESCRIPTION_LENGTH = 20
MIN_CONCRETE_APPLICATION_LENGTH = 30

# Valid enum values for effort and priority — mirrors TacticRecommendation.
VALID_EFFORT: frozenset[str] = frozenset({"low", "medium", "high"})
VALID_PRIORITY: frozenset[str] = frozenset({"critical", "recommended", "optional"})


class TacticsAdvisorTool(BaseTool):
    """Recommends architecture tactics for each inferred quality attribute.

    Draws exclusively from the Bass/Clements/Kazman catalog
    (Software Architecture in Practice, 4th ed., 2021) or equivalent
    authoritative SEI references.

    Reads stages 4 output (characteristics, architecture_design,
    characteristic_conflicts) and writes stage 4b output (tactics,
    tactics_summary).
    """

    async def run(
        self, context: ArchitectureContext
    ) -> ArchitectureContext:
        """Recommend tactics for each inferred characteristic.

        Reads:  context.characteristics, context.architecture_design,
                context.characteristic_conflicts, context.parsed_entities
        Writes: context.tactics (list of TacticRecommendation dicts),
                context.tactics_summary

        Args:
            context: Pipeline state after stage 4 has completed.

        Returns:
            context with tactics and tactics_summary populated.

        Raises:
            ToolExecutionException: if characteristics list is empty,
                or if the LLM returns invalid JSON.
        """
        if not context.characteristics:
            raise ToolExecutionException(
                "Cannot recommend tactics without inferred characteristics. "
                "Ensure stage 4 (characteristic_inference) completed."
            )

        if not context.architecture_design:
            logger.warning(
                "Recommending tactics before architecture design is available. "
                "concrete_application fields will be less specific. "
                "conversation_id=%s",
                context.conversation_id,
            )

        prompt = load_prompt(
            "tactics_advisor",
            parsed_entities=context.parsed_entities,
            characteristics=context.characteristics,
            architecture_design=context.architecture_design,
            characteristic_conflicts=context.characteristic_conflicts,
        )

        raw = await self.llm_client.complete(prompt, response_format="json")

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            logger.error(
                "TacticsAdvisor LLM returned invalid JSON: %s",
                raw[:500],
            )
            raise ToolExecutionException(
                f"Tactics advisor returned invalid JSON: {exc}. "
                f"Raw response (first 300 chars): {raw[:300]}"
            ) from exc

        raw_tactics: list[dict] = parsed.get("tactics", [])

        valid_tactics: list[TacticRecommendation] = []
        for raw_tactic in raw_tactics:
            tactic_id = raw_tactic.get("tactic_id", "unknown")
            rejection_reason = self._validate_tactic(raw_tactic)
            if rejection_reason:
                logger.warning(
                    "Tactic %s rejected: %s", tactic_id, rejection_reason
                )
                continue

            try:
                tactic = TacticRecommendation(**raw_tactic)
                valid_tactics.append(tactic)
            except Exception as exc:
                logger.warning(
                    "Tactic %s failed Pydantic validation: %s",
                    tactic_id, exc,
                )

        if len(valid_tactics) < MIN_TACTICS:
            logger.warning(
                "TacticsAdvisor produced only %d valid tactics "
                "(minimum expected: %d). "
                "conversation_id=%s",
                len(valid_tactics),
                MIN_TACTICS,
                context.conversation_id,
            )

        already_addressed_count = sum(
            1 for t in valid_tactics if t.already_addressed
        )
        new_count = len(valid_tactics) - already_addressed_count

        context.tactics = [t.model_dump() for t in valid_tactics]
        context.tactics_summary = parsed.get("tactics_summary", "")

        characteristics_covered = len({
            t.characteristic_name for t in valid_tactics
        })

        logger.info(
            "Tactics recommendation complete: %d tactics across %d characteristics. "
            "already_addressed=%d new=%d conversation_id=%s",
            len(valid_tactics),
            characteristics_covered,
            already_addressed_count,
            new_count,
            context.conversation_id,
        )

        return context

    def _validate_tactic(self, raw: dict) -> str | None:
        """Return a rejection reason if the tactic fails validation, else None.

        Validation rules:
          - tactic_name must be non-blank
          - characteristic_name must be non-blank
          - description must be non-blank and >= MIN_DESCRIPTION_LENGTH chars
          - concrete_application must be non-blank and >= MIN_CONCRETE_APPLICATION_LENGTH
            chars (too short means it is a generic statement, not system-specific)
          - effort must be one of: low, medium, high
          - priority must be one of: critical, recommended, optional
          - implementation_examples must be a list with at least 1 item

        Args:
            raw: Unvalidated tactic dict from LLM output.

        Returns:
            Rejection reason string, or None if valid.
        """
        tactic_name = raw.get("tactic_name", "")
        if not str(tactic_name).strip():
            return "tactic_name is blank"

        characteristic_name = raw.get("characteristic_name", "")
        if not str(characteristic_name).strip():
            return "characteristic_name is blank"

        description = raw.get("description", "")
        if not str(description).strip():
            return "description is blank"
        if len(str(description).strip()) < MIN_DESCRIPTION_LENGTH:
            return (
                f"description is too short ({len(str(description).strip())} chars, "
                f"minimum {MIN_DESCRIPTION_LENGTH}) — not a real tactic definition"
            )

        concrete_application = raw.get("concrete_application", "")
        if not str(concrete_application).strip():
            return "concrete_application is blank"
        if len(str(concrete_application).strip()) < MIN_CONCRETE_APPLICATION_LENGTH:
            return (
                f"concrete_application is too short "
                f"({len(str(concrete_application).strip())} chars, "
                f"minimum {MIN_CONCRETE_APPLICATION_LENGTH}) — "
                "not specific to this system"
            )

        effort = raw.get("effort", "")
        if str(effort).strip().lower() not in VALID_EFFORT:
            return f"effort '{effort}' is not one of: {sorted(VALID_EFFORT)}"

        priority = raw.get("priority", "")
        if str(priority).strip().lower() not in VALID_PRIORITY:
            return f"priority '{priority}' is not one of: {sorted(VALID_PRIORITY)}"

        examples = raw.get("implementation_examples", [])
        if not isinstance(examples, list) or len(examples) < 1:
            return "implementation_examples must be a list with at least 1 item"

        return None

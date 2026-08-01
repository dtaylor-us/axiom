from __future__ import annotations

import json
import logging

from app.llm.client import LLMClient
from app.llm.schemas import SCHEMAS
from app.models import ArchitectureContext
from app.prompts.loader import load_prompt
from app.tools.base import BaseTool, ToolExecutionException

logger = logging.getLogger(__name__)

_STAGE = "conflict_analysis"


class CharacteristicConflictAnalyzerTool(BaseTool):
    """Analyses tensions and conflicts between architecture characteristics.

    Applies provider-native structured output enforcement (Layer 1) via the
    SCHEMAS registry, and one repair attempt on JSON parse failure (Layer 2).
    """

    async def run(self, context: ArchitectureContext) -> ArchitectureContext:
        if not context.characteristics:
            raise ToolExecutionException(
                "characteristics is empty; run CharacteristicReasoningEngine first"
            )

        prompt = load_prompt(
            "conflict_analyzer",
            parsed_entities=context.parsed_entities,
            characteristics=context.characteristics,
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
            result = json.loads(raw)
        except json.JSONDecodeError as e:
            logger.warning(
                "ConflictAnalyzer JSON parse failed, attempting repair. error=%s", e
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
                result = json.loads(raw)
            except json.JSONDecodeError as e2:
                raise ToolExecutionException(
                    f"Stage output could not be parsed after repair attempt. error={e2}"
                ) from e2

        context.characteristic_conflicts = result.get("conflicts", [])
        context.underrepresented_characteristics = result.get(
            "underrepresented", []
        )
        context.overspecified_characteristics = result.get("overspecified", [])
        context.tension_summary = result.get("tension_summary", "")
        logger.info(
            "ConflictAnalyzer found %d conflicts, %d underrepresented, "
            "%d overspecified repair_attempted=%s",
            len(context.characteristic_conflicts),
            len(context.underrepresented_characteristics),
            len(context.overspecified_characteristics),
            repair_attempted,
        )
        return context

    async def run(self, context: ArchitectureContext) -> ArchitectureContext:
        if not context.characteristics:
            raise ToolExecutionException(
                "characteristics is empty; run CharacteristicReasoningEngine first"
            )

        prompt = load_prompt(
            "conflict_analyzer",
            parsed_entities=context.parsed_entities,
            characteristics=context.characteristics,
        )

        raw = await self.llm_client.complete(
            prompt, response_format="json", stage_name=_STAGE
        )

        try:
            result = json.loads(raw)
        except json.JSONDecodeError as e:
            logger.error(
                "ConflictAnalyzer LLM returned invalid JSON: %s", raw[:500]
            )
            raise ToolExecutionException(f"LLM returned invalid JSON: {e}") from e

        context.characteristic_conflicts = result.get("conflicts", [])
        context.underrepresented_characteristics = result.get(
            "underrepresented", []
        )
        context.overspecified_characteristics = result.get("overspecified", [])
        context.tension_summary = result.get("tension_summary", "")
        logger.info(
            "ConflictAnalyzer found %d conflicts, %d underrepresented, %d overspecified",
            len(context.characteristic_conflicts),
            len(context.underrepresented_characteristics),
            len(context.overspecified_characteristics),
        )
        return context

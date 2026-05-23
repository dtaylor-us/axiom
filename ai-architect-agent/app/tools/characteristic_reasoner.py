from __future__ import annotations

import json
import logging

from app.llm.client import LLMClient
from app.llm.schemas import SCHEMAS
from app.models import ArchitectureContext
from app.prompts.loader import load_prompt
from app.tools.base import BaseTool, ToolExecutionException

logger = logging.getLogger(__name__)

_STAGE = "characteristic_inference"


class CharacteristicReasoningEngineTool(BaseTool):
    """Infers architecture characteristics from parsed requirements and scenarios.

    Applies provider-native structured output enforcement (Layer 1) via the
    SCHEMAS registry, and one repair attempt on JSON parse failure (Layer 2).
    """

    async def run(self, context: ArchitectureContext) -> ArchitectureContext:
        if not context.parsed_entities:
            raise ToolExecutionException(
                "parsed_entities is empty; run RequirementParser first"
            )

        prompt = load_prompt(
            "characteristic_reasoner",
            raw_requirements=context.raw_requirements,
            parsed_entities=context.parsed_entities,
            scenarios=context.scenarios,
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
                "CharacteristicReasoningEngine JSON parse failed, "
                "attempting repair. error=%s", e
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

        context.characteristics = result.get("characteristics", [])
        logger.info(
            "CharacteristicReasoningEngine inferred %d characteristics "
            "repair_attempted=%s",
            len(context.characteristics),
            repair_attempted,
        )
        return context

    async def run(self, context: ArchitectureContext) -> ArchitectureContext:
        if not context.parsed_entities:
            raise ToolExecutionException(
                "parsed_entities is empty; run RequirementParser first"
            )

        prompt = load_prompt(
            "characteristic_reasoner",
            raw_requirements=context.raw_requirements,
            parsed_entities=context.parsed_entities,
            scenarios=context.scenarios,
        )

        raw = await self.llm_client.complete(
            prompt, response_format="json", stage_name=_STAGE
        )

        try:
            result = json.loads(raw)
        except json.JSONDecodeError as e:
            logger.error(
                "CharacteristicReasoningEngine LLM returned invalid JSON: %s",
                raw[:500],
            )
            raise ToolExecutionException(f"LLM returned invalid JSON: {e}") from e

        context.characteristics = result.get("characteristics", [])
        logger.info(
            "CharacteristicReasoningEngine inferred %d characteristics",
            len(context.characteristics),
        )
        return context

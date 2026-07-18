from __future__ import annotations

import json
import logging

from app.llm.client import LLMClient
from app.llm.schemas import SCHEMAS
from app.models import ArchitectureContext
from app.prompts.loader import load_prompt
from app.tools.base import BaseTool, ToolExecutionException

logger = logging.getLogger(__name__)

_STAGE = "requirement_parsing"


class RequirementParserTool(BaseTool):
    """Parses raw requirements into structured entities using the LLM.

    Applies provider-native structured output enforcement (Layer 1) via the
    SCHEMAS registry, and one repair attempt on JSON parse failure (Layer 2).
    """

    async def run(self, context: ArchitectureContext) -> ArchitectureContext:
        if not context.raw_requirements:
            raise ToolExecutionException("raw_requirements is empty; nothing to parse")

        prompt = load_prompt(
            "requirement_parser",
            raw_requirements=context.raw_requirements,
            project_memory_context=json.dumps(
                context.project_memory_context or {},
                indent=2,
                sort_keys=True,
            ),
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
                "RequirementParser JSON parse failed, attempting repair. error=%s", e
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

        context.parsed_entities = parsed
        logger.info(
            "RequirementParser extracted domain=%s, system_type=%s, %d FRs "
            "repair_attempted=%s",
            parsed.get("domain", "unknown"),
            parsed.get("system_type", "unknown"),
            len(parsed.get("functional_requirements", [])),
            repair_attempted,
        )
        return context

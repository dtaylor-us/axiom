from __future__ import annotations

import json
import logging

from app.llm.client import LLMClient
from app.models import ArchitectureContext
from app.prompts.loader import load_prompt
from app.tools.base import BaseTool, ToolExecutionException

logger = logging.getLogger(__name__)


class RequirementParserTool(BaseTool):
    """Parses raw requirements into structured entities using the LLM."""

    async def run(self, context: ArchitectureContext) -> ArchitectureContext:
        if not context.raw_requirements:
            raise ToolExecutionException("raw_requirements is empty; nothing to parse")

        prompt = load_prompt("requirement_parser", raw_requirements=context.raw_requirements)

        raw = await self.llm_client.complete(prompt, response_format="json")

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as e:
            logger.error("RequirementParser LLM returned invalid JSON: %s", raw[:500])
            raise ToolExecutionException(f"LLM returned invalid JSON: {e}") from e

        context.parsed_entities = parsed
        logger.info(
            "RequirementParser extracted domain=%s, system_type=%s, %d FRs",
            parsed.get("domain", "unknown"),
            parsed.get("system_type", "unknown"),
            len(parsed.get("functional_requirements", [])),
        )
        return context

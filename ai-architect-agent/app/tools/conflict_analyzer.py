from __future__ import annotations

import json
import logging

from app.llm.client import LLMClient
from app.models import ArchitectureContext
from app.prompts.loader import load_prompt
from app.tools.base import BaseTool, ToolExecutionException

logger = logging.getLogger(__name__)


class CharacteristicConflictAnalyzerTool(BaseTool):
    """Analyses tensions and conflicts between architecture characteristics."""

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

        raw = await self.llm_client.complete(prompt, response_format="json")

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

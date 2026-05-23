from __future__ import annotations

import json
import logging

from app.llm.client import LLMClient
from app.models import ArchitectureContext
from app.prompts.loader import load_prompt
from app.tools.base import BaseTool, ToolExecutionException

logger = logging.getLogger(__name__)


class ScenarioModelerTool(BaseTool):
    """Models small / medium / large scale scenarios for the system."""

    async def run(self, context: ArchitectureContext) -> ArchitectureContext:
        if not context.parsed_entities:
            raise ToolExecutionException(
                "parsed_entities is empty; run RequirementParser first"
            )

        prompt = load_prompt(
            "scenario_modeler",
            raw_requirements=context.raw_requirements,
            parsed_entities=context.parsed_entities,
        )

        raw = await self.llm_client.complete(prompt, response_format="json")

        try:
            result = json.loads(raw)
        except json.JSONDecodeError as e:
            logger.error("ScenarioModeler LLM returned invalid JSON: %s", raw[:500])
            raise ToolExecutionException(f"LLM returned invalid JSON: {e}") from e

        context.scenarios = result.get("scenarios", [])
        logger.info(
            "ScenarioModeler produced %d tier scenarios",
            len(context.scenarios),
        )
        return context

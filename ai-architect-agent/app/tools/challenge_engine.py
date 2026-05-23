from __future__ import annotations

import json
import logging

from app.llm.client import LLMClient
from app.models import ArchitectureContext
from app.prompts.loader import load_prompt
from app.tools.base import BaseTool, ToolExecutionException

logger = logging.getLogger(__name__)


class RequirementChallengeEngineTool(BaseTool):
    """Challenges the parsed requirements to find gaps and ambiguities."""

    async def run(self, context: ArchitectureContext) -> ArchitectureContext:
        if not context.parsed_entities:
            raise ToolExecutionException(
                "parsed_entities is empty; run RequirementParser first"
            )

        prompt = load_prompt(
            "requirement_challenge",
            raw_requirements=context.raw_requirements,
            parsed_entities=context.parsed_entities,
            review_constraints=context.review_constraints,
        )

        raw = await self.llm_client.complete(prompt, response_format="json")

        try:
            result = json.loads(raw)
        except json.JSONDecodeError as e:
            logger.error("ChallengeEngine LLM returned invalid JSON: %s", raw[:500])
            raise ToolExecutionException(f"LLM returned invalid JSON: {e}") from e

        context.missing_requirements = result.get("missing_requirements", [])
        context.ambiguities = result.get("ambiguities", [])
        context.hidden_assumptions = result.get("hidden_assumptions", [])
        context.clarifying_questions = result.get("clarifying_questions", [])

        context.architecture_override = result.get(
            "architecture_override",
            {
                "type": "none",
                "styles": [],
                "raw_instruction": "",
                "detected_confidence": "low",
            },
        )
        context.buy_vs_build_preferences = result.get(
            "buy_vs_build_preferences",
            {
                "prefer_open_source": False,
                "avoid_vendor_lockin": False,
                "existing_tools": [],
                "build_preference": "neutral",
                "budget_constrained": False,
                "raw_signals": [],
            },
        )

        logger.info(
            "ChallengeEngine found %d missing reqs, %d ambiguities, %d assumptions, %d questions",
            len(context.missing_requirements),
            len(context.ambiguities),
            len(context.hidden_assumptions),
            len(context.clarifying_questions),
        )
        return context

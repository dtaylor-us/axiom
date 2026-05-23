from __future__ import annotations

import json
import logging

from app.llm.client import LLMClient
from app.models import ArchitectureContext
from app.prompts.loader import load_prompt
from app.tools.base import BaseTool, ToolExecutionException

logger = logging.getLogger(__name__)

_VALID_CATEGORIES = {"fragility", "scale_limit", "redesign_point", "operational"}


class WeaknessAnalyzerTool(BaseTool):
    """Performs architectural fragility and weakness analysis."""

    async def run(self, context: ArchitectureContext) -> ArchitectureContext:
        if not context.architecture_design:
            raise ToolExecutionException(
                "Cannot analyze weaknesses without architecture design"
            )

        prompt = load_prompt(
            "weakness_analyzer",
            parsed_entities=context.parsed_entities,
            architecture_design=context.architecture_design,
            characteristics=context.characteristics,
            scenarios=context.scenarios,
            trade_offs=context.trade_offs,
        )

        raw = await self.llm_client.complete(prompt, response_format="json")

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as e:
            logger.error(
                "WeaknessAnalyzer LLM returned invalid JSON: %s", raw[:500]
            )
            raise ToolExecutionException(
                f"LLM returned invalid JSON: {e}"
            ) from e

        weaknesses = parsed.get("weaknesses", [])
        validated: list[dict] = []

        for w in weaknesses:
            severity = w.get("severity")
            likelihood = w.get("likelihood")
            category = w.get("category", "")
            signals = w.get("early_warning_signals", [])

            if not isinstance(severity, int) or severity < 1 or severity > 5:
                logger.warning(
                    "WeaknessAnalyzer: dropping weakness %s — invalid severity: %s",
                    w.get("id", "unknown"),
                    severity,
                )
                continue
            if not isinstance(likelihood, int) or likelihood < 1 or likelihood > 5:
                logger.warning(
                    "WeaknessAnalyzer: dropping weakness %s — invalid likelihood: %s",
                    w.get("id", "unknown"),
                    likelihood,
                )
                continue
            if category not in _VALID_CATEGORIES:
                logger.warning(
                    "WeaknessAnalyzer: dropping weakness %s — invalid category: '%s'",
                    w.get("id", "unknown"),
                    category,
                )
                continue
            if not isinstance(signals, list) or len(signals) == 0:
                logger.warning(
                    "WeaknessAnalyzer: dropping weakness %s — empty early_warning_signals",
                    w.get("id", "unknown"),
                )
                continue

            validated.append(w)

        # Sort by (severity + likelihood) descending
        validated.sort(
            key=lambda x: x.get("severity", 0) + x.get("likelihood", 0),
            reverse=True,
        )

        context.weaknesses = validated
        context.weakness_summary = parsed.get("weakness_summary", "")

        logger.info(
            "WeaknessAnalyzer produced %d validated weaknesses (dropped %d)",
            len(validated),
            len(weaknesses) - len(validated),
        )
        return context

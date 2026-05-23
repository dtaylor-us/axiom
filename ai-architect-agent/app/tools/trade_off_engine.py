from __future__ import annotations

import json
import logging

from app.llm.client import LLMClient
from app.llm.schemas import SCHEMAS
from app.models import ArchitectureContext
from app.prompts.loader import load_prompt
from app.tools.base import BaseTool, ToolExecutionException

logger = logging.getLogger(__name__)

_STAGE = "trade_off_analysis"
_VALID_CONFIDENCE = {"high", "medium", "low"}


class TradeOffEngineTool(BaseTool):
    """Performs trade-off analysis on architectural decisions."""

    async def run(self, context: ArchitectureContext) -> ArchitectureContext:
        if not context.architecture_design:
            raise ToolExecutionException(
                "Cannot run trade-off analysis without architecture design"
            )
        if not context.characteristics:
            raise ToolExecutionException(
                "Cannot run trade-off analysis without characteristics"
            )

        prompt = load_prompt(
            "trade_off_engine",
            parsed_entities=context.parsed_entities,
            architecture_design=context.architecture_design,
            characteristics=context.characteristics,
            characteristic_conflicts=context.characteristic_conflicts,
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
                "TradeOffEngine JSON parse failed, attempting repair. error=%s", e
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

        decisions = result.get("decisions", [])
        validated: list[dict] = []

        for decision in decisions:
            optimises = decision.get("optimises_characteristics", [])
            sacrifices = decision.get("sacrifices_characteristics", [])
            confidence = decision.get("confidence", "")

            if not optimises:
                logger.warning(
                    "TradeOffEngine: dropping decision %s — empty optimises_characteristics",
                    decision.get("decision_id", "unknown"),
                )
                continue
            if not sacrifices:
                logger.warning(
                    "TradeOffEngine: dropping decision %s — empty sacrifices_characteristics",
                    decision.get("decision_id", "unknown"),
                )
                continue
            if confidence not in _VALID_CONFIDENCE:
                logger.warning(
                    "TradeOffEngine: dropping decision %s — invalid confidence '%s'",
                    decision.get("decision_id", "unknown"),
                    confidence,
                )
                continue

            validated.append(decision)

        context.trade_offs = validated
        context.trade_off_dominant_tension = (
            result.get("dominant_tension", "") or ""
        )

        logger.info(
            "TradeOffEngine produced %d validated decisions (dropped %d) "
            "repair_attempted=%s",
            len(validated),
            len(decisions) - len(validated),
            repair_attempted,
        )
        return context
